from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BeforeValidator
from pydantic_core import PydanticCustomError

from crm_api.deps import CurrentUser, SessionDep
from crm_api.errors import responses
from crm_api.overview import compute_overview
from crm_api.schemas import USER_MESSAGE, OverviewOut, Period

router = APIRouter(prefix="/api/overview", tags=["overview"])


def get_now() -> datetime:
    """The current time, as a dependency so tests can freeze it."""
    return datetime.now(UTC)


def _check_period(value: Any) -> Any:
    if value not in ("7d", "30d", "90d", "12m"):
        raise PydanticCustomError(USER_MESSAGE, "Período inválido.")
    return value


@router.get("", summary="Dashboard metrics", responses=responses(401, 422))
def get_overview(
    user: CurrentUser,
    session: SessionDep,
    now: Annotated[datetime, Depends(get_now)],
    period: Annotated[Period, BeforeValidator(_check_period), Query()] = "30d",
) -> OverviewOut:
    """KPIs, funnel and revenue for the period, counting only the user's own data (all for admins).

    Trends compare the period with the same-length period right before it; `12m` uses calendar
    months.
    """
    return compute_overview(session, user, period, now)
