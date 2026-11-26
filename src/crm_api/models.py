"""Database tables. Column names and enum values mirror the Mini-CRM API contract."""

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, TypeDecorator
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import Mapped, mapped_column, relationship

from crm_api.db import Base


class UTCDateTime(TypeDecorator[datetime]):
    """Timezone-aware UTC datetimes on every database.

    PostgreSQL stores the offset (timestamptz); SQLite stores plain text and loses it. This type
    rejects naive datetimes on the way in and always hands back aware UTC datetimes on the way out,
    so the API never mixes naive and aware values.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError(
                "Naive datetime: pass a timezone-aware value (e.g. datetime.now(UTC))."
            )
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class UserRole(StrEnum):
    ADMIN = "admin"
    VENDEDOR = "vendedor"


class CompanySize(StrEnum):
    PEQUENA = "pequena"
    MEDIA = "media"
    GRANDE = "grande"


class DealStage(StrEnum):
    NOVO = "novo"
    CONTATO = "contato"
    PROPOSTA = "proposta"
    NEGOCIACAO = "negociacao"
    GANHO = "ganho"
    PERDIDO = "perdido"


class ActivityType(StrEnum):
    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    NOTE = "note"


def enum_column[E: StrEnum](enum: type[E], name: str) -> Enum:
    # Stored as VARCHAR + CHECK constraint (not a native PostgreSQL ENUM), so adding a value later
    # is a simple migration on both databases. values_callable stores "admin", not "ADMIN".
    return Enum(
        enum,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=20,
        values_callable=lambda members: [member.value for member in members],
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    role: Mapped[UserRole] = mapped_column(enum_column(UserRole, "user_role"))
    password_hash: Mapped[str] = mapped_column(String(255))


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    industry: Mapped[str] = mapped_column(String(80))
    size: Mapped[CompanySize] = mapped_column(enum_column(CompanySize, "company_size"))
    city: Mapped[str] = mapped_column(String(80))
    state: Mapped[str] = mapped_column(String(2))
    website: Mapped[str] = mapped_column(String(255))


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    # Stored lowercased by the API, so this constraint makes e-mails unique ignoring case.
    email: Mapped[str] = mapped_column(String(254), unique=True)
    phone: Mapped[str] = mapped_column(String(20))
    job_title: Mapped[str] = mapped_column(String(80))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)

    # lazy="raise": loading the company must be explicit in the query (joinedload), so a list of
    # 100 contacts can never silently fire 100 extra queries (the N+1 problem).
    company: Mapped[Company] = relationship(lazy="raise")


class Deal(Base):
    __tablename__ = "deals"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    title: Mapped[str] = mapped_column(String(150))
    # Whole reais, as in the contract (amounts in the demo have no cents).
    value: Mapped[int] = mapped_column(Integer)
    stage: Mapped[DealStage] = mapped_column(enum_column(DealStage, "deal_stage"), index=True)
    contact_id: Mapped[str] = mapped_column(ForeignKey("contacts.id"), index=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    expected_close_date: Mapped[datetime] = mapped_column(UTCDateTime())
    closed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())

    contact: Mapped[Contact] = relationship(lazy="raise")
    company: Mapped[Company] = relationship(lazy="raise")

    @property
    def is_closed(self) -> bool:
        return self.stage in (DealStage.GANHO, DealStage.PERDIDO)


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    type: Mapped[ActivityType] = mapped_column(enum_column(ActivityType, "activity_type"))
    contact_id: Mapped[str] = mapped_column(ForeignKey("contacts.id"), index=True)
    deal_id: Mapped[str | None] = mapped_column(ForeignKey("deals.id"))
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    date: Mapped[datetime] = mapped_column(UTCDateTime())
    summary: Mapped[str] = mapped_column(String(255))
