"""Shared fixtures.

Tests run against in-memory SQLite by default. Set TEST_DATABASE_URL to run the same suite against
PostgreSQL (CI does both). The schema and the demo data are created once per run; each test runs
inside a transaction that is rolled back at the end, so tests never see each other's changes.
"""

import os
from collections.abc import Callable, Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from crm_api import models  # noqa: F401  (registers every table on Base.metadata)
from crm_api.config import Settings
from crm_api.db import Base, create_db_engine, get_session
from crm_api.main import create_app
from crm_api.seed import DEMO_PASSWORD, load_seed

# A fixed "now" keeps date-dependent assertions deterministic.
NOW = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        engine = create_db_engine(Settings(database_url=url).database_url)
    else:
        # One shared connection, or every new connection would get its own empty in-memory database.
        engine = create_db_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        load_seed(session, now=NOW)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    with engine.connect() as connection:
        transaction = connection.begin()
        # commit() inside the code under test only releases a savepoint; the outer rollback wins.
        with Session(
            bind=connection,
            join_transaction_mode="create_savepoint",
            autoflush=False,
            expire_on_commit=False,
        ) as session:
            yield session
        transaction.rollback()


@pytest.fixture
def seeded(session: Session) -> Session:
    """A session on the demo data (loaded once per run). Named for readability in tests."""
    return session


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as test_client:
        yield test_client


ADMIN_EMAIL = "marina@minicrm.demo"
SELLER_EMAIL = "rafael@minicrm.demo"


@pytest.fixture
def login(client: TestClient, seeded: Session) -> Callable[[str], dict[str, str]]:
    """Sign in as a demo user and get the Authorization header for the next requests."""

    def _login(email: str) -> dict[str, str]:
        response = client.post("/api/auth/login", json={"email": email, "password": DEMO_PASSWORD})
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['token']}"}

    return _login


@pytest.fixture
def admin_headers(login: Callable[[str], dict[str, str]]) -> dict[str, str]:
    return login(ADMIN_EMAIL)


@pytest.fixture
def seller_headers(login: Callable[[str], dict[str, str]]) -> dict[str, str]:
    return login(SELLER_EMAIL)
