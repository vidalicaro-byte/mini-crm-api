from datetime import UTC, datetime
from typing import Annotated, Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Query, Response, status
from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import InstrumentedAttribute, Session, joinedload

from crm_api.access import visible_contacts
from crm_api.deps import CurrentUser, SessionDep
from crm_api.errors import conflict, invalid, not_found, responses
from crm_api.models import Company, Contact, User
from crm_api.pagination import PaginationDep
from crm_api.schemas import ContactCreate, ContactOut, ContactUpdate, Page, SortOrder
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


def _find_visible(session: Session, user: User, contact_id: str) -> Contact:
    contact = session.scalars(
        _contacts_query().where(Contact.id == contact_id, visible_contacts(user))
    ).one_or_none()
    if contact is None:
        raise not_found("Contato não encontrado.")
    return contact


@router.get("/{contact_id}", responses=responses(401, 404))
def get_contact(contact_id: str, user: CurrentUser, session: SessionDep) -> ContactOut:
    """One contact. Someone else's contact is reported as missing (404) to a seller."""
    return ContactOut.model_validate(_find_visible(session, user, contact_id))


_EMAIL_TAKEN = "Já existe um contato com este e-mail."


def _check_rules(session: Session, company_id: str | None, email: str | None, own_id: str) -> None:
    """Rules that need the database: the company must exist and the e-mail must be unique."""
    if company_id is not None and session.get(Company, company_id) is None:
        raise invalid("Empresa não encontrada.")
    if email is not None:
        taken = session.scalar(
            select(Contact.id).where(Contact.email == email, Contact.id != own_id)
        )
        if taken:
            raise conflict(_EMAIL_TAKEN)


def _save(session: Session, contact: Contact) -> ContactOut:
    try:
        session.commit()
    except IntegrityError:
        # Two requests with the same e-mail at the same moment: the check above passed for both,
        # the unique constraint stops the second one.
        session.rollback()
        raise conflict(_EMAIL_TAKEN) from None
    # Reload with the company joined in. populate_existing replaces the company already in memory,
    # which is stale when the update moved the contact to another company.
    saved = session.scalars(
        _contacts_query().where(Contact.id == contact.id).execution_options(populate_existing=True)
    ).one()
    return ContactOut.model_validate(saved)


@router.post("", status_code=status.HTTP_201_CREATED, responses=responses(401, 409, 422))
def create_contact(
    body: ContactCreate, user: CurrentUser, session: SessionDep, response: Response
) -> ContactOut:
    """Create a contact. It belongs to whoever creates it."""
    contact_id = f"ct_{uuid4().hex[:12]}"
    _check_rules(session, body.company_id, body.email, own_id=contact_id)
    contact = Contact(
        id=contact_id,
        **body.model_dump(),
        owner_id=user.id,
        created_at=datetime.now(UTC),
    )
    session.add(contact)
    created = _save(session, contact)
    response.headers["Location"] = f"/api/contacts/{contact.id}"
    return created


@router.patch("/{contact_id}", responses=responses(401, 404, 409, 422))
def update_contact(
    contact_id: str, body: ContactUpdate, user: CurrentUser, session: SessionDep
) -> ContactOut:
    """Change some fields of a contact. Only the fields sent are changed; the owner never is."""
    contact = _find_visible(session, user, contact_id)
    changes = body.changes()
    _check_rules(session, changes.get("company_id"), changes.get("email"), own_id=contact.id)
    for field, value in changes.items():
        setattr(contact, field, value)
    return _save(session, contact)
