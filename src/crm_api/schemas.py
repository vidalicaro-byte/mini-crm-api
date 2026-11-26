"""Request and response bodies. JSON uses camelCase, as in the front end's contract."""

import re
from datetime import datetime
from typing import Annotated, Any, Literal, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    EmailStr,
    Field,
    model_validator,
    validate_email,
)
from pydantic.alias_generators import to_camel
from pydantic_core import PydanticCustomError

from crm_api.models import ActivityType, CompanySize, DealStage, UserRole


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


class CompanyRef(ApiModel):
    id: str = Field(examples=["cmp_1"])
    name: str = Field(examples=["Aurora Tecnologia"])


class ContactOut(ApiModel):
    id: str = Field(examples=["ct_1"])
    name: str
    email: str
    phone: str
    job_title: str
    company_id: str
    owner_id: str
    created_at: datetime
    company: CompanyRef


type SortOrder = Literal["asc", "desc"]


# --- Contact input: the same rules and messages as the front end's form (contactInputSchema) ---

USER_MESSAGE = "user_message"  # error type whose message is shown to the user as-is


def _fail(message: str) -> PydanticCustomError:
    return PydanticCustomError(USER_MESSAGE, message)


def _check_name(value: str) -> str:
    if len(value) < 2:
        raise _fail("Informe o nome (mínimo 2 letras).")
    if len(value) > 100:
        raise _fail("Nome muito longo.")
    return value


def _check_email(value: str) -> str:
    try:
        _, address = validate_email(value)
    except PydanticCustomError:
        raise _fail("Informe um e-mail válido.") from None
    return address.lower()


def _check_phone(value: str) -> str:
    # Optional, but when present it must look like a Brazilian number with area code.
    digits = re.sub(r"\D", "", value)
    if value and not 10 <= len(digits) <= 11:
        raise _fail("Informe o telefone com DDD, por exemplo (11) 91234-5678.")
    return value


def _check_job_title(value: str) -> str:
    if len(value) > 80:
        raise _fail("Cargo muito longo.")
    return value


def _check_company_id(value: str) -> str:
    if not value:
        raise _fail("Escolha a empresa.")
    return value


type _Trimmed = Annotated[str, BeforeValidator(_strip)]
ContactName = Annotated[_Trimmed, AfterValidator(_check_name), Field(examples=["Ana Souza"])]
ContactEmail = Annotated[
    _Trimmed, AfterValidator(_check_email), Field(examples=["ana.souza@example.com"])
]
Phone = Annotated[_Trimmed, AfterValidator(_check_phone), Field(examples=["(11) 91234-5678"])]
JobTitle = Annotated[_Trimmed, AfterValidator(_check_job_title), Field(examples=["Compradora"])]
CompanyId = Annotated[str, AfterValidator(_check_company_id), Field(examples=["cmp_1"])]


class ContactCreate(ApiModel):
    name: ContactName
    email: ContactEmail
    phone: Phone = ""
    job_title: JobTitle = ""
    company_id: CompanyId


class ContactUpdate(ApiModel):
    """Partial update: only the fields sent are changed. Fields can't be set to null."""

    name: ContactName | None = None
    email: ContactEmail | None = None
    phone: Phone | None = None
    job_title: JobTitle | None = None
    company_id: CompanyId | None = None

    @model_validator(mode="after")
    def reject_nulls(self) -> Self:
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise _fail("Campos não podem ser nulos.")
        return self

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class OpenDeals(ApiModel):
    count: int
    value: int


class CompanyOut(ApiModel):
    """A company plus figures about what the viewer may see (a seller only counts their own)."""

    id: str = Field(examples=["cmp_1"])
    name: str
    industry: str
    size: CompanySize
    city: str
    state: str
    website: str
    contacts_count: int
    open_deals: OpenDeals


class ContactRef(ApiModel):
    id: str = Field(examples=["ct_1"])
    name: str = Field(examples=["Ana Souza"])


class DealOut(ApiModel):
    id: str = Field(examples=["deal_1"])
    title: str
    value: int = Field(description="Whole reais.", examples=[45000])
    stage: DealStage
    contact_id: str
    company_id: str
    owner_id: str
    created_at: datetime
    expected_close_date: datetime
    closed_at: datetime | None
    contact: ContactRef
    company: CompanyRef


def _check_stage(value: Any) -> Any:
    if value not in {stage.value for stage in DealStage}:
        raise _fail("Etapa inválida.")
    return value


class DealStageUpdate(ApiModel):
    stage: Annotated[DealStage, BeforeValidator(_check_stage)]


class ActivityOut(ApiModel):
    id: str = Field(examples=["act_1"])
    type: ActivityType
    contact_id: str
    deal_id: str | None
    owner_id: str
    date: datetime
    summary: str
