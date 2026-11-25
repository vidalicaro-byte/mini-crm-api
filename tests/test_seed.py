from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crm_api.models import Activity, Company, Contact, Deal, DealStage, User, UserRole
from crm_api.security import verify_password
from crm_api.seed import DEMO_PASSWORD, load_seed, parse_datetime, read_seed
from tests.conftest import NOW


def count(session: Session, model: type) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def test_seed_loads_every_record(seeded: Session) -> None:
    assert count(seeded, User) == 5
    assert count(seeded, Company) == 40
    assert count(seeded, Contact) == 180
    assert count(seeded, Deal) == 90
    assert count(seeded, Activity) == 300


def test_seed_can_run_twice(seeded: Session) -> None:
    counts = load_seed(seeded, now=NOW)

    assert counts["contacts"] == 180
    assert count(seeded, Contact) == 180


def test_dates_move_forward_to_now(seeded: Session) -> None:
    reference = read_seed()["referenceDate"]
    first = read_seed()["contacts"][0]
    contact = seeded.get_one(Contact, first["id"])

    # The seed was generated at `referenceDate`; every date keeps its distance from it.
    expected = parse_datetime(first["createdAt"]) + (NOW - parse_datetime(reference))
    assert contact.created_at == expected
    latest = seeded.scalar(select(func.max(Contact.created_at)))
    assert latest is not None
    assert latest <= NOW + timedelta(seconds=1)


def test_closed_deals_have_a_closing_date_and_open_ones_dont(seeded: Session) -> None:
    for deal in seeded.scalars(select(Deal)):
        closed = deal.stage in (DealStage.GANHO, DealStage.PERDIDO)
        assert (deal.closed_at is not None) == closed, deal.id


def test_demo_users_can_use_the_demo_password(seeded: Session) -> None:
    admin = seeded.scalars(select(User).where(User.email == "marina@minicrm.demo")).one()

    assert admin.role is UserRole.ADMIN
    assert verify_password(DEMO_PASSWORD, admin.password_hash)
    assert not verify_password("wrong-password", admin.password_hash)


def test_emails_are_stored_lowercase(seeded: Session) -> None:
    emails = seeded.scalars(select(Contact.email)).all()

    assert all(email == email.lower() for email in emails)
