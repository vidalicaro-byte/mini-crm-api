from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, joinedload

from crm_api.access import visible_contacts, visible_deals
from crm_api.deps import CurrentUser, SessionDep
from crm_api.errors import not_found, responses
from crm_api.models import Contact, Deal, User
from crm_api.pagination import DealsPaginationDep
from crm_api.schemas import DealOut, DealStageUpdate, Page

router = APIRouter(prefix="/api/deals", tags=["deals"])


def _deals_query() -> Select[Deal]:
    return select(Deal).options(joinedload(Deal.contact), joinedload(Deal.company))


def ensure_contact_visible(session: Session, user: User, contact_id: str) -> None:
    visible = session.scalar(
        select(Contact.id).where(Contact.id == contact_id, visible_contacts(user))
    )
    if visible is None:
        raise not_found("Contato não encontrado.")


@router.get("", responses=responses(401, 404, 422))
def list_deals(
    user: CurrentUser,
    session: SessionDep,
    pagination: DealsPaginationDep,
    contact_id: Annotated[str | None, Query(alias="contactId")] = None,
    company_id: Annotated[str | None, Query(alias="companyId")] = None,
) -> Page[DealOut]:
    """Deals, newest first. Without parameters: every deal the user may see (the funnel board).

    With `contactId`: that contact's deals (404 if the user may not see the contact).
    With `companyId`: the deals of that company the user may see.
    """
    query = _deals_query()
    if contact_id:
        ensure_contact_visible(session, user, contact_id)
        query = query.where(Deal.contact_id == contact_id)
    else:
        query = query.where(visible_deals(user))
    if company_id:
        query = query.where(Deal.company_id == company_id)

    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    query = query.order_by(Deal.created_at.desc(), Deal.id)
    deals = session.scalars(query.offset(pagination.offset).limit(pagination.page_size)).all()
    return Page[DealOut](
        data=[DealOut.model_validate(deal) for deal in deals],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.patch("/{deal_id}", responses=responses(401, 404, 422))
def move_deal(
    deal_id: str, body: DealStageUpdate, user: CurrentUser, session: SessionDep
) -> DealOut:
    """Move a deal to another stage. Closing it stamps `closedAt`; reopening clears it."""
    deal = session.scalars(
        _deals_query().where(Deal.id == deal_id, visible_deals(user))
    ).one_or_none()
    if deal is None:
        raise not_found("Negócio não encontrado.")

    deal.stage = body.stage
    if not deal.is_closed:
        deal.closed_at = None
    elif deal.closed_at is None:
        # Moving between "ganho" and "perdido" keeps the original closing date.
        deal.closed_at = datetime.now(UTC)
    session.commit()
    return DealOut.model_validate(deal)
