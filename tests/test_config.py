import pytest

from crm_api.config import Settings


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("postgres://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        (
            "postgresql://u:p@host/db?sslmode=require",
            "postgresql+psycopg://u:p@host/db?sslmode=require",
        ),
        ("postgresql+psycopg://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        ("sqlite:///./crm.db", "sqlite:///./crm.db"),
    ],
)
def test_database_url_gets_the_psycopg_driver(given: str, expected: str) -> None:
    assert Settings(database_url=given).database_url == expected


def test_cors_origins_accept_a_comma_separated_list() -> None:
    settings = Settings(cors_origins="https://app.example.com/, http://localhost:5173 ,")

    assert settings.cors_origins == ["https://app.example.com", "http://localhost:5173"]


def test_migrations_prefer_the_direct_connection() -> None:
    pooled = "postgresql://u:p@ep-x-pooler.neon.tech/db"
    direct = "postgresql://u:p@ep-x.neon.tech/db"

    assert Settings(database_url=pooled).migrations_database_url.endswith("-pooler.neon.tech/db")
    settings = Settings(database_url=pooled, database_url_unpooled=direct)
    assert settings.migrations_database_url == "postgresql+psycopg://u:p@ep-x.neon.tech/db"
