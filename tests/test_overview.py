"""GET /api/overview. Expected values come from a plain-Python port of the Mini-CRM mock
(src/mocks/overview.ts) run over the seed file, independent from the SQL implementation."""

from datetime import UTC, datetime, timedelta
from math import ceil
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from crm_api.routers.overview import get_now
from crm_api.seed import parse_datetime, read_seed
from tests.conftest import NOW

SEED = read_seed()
OFFSET = NOW - parse_datetime(SEED["referenceDate"])
STAGES = ["novo", "contato", "proposta", "negociacao", "ganho", "perdido"]
DAY = timedelta(days=1)


def shifted(iso: str | None) -> datetime | None:
    return parse_datetime(iso) + OFFSET if iso else None


def month_start(moment: datetime, back: int) -> datetime:
    index = moment.year * 12 + moment.month - 1 - back
    return datetime(index // 12, index % 12 + 1, 1, tzinfo=UTC)


def expected_overview(period: str, owner: str | None) -> dict[str, Any]:
    def mine(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [i for i in items if owner is None or i["ownerId"] == owner]

    contacts, deals = mine(SEED["contacts"]), mine(SEED["deals"])
    end = NOW + timedelta(milliseconds=1)
    if period == "12m":
        current = (month_start(NOW, 11), end)
        previous = (month_start(NOW, 23), current[0])
    else:
        length = {"7d": 7, "30d": 30, "90d": 90}[period] * DAY
        current, previous = (end - length, end), (end - 2 * length, end - length)

    def within(value: datetime | None, window: tuple[datetime, datetime]) -> bool:
        return value is not None and window[0] <= value < window[1]

    def closed(stage: str, window: tuple[datetime, datetime]) -> list[dict[str, Any]]:
        return [d for d in deals if d["stage"] == stage and within(shifted(d["closedAt"]), window)]

    def rate(window: tuple[datetime, datetime]) -> float | None:
        won, lost = len(closed("ganho", window)), len(closed("perdido", window))
        return None if won + lost == 0 else won / (won + lost)

    open_deals = [d for d in deals if d["stage"] not in ("ganho", "perdido")]
    created = [d for d in deals if within(shifted(d["createdAt"]), current)]

    if period == "12m":
        granularity, starts = "month", [month_start(NOW, 11 - i) for i in range(12)]
    else:
        granularity = "week" if period == "90d" else "day"
        size = 7 * DAY if granularity == "week" else DAY
        count = ceil((current[1] - current[0]) / size)
        starts = [current[1] - (count - i) * size for i in range(count)]
    values = [0] * len(starts)
    for deal in closed("ganho", current):
        closed_at = shifted(deal["closedAt"])
        assert closed_at is not None
        index = max(i for i, start in enumerate(starts) if start <= closed_at)
        values[index] += deal["value"]

    def iso(moment: datetime) -> str:
        return moment.isoformat().replace("+00:00", "Z")

    return {
        "period": period,
        "totals": {"contacts": len(contacts), "companies": len(SEED["companies"])},
        "newContacts": {
            "current": sum(within(shifted(c["createdAt"]), current) for c in contacts),
            "previous": sum(within(shifted(c["createdAt"]), previous) for c in contacts),
        },
        "wonRevenue": {
            "current": sum(d["value"] for d in closed("ganho", current)),
            "previous": sum(d["value"] for d in closed("ganho", previous)),
        },
        "conversionRate": {"current": rate(current), "previous": rate(previous)},
        "openDeals": {"count": len(open_deals), "value": sum(d["value"] for d in open_deals)},
        "funnel": [
            {
                "stage": stage,
                "count": sum(d["stage"] == stage for d in created),
                "value": sum(d["value"] for d in created if d["stage"] == stage),
            }
            for stage in STAGES
        ],
        "revenue": {
            "granularity": granularity,
            "buckets": [{"start": iso(s), "value": v} for s, v in zip(starts, values, strict=True)],
        },
    }


@pytest.fixture
def frozen(client: TestClient) -> TestClient:
    """The seed was loaded relative to NOW, so the overview must be computed at NOW too."""
    app = client.app
    assert isinstance(app, FastAPI)
    app.dependency_overrides[get_now] = lambda: NOW
    return client


def normalize(body: dict[str, Any]) -> dict[str, Any]:
    # Rates are floats: compare them rounded, everything else exactly.
    for key in ("current", "previous"):
        if body["conversionRate"][key] is not None:
            body["conversionRate"][key] = round(body["conversionRate"][key], 9)
    for bucket in body["revenue"]["buckets"]:
        bucket["start"] = parse_datetime(bucket["start"]).isoformat().replace("+00:00", "Z")
    return body


@pytest.mark.parametrize("period", ["7d", "30d", "90d", "12m"])
@pytest.mark.parametrize("viewer", ["admin", "seller"])
def test_overview_matches_the_mock(
    frozen: TestClient,
    admin_headers: dict[str, str],
    seller_headers: dict[str, str],
    period: str,
    viewer: str,
) -> None:
    headers, owner = (admin_headers, None) if viewer == "admin" else (seller_headers, "usr_2")

    response = frozen.get("/api/overview", params={"period": period}, headers=headers)

    assert response.status_code == 200
    assert normalize(response.json()) == normalize(expected_overview(period, owner))


def test_the_data_actually_exercises_every_figure(
    frozen: TestClient, admin_headers: dict[str, str]
) -> None:
    # Guards against a test that passes because everything is zero.
    body = frozen.get("/api/overview", params={"period": "90d"}, headers=admin_headers).json()

    assert body["newContacts"]["current"] > 0
    assert body["wonRevenue"]["current"] > 0
    assert body["conversionRate"]["current"] is not None
    assert sum(stage["count"] for stage in body["funnel"]) > 0
    assert sum(1 for bucket in body["revenue"]["buckets"] if bucket["value"]) > 1


def test_bucket_counts(frozen: TestClient, admin_headers: dict[str, str]) -> None:
    def buckets(period: str) -> list[dict[str, Any]]:
        response = frozen.get("/api/overview", params={"period": period}, headers=admin_headers)
        result: list[dict[str, Any]] = response.json()["revenue"]["buckets"]
        return result

    assert len(buckets("7d")) == 7
    assert len(buckets("30d")) == 30
    assert len(buckets("90d")) == 13
    months = buckets("12m")
    assert len(months) == 12
    assert months[-1]["start"].startswith("2026-11-01")


def test_default_period_is_30_days(frozen: TestClient, admin_headers: dict[str, str]) -> None:
    body = frozen.get("/api/overview", headers=admin_headers).json()

    assert body["period"] == "30d"


def test_invalid_period_is_422(frozen: TestClient, admin_headers: dict[str, str]) -> None:
    response = frozen.get("/api/overview", params={"period": "1y"}, headers=admin_headers)

    assert response.status_code == 422
    assert response.json()["message"] == "Período inválido."


def test_overview_requires_a_token(client: TestClient) -> None:
    assert client.get("/api/overview").status_code == 401
