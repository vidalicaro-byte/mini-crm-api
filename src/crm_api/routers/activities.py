from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from crm_api.deps import CurrentUser, SessionDep
from crm_api.errors import responses
from crm_api.models import Activity
from crm_api.pagination import ActivitiesPaginationDep
from crm_api.routers.deals import ensure_contact_visible
from crm_api.schemas import ActivityOut, Page

router = APIRouter(prefix="/api/activities", tags=["activities"])


@router.get("", responses=responses(401, 404, 422))
def list_activities(
    user: CurrentUser,
    session: SessionDep,
    pagination: ActivitiesPaginationDep,
    contact_id: Annotated[str, Query(alias="contactId", min_length=1)],
) -> Page[ActivityOut]:
    """A contact's activities (calls, e-mails, meetings, notes), newest first."""
    ensure_contact_visible(session, user, contact_id)
    query = select(Activity).where(Activity.contact_id == contact_id)
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    activities = session.scalars(
        query.order_by(Activity.date.desc(), Activity.id)
        .offset(pagination.offset)
        .limit(pagination.page_size)
    ).all()
    return Page[ActivityOut](
        data=[ActivityOut.model_validate(activity) for activity in activities],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )
