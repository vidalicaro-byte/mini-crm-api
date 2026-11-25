"""FastAPI dependencies shared by the routers: settings, database session and current user."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from crm_api.config import Settings, get_settings
from crm_api.db import get_session
from crm_api.errors import forbidden, unauthorized
from crm_api.models import User, UserRole
from crm_api.security import read_token_subject

# Reads "Authorization: Bearer <token>". tokenUrl powers the docs' "Authorize" button.
_bearer = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)

SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[Session, Depends(get_session)]


def get_current_user(
    session: SessionDep, settings: SettingsDep, token: Annotated[str | None, Depends(_bearer)]
) -> User:
    user_id = read_token_subject(token, settings) if token else None
    user = session.get(User, user_id) if user_id else None
    if user is None:
        raise unauthorized()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role is not UserRole.ADMIN:
        raise forbidden()
    return user


AdminUser = Annotated[User, Depends(require_admin)]
