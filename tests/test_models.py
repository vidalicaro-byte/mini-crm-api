from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session

from crm_api.models import Company, CompanySize, Contact, User, UserRole

BRASILIA = timezone(timedelta(hours=-3))


def make_user(session: Session, user_id: str = "usr_t", email: str = "t@example.com") -> User:
    user = User(id=user_id, name="Teste", email=email, role=UserRole.VENDEDOR, password_hash="x")
    session.add(user)
    session.flush()
    return user


def make_company(session: Session) -> Company:
    company = Company(
        id="cmp_t",
        name="Acme",
        industry="Tecnologia",
        size=CompanySize.PEQUENA,
        city="Recife",
        state="PE",
        website="https://acme.example",
    )
    session.add(company)
    session.flush()
    return company


def make_contact(session: Session, created_at: datetime, email: str = "c@example.com") -> Contact:
    contact = Contact(
        id=f"ct_{email}",
        name="Contato",
        email=email,
        phone="",
        job_title="",
        company_id="cmp_t",
        owner_id="usr_t",
        created_at=created_at,
    )
    session.add(contact)
    session.flush()
    return contact


def test_datetimes_come_back_timezone_aware_in_utc(session: Session) -> None:
    make_user(session)
    make_company(session)
    make_contact(session, created_at=datetime(2026, 11, 25, 9, 0, tzinfo=BRASILIA))
    session.expire_all()  # force a real read from the database

    stored = session.scalars(
        select(Contact.created_at).where(Contact.id == "ct_c@example.com")
    ).one()

    assert stored == datetime(2026, 11, 25, 12, 0, tzinfo=UTC)
    assert stored.utcoffset() == timedelta(0)


def test_naive_datetimes_are_rejected(session: Session) -> None:
    make_user(session)
    make_company(session)

    with pytest.raises(StatementError, match="Naive datetime"):
        make_contact(session, created_at=datetime(2026, 11, 25, 12, 0))  # noqa: DTZ001


def test_contact_email_is_unique(session: Session) -> None:
    make_user(session)
    make_company(session)
    make_contact(session, datetime.now(UTC), email="same@example.com")

    with pytest.raises(IntegrityError):
        session.add(
            Contact(
                id="ct_other",
                name="Outro",
                email="same@example.com",
                phone="",
                job_title="",
                company_id="cmp_t",
                owner_id="usr_t",
                created_at=datetime.now(UTC),
            )
        )
        session.flush()


def test_foreign_keys_are_enforced(session: Session) -> None:
    make_user(session)

    with pytest.raises(IntegrityError):
        make_contact(session, datetime.now(UTC))  # company cmp_t doesn't exist


def test_enum_values_outside_the_contract_are_rejected(session: Session) -> None:
    with pytest.raises(IntegrityError):
        session.execute(
            text(
                "INSERT INTO users (id, name, email, role, password_hash) "
                "VALUES ('usr_x', 'X', 'x@example.com', 'superuser', 'x')"
            )
        )
