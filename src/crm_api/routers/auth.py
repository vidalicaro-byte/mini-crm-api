from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from crm_api.deps import CurrentUser, SessionDep, SettingsDep
from crm_api.errors import ApiError, responses
from crm_api.models import User
from crm_api.schemas import LoginRequest, LoginResponse, TokenResponse, UserOut
from crm_api.security import create_access_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def authenticate(session: Session, email: str, password: str) -> User:
    user = session.scalars(select(User).where(User.email == email.strip().lower())).one_or_none()
    # The password is checked even for unknown e-mails (against a dummy hash) and both cases get
    # the same message, so neither the answer nor its timing reveals which e-mails exist.
    if not verify_password(password, user.password_hash if user else None) or user is None:
        raise ApiError(401, "E-mail ou senha incorretos.")
    return user


@router.post("/login", summary="Sign in (JSON)", responses=responses(401, 422))
def login(body: LoginRequest, session: SessionDep, settings: SettingsDep) -> LoginResponse:
    """Exchange e-mail and password for an access token (JWT, valid for 8 hours)."""
    user = authenticate(session, body.email, body.password)
    return LoginResponse(
        token=create_access_token(user, settings), user=UserOut.model_validate(user)
    )


@router.post("/token", summary="Sign in (OAuth2 form, used by Authorize)", responses=responses(401))
def token(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDep,
    settings: SettingsDep,
) -> TokenResponse:
    """OAuth2 password flow for the interactive docs: use your e-mail as the username."""
    user = authenticate(session, form.username, form.password)
    return TokenResponse(access_token=create_access_token(user, settings))


@router.get("/me", summary="Current user", responses=responses(401))
def me(user: CurrentUser) -> UserOut:
    """The signed-in user."""
    return UserOut.model_validate(user)
