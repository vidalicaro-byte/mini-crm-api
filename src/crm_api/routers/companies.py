from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query
from sqlalchemy import ColumnElement, Row, Select, case, func, select
from sqlalchemy.orm import InstrumentedAttribute

from crm_api.access import visible_contacts, visible_deals
from crm_api.deps import CurrentUser, SessionDep
from crm_api.errors import not_found, responses
from crm_api.models import Company, CompanySize, Contact, Deal, DealStage, User
from crm_api.pagination import PaginationDep
from crm_api.schemas import CompanyOut, OpenDeals, Page, SortOrder
from crm_api.text import natural_sort

router = APIRouter(prefix="/api/companies", tags=["companies"])

type CompanySort = Literal["name", "industry", "size", "city", "contactsCount", "openDealsValue"]

_CLOSED = (DealStage.GANHO, DealStage.PERDIDO)


def _companies_query(user: User) -> Select[Company, int, int, int]:
    """Companies with three figures computed by the database, counting only what `user` may see.

    Correlated subqueries: for each company row, the database counts its contacts and open deals.
    Everyone sees every company; the figures differ per user.
    """
    contacts_count = (
        select(func.count(Contact.id))
        .where(Contact.company_id == Company.id, visible_contacts(user))
        .scalar_subquery()
    )
    open_deal = (Deal.company_id == Company.id, Deal.stage.not_in(_CLOSED), visible_deals(user))
    open_count = select(func.count(Deal.id)).where(*open_deal).scalar_subquery()
    open_value = select(func.coalesce(func.sum(Deal.value), 0)).where(*open_deal).scalar_subquery()
    return select(
        Company,
        contacts_count.label("contacts_count"),
        open_count.label("open_count"),
        open_value.label("open_value"),
    )


def _to_out(row: Row[Company, int, int, int]) -> CompanyOut:
    company, contacts_count, open_count, open_value = row
    return CompanyOut(
        id=company.id,
        name=company.name,
        industry=company.industry,
        size=company.size,
        city=company.city,
        state=company.state,
        website=company.website,
        contacts_count=contacts_count,
        open_deals=OpenDeals(count=open_count, value=open_value),
    )


# Sizes sort by magnitude, not alphabetically ("média" sits between "pequena" and "grande").
_SIZE_RANK = case(
    {CompanySize.PEQUENA: 0, CompanySize.MEDIA: 1, CompanySize.GRANDE: 2}, value=Company.size
)


def _sort_column(
    query: Select[Company, int, int, int], sort: CompanySort
) -> ColumnElement[Any] | InstrumentedAttribute[Any]:
    columns: dict[str, ColumnElement[Any] | InstrumentedAttribute[Any]] = {
        "name": natural_sort(Company.name),
        "industry": natural_sort(Company.industry),
        "size": _SIZE_RANK,
        "city": natural_sort(Company.city),
        # The figures computed in the SELECT, referenced by their labels.
        "contactsCount": query.selected_columns.contacts_count,
        "openDealsValue": query.selected_columns.open_value,
    }
    return columns[sort]


@router.get("", responses=responses(401, 422))
def list_companies(
    user: CurrentUser,
    session: SessionDep,
    pagination: PaginationDep,
    q: Annotated[
        str | None, Query(max_length=100, description="Searches name, industry and city.")
    ] = None,
    size: CompanySize | None = None,
    sort: CompanySort = "name",
    order: SortOrder = "asc",
) -> Page[CompanyOut]:
    """Every company (visible to all), with figures counting only what the user may see."""
    query = _companies_query(user)
    if size:
        query = query.where(Company.size == size)
    if q and (needle := q.strip().lower()):
        query = query.where(
            func.lower(Company.name).contains(needle, autoescape=True)
            | func.lower(Company.industry).contains(needle, autoescape=True)
            | func.lower(Company.city).contains(needle, autoescape=True)
        )

    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    sort_by = _sort_column(query, sort)
    direction = sort_by.desc() if order == "desc" else sort_by.asc()
    # Ties (same size, same count...) fall back to the name, then the id, for a stable order.
    query = query.order_by(direction, natural_sort(Company.name), Company.id)
    rows = session.execute(query.offset(pagination.offset).limit(pagination.page_size)).all()

    return Page[CompanyOut](
        data=[_to_out(row) for row in rows],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/{company_id}", responses=responses(401, 404))
def get_company(company_id: str, user: CurrentUser, session: SessionDep) -> CompanyOut:
    """One company, with figures counting only what the user may see."""
    row = session.execute(_companies_query(user).where(Company.id == company_id)).one_or_none()
    if row is None:
        raise not_found("Empresa não encontrada.")
    return _to_out(row)
