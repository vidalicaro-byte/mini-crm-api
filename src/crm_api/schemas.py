"""Request and response bodies. JSON uses camelCase, as in the front end's contract."""

from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, EmailStr, Field
from pydantic.alias_generators import to_camel

from crm_api.models import UserRole


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class ErrorResponse(BaseModel):
    message: str = Field(examples=["Sessão expirada. Entre novamente."])


class Page[T](ApiModel):
    data: list[T]
    total: int
    page: int
    page_size: int


class UserOut(ApiModel):
    id: str = Field(examples=["usr_1"])
    name: str = Field(examples=["Marina Albuquerque"])
    email: str = Field(examples=["marina@minicrm.demo"])
    role: UserRole


def _strip(value: Any) -> Any:
    return value.strip() if isinstance(value, str) else value


# Trimmed before validation (people often paste an address with a trailing space) and stored
# lowercased, so "Ana@X.com" and "ana@x.com" are the same person.
Email = Annotated[EmailStr, BeforeValidator(_strip), AfterValidator(str.lower)]


class LoginRequest(ApiModel):
    email: Email = Field(examples=["marina@minicrm.demo"])
    password: str = Field(min_length=1, examples=["demo1234"])


class LoginResponse(ApiModel):
    token: str
    user: UserOut


class TokenResponse(BaseModel):
    """OAuth2 password-flow response (used by the "Authorize" button of the interactive docs)."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105  (OAuth2 token type, not a secret)
