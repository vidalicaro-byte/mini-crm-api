from fastapi import APIRouter
from sqlalchemy import func, select

from crm_api.deps import AdminUser, SessionDep
from crm_api.errors import responses
from crm_api.models import User
from crm_api.pagination import PaginationDep
from crm_api.schemas import Page, UserOut

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", responses=responses(401, 403))
def list_users(_admin: AdminUser, session: SessionDep, pagination: PaginationDep) -> Page[UserOut]:
    """Every user, sorted by name. Admins only."""
    total = session.scalar(select(func.count()).select_from(User)) or 0
    users = session.scalars(
        select(User)
        .order_by(User.name, User.id)
        .offset(pagination.offset)
        .limit(pagination.page_size)
    ).all()
    return Page[UserOut](
        data=[UserOut.model_validate(user) for user in users],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )
