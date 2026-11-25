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
