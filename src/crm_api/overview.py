"""The dashboard's numbers, aggregated by the database for one user and one period.

Mirrors the Mini-CRM mock (src/mocks/overview.ts): the same windows, buckets and rules, but each
figure is a SQL aggregate instead of a loop over every row.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import ceil
from typing import Literal

from sqlalchemy import ColumnElement, and_, case, func, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from crm_api.access import visible_contacts, visible_deals
from crm_api.models import Company, Contact, Deal, DealStage, User
from crm_api.schemas import (
    FunnelStage,
    OpenDeals,
    OverviewOut,
    Period,
    RateTrend,
    Revenue,
    RevenueBucket,
    Totals,
    Trend,
)

DAY = timedelta(days=1)
# Windows end just after "now", so a record created this very instant counts (as in the mock).
_EPSILON = timedelta(milliseconds=1)


@dataclass(frozen=True)
class Window:
    """[start, end)"""

    start: datetime
    end: datetime

    def contains(
        self, column: InstrumentedAttribute[datetime] | InstrumentedAttribute[datetime | None]
    ) -> ColumnElement[bool]:
        return and_(column >= self.start, column < self.end)


def start_of_month(moment: datetime, months_back: int = 0) -> datetime:
    """Calendar months are cut in UTC: good enough for demo data."""
    month_index = moment.year * 12 + (moment.month - 1) - months_back
    return datetime(month_index // 12, month_index % 12 + 1, 1, tzinfo=UTC)


def windows(period: Period, now: datetime) -> tuple[Window, Window]:
    """The chosen period and the same-length period right before it."""
    end = now + _EPSILON
    if period == "12m":
        start = start_of_month(now, 11)
        return Window(start, end), Window(start_of_month(now, 23), start)
    length = {"7d": 7, "30d": 30, "90d": 90}[period] * DAY
    return Window(end - length, end), Window(end - 2 * length, end - length)


type Granularity = Literal["day", "week", "month"]


def bucket_starts(
    period: Period, now: datetime, current: Window
) -> tuple[Granularity, list[datetime]]:
    if period == "12m":
        return "month", [start_of_month(now, 11 - index) for index in range(12)]
    granularity: Granularity = "week" if period == "90d" else "day"
    size = 7 * DAY if granularity == "week" else DAY
    count = ceil((current.end - current.start) / size)
    # Oldest first; the first week of a 90-day period may start before the period does.
    return granularity, [current.end - (count - index) * size for index in range(count)]


def compute_overview(session: Session, user: User, period: Period, now: datetime) -> OverviewOut:
    current, previous = windows(period, now)
    my_contacts = visible_contacts(user)
    my_deals = visible_deals(user)
    won = Deal.stage == DealStage.GANHO
    lost = Deal.stage == DealStage.PERDIDO

    # One query per table; FILTER (WHERE ...) computes several aggregates in a single pass.
    contacts = session.execute(
        select(
            func.count(),
            func.count().filter(current.contains(Contact.created_at)),
            func.count().filter(previous.contains(Contact.created_at)),
        ).where(my_contacts)
    ).one()

    def won_value(window: Window) -> ColumnElement[int]:
        return func.coalesce(func.sum(Deal.value).filter(won, window.contains(Deal.closed_at)), 0)

    def closed_count(stage: ColumnElement[bool], window: Window) -> ColumnElement[int]:
        return func.count().filter(stage, window.contains(Deal.closed_at))

    is_open = ~(won | lost)
    deals = session.execute(
        select(
            won_value(current),
            won_value(previous),
            closed_count(won, current),
            closed_count(lost, current),
            closed_count(won, previous),
            closed_count(lost, previous),
            func.count().filter(is_open),
            func.coalesce(func.sum(Deal.value).filter(is_open), 0),
        ).where(my_deals)
    ).one()
    won_now, lost_now, won_before, lost_before = deals[2:6]

    funnel_rows = session.execute(
        select(Deal.stage, func.count(), func.sum(Deal.value))
        .where(my_deals, current.contains(Deal.created_at))
        .group_by(Deal.stage)
    ).all()
    funnel = {stage: (count, value) for stage, count, value in funnel_rows}
    funnel_stages = []
    for stage in DealStage:  # every stage, in board order, even when empty
        count, value = funnel.get(stage, (0, 0))
        funnel_stages.append(FunnelStage(stage=stage, count=count, value=value))
    funnel_stages = []
    for stage in DealStage:  # every stage, in board order, even when empty
        count, value = funnel.get(stage, (0, 0))
        funnel_stages.append(FunnelStage(stage=stage, count=count, value=value))

    return OverviewOut(
        period=period,
        totals=Totals(
            contacts=contacts[0],
            companies=session.scalar(select(func.count()).select_from(Company)) or 0,
        ),
        new_contacts=Trend(current=contacts[1], previous=contacts[2]),
        won_revenue=Trend(current=deals[0], previous=deals[1]),
        conversion_rate=RateTrend(
            current=_rate(won_now, lost_now), previous=_rate(won_before, lost_before)
        ),
        open_deals=OpenDeals(count=deals[6], value=deals[7]),
        funnel=funnel_stages,
        revenue=_revenue(session, user, period, now, current),
    )


def _rate(won: int, lost: int) -> float | None:
    closed = won + lost
    return None if closed == 0 else won / closed


def _revenue(
    session: Session, user: User, period: Period, now: datetime, current: Window
) -> Revenue:
    granularity, starts = bucket_starts(period, now, current)
    # Each won deal goes to the last bucket that starts at or before its closing time. A CASE
    # with one branch per bucket (newest first) does that on any database, without date functions
    # that differ between SQLite and PostgreSQL.
    bucket = case(
        *[(Deal.closed_at >= start, index) for index, start in reversed(list(enumerate(starts)))],
        else_=-1,
    )
    rows = session.execute(
        select(bucket, func.sum(Deal.value))
        .where(
            visible_deals(user),
            Deal.stage == DealStage.GANHO,
            current.contains(Deal.closed_at),
        )
        .group_by(bucket)
    ).all()
    totals = {index: value for index, value in rows}
    return Revenue(
        granularity=granularity,
        buckets=[
            RevenueBucket(start=start, value=totals.get(index, 0))
            for index, start in enumerate(starts)
        ],
    )
