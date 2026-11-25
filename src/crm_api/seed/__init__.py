"""Demo data: the same fictional records the Mini-CRM front end ships with."""

import json
from datetime import UTC, datetime, timedelta
from importlib.resources import files
from typing import Any

from sqlalchemy import delete
from sqlalchemy.orm import Session

from crm_api.models import Activity, Company, Contact, Deal, User
from crm_api.security import hash_password

DEMO_PASSWORD = "demo1234"  # noqa: S105  (public demo credential, shown in the README)

# Children before parents, so deleting never breaks a foreign key.
_TABLES_IN_DELETE_ORDER = (Activity, Deal, Contact, Company, User)


def read_seed() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(
        files("crm_api.seed").joinpath("seed.json").read_text(encoding="utf-8")
    )
    return data


def parse_datetime(iso: str) -> datetime:
    """Parse an ISO 8601 string from the seed file as an aware UTC datetime."""
    return datetime.fromisoformat(iso).astimezone(UTC)


def load_seed(session: Session, now: datetime | None = None) -> dict[str, int]:
    """Replace every row with the demo data and return how many rows each table got.

    Dates move forward by the time elapsed since the seed was generated (as the front end's mock
    does), so "the last 30 days" always has data however old the seed file is.
    """
    now = now or datetime.now(UTC)
    data = read_seed()
    offset: timedelta = now - parse_datetime(data["referenceDate"])

    def shift(iso: str) -> datetime:
        return parse_datetime(iso) + offset

    for table in _TABLES_IN_DELETE_ORDER:
        session.execute(delete(table))

    # Every demo user shares one password, so hash it once (Argon2 is slow on purpose).
    password_hash = hash_password(DEMO_PASSWORD)
    session.add_all(
        User(
            id=u["id"],
            name=u["name"],
            email=u["email"].lower(),
            role=u["role"],
            password_hash=password_hash,
        )
        for u in data["users"]
    )
    session.add_all(
        Company(
            id=c["id"],
            name=c["name"],
            industry=c["industry"],
            size=c["size"],
            city=c["city"],
            state=c["state"],
            website=c["website"],
        )
        for c in data["companies"]
    )
    session.flush()
    session.add_all(
        Contact(
            id=c["id"],
            name=c["name"],
            email=c["email"].lower(),
            phone=c["phone"],
            job_title=c["jobTitle"],
            company_id=c["companyId"],
            owner_id=c["ownerId"],
            created_at=shift(c["createdAt"]),
        )
        for c in data["contacts"]
    )
    session.flush()
    session.add_all(
        Deal(
            id=d["id"],
            title=d["title"],
            value=d["value"],
            stage=d["stage"],
            contact_id=d["contactId"],
            company_id=d["companyId"],
            owner_id=d["ownerId"],
            created_at=shift(d["createdAt"]),
            expected_close_date=shift(d["expectedCloseDate"]),
            closed_at=shift(d["closedAt"]) if d["closedAt"] else None,
        )
        for d in data["deals"]
    )
    session.flush()
    session.add_all(
        Activity(
            id=a["id"],
            type=a["type"],
            contact_id=a["contactId"],
            deal_id=a["dealId"],
            owner_id=a["ownerId"],
            date=shift(a["date"]),
            summary=a["summary"],
        )
        for a in data["activities"]
    )
    session.commit()
    return {
        key: len(data[key]) for key in ("users", "companies", "contacts", "deals", "activities")
    }
