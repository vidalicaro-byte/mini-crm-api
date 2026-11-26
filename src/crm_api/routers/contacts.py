from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query
from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.orm import InstrumentedAttribute, joinedload

from crm_api.access import visible_contacts
from crm_api.deps import CurrentUser, SessionDep
from crm_api.errors import not_found, responses
from crm_api.models import Company, Contact
from crm_api.pagination import PaginationDep
from crm_api.schemas import ContactOut, Page, SortOrder
from crm_api.text import natural_sort

router = APIRouter(prefix="/api/contacts", tags=["contacts"])

type ContactSort = Literal["name", "email", "company", "createdAt"]

_SORT_COLUMNS: dict[str, ColumnElement[Any] | InstrumentedAttribute[Any]] = {
    "name": natural_sort(Contact.name),
    "email": natural_sort(Contact.email),
    "company": natural_sort(Company.name),
    "createdAt": Contact.created_at,
}


def _contacts_query() -> Select[Contact]:
    # The join serves search and sorting by company name; joinedload fills contact.company from it.
    return select(Contact).join(Contact.company).options(joinedload(Contact.company))


@router.get("", responses=responses(401, 422))
def list_contacts(
    user: CurrentUser,
    session: SessionDep,
    pagination: PaginationDep,
    q: Annotated[
        str | None,
        Query(max_length=100, description="Searches name, e-mail and company name."),
    ] = None,
    company_id: Annotated[str | None, Query(alias="companyId")] = None,
    sort: ContactSort = "name",
    order: SortOrder = "asc",
) -> Page[ContactOut]:
    """Contacts the user may see (sellers: only their own), filtered, sorted and paginated."""
    query = _contacts_query().where(visible_contacts(user))
    if company_id:
        query = query.where(Contact.company_id == company_id)
    if q and (needle := q.strip().lower()):
        # autoescape: a search for "50%" looks for the text "50%", not "50" followed by anything.
        query = query.where(
            func.lower(Contact.name).contains(needle, autoescape=True)
            | Contact.email.contains(needle, autoescape=True)
            | func.lower(Company.name).contains(needle, autoescape=True)
        )

    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    column = _SORT_COLUMNS[sort]
    # The id breaks ties, so pages never repeat or skip a row that shares a name.
    query = query.order_by(column.desc() if order == "desc" else column.asc(), Contact.id)
    contacts = session.scalars(query.offset(pagination.offset).limit(pagination.page_size)).all()

    return Page[ContactOut](
        data=[ContactOut.model_validate(contact) for contact in contacts],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/{contact_id}", responses=responses(401, 404))
def get_contact(contact_id: str, user: CurrentUser, session: SessionDep) -> ContactOut:
    """One contact. Someone else's contact is reported as missing (404) to a seller."""
    contact = session.scalars(
        _contacts_query().where(Contact.id == contact_id, visible_contacts(user))
    ).one_or_none()
    if contact is None:
        raise not_found("Contato não encontrado.")
    return ContactOut.model_validate(contact)
