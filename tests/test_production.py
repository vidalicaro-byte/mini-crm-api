"""Pieces that only matter in production: CORS, the root redirect, engine options, seeding."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from crm_api.config import Settings, get_settings
from crm_api.db import create_db_engine
from crm_api.main import create_app
from crm_api.models import Contact
from crm_api.seed import __main__ as seed_cli

FRONT_END = "https://mini-crm.example.com"


@pytest.fixture
def cors_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("CORS_ORIGINS", FRONT_END)
    get_settings.cache_clear()
    try:
        return TestClient(create_app())
    finally:
        get_settings.cache_clear()


def preflight(client: TestClient, origin: str) -> dict[str, str]:
    response = client.options(
        "/api/auth/login",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    return dict(response.headers)


def test_the_front_end_may_call_the_api(cors_client: TestClient) -> None:
    headers = preflight(cors_client, FRONT_END)

    assert headers["access-control-allow-origin"] == FRONT_END


def test_other_sites_may_not(cors_client: TestClient) -> None:
    headers = preflight(cors_client, "https://evil.example.com")

    assert "access-control-allow-origin" not in headers


def test_root_redirects_to_the_docs(client: TestClient) -> None:
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/docs"


def test_postgres_engines_check_connections_before_use() -> None:
    engine = create_db_engine("postgresql+psycopg://u:p@ep-x-pooler.neon.tech/db")

    assert engine.pool._pre_ping
    engine.dispose()


def test_production_settings_need_no_database_to_validate() -> None:
    settings = Settings(environment="production", jwt_secret="s" * 40)

    assert settings.cors_origins == ["http://localhost:5173"]


def test_seed_if_empty_skips_a_database_with_data(
    seeded: Session, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(seed_cli, "SessionLocal", lambda: _NonClosing(seeded))
    seeded.get_one(Contact, "ct_1").name = "Marcado pelo teste"  # a change a reseed would undo
    seeded.flush()

    seed_cli.main(["--if-empty"])

    assert "skipped" in capsys.readouterr().out
    assert seeded.scalar(select(Contact.name).where(Contact.id == "ct_1")) == "Marcado pelo teste"


class _NonClosing:
    """Hands the test's session to code that uses `with SessionLocal() as session`."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def __enter__(self) -> Session:
        return self.session

    def __exit__(self, *_exc: object) -> None:
        return None
