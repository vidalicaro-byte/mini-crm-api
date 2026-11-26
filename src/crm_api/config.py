from functools import lru_cache
from typing import Annotated, Self

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Only good for local development and tests; production must set JWT_SECRET.
DEV_JWT_SECRET = "dev-only-insecure-secret-change-me-0123456789"  # noqa: S105


class Settings(BaseSettings):
    """Application settings read from environment variables (and an optional .env file)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Mini-CRM API"
    environment: str = "development"
    # SQLite file in the project folder for local development; PostgreSQL in CI and production.
    database_url: str = "sqlite:///./crm.db"
    # Neon: DATABASE_URL is the pooled connection (for the app); migrations should use the direct
    # one. Optional: without it, migrations use DATABASE_URL.
    database_url_unpooled: str | None = None

    # Front ends allowed to call the API from a browser, comma-separated (CORS).
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    jwt_secret: SecretStr = SecretStr(DEV_JWT_SECRET)
    jwt_algorithm: str = "HS256"
    # Same lifetime as the front end's mock API: a working day.
    jwt_expire_minutes: int = 8 * 60

    @field_validator("database_url", "database_url_unpooled")
    @classmethod
    def use_psycopg_driver(cls, url: str | None) -> str | None:
        """Hosts give `postgres://` or `postgresql://` URLs; SQLAlchemy needs the driver name."""
        for prefix in ("postgres://", "postgresql://"):
            if url and url.startswith(prefix):
                return "postgresql+psycopg://" + url.removeprefix(prefix)
        return url

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip().rstrip("/") for origin in value.split(",") if origin.strip()]
        return value

    @property
    def migrations_database_url(self) -> str:
        return self.database_url_unpooled or self.database_url

    @model_validator(mode="after")
    def require_real_secret_in_production(self) -> Self:
        secret = self.jwt_secret.get_secret_value()
        if self.environment == "production" and (secret == DEV_JWT_SECRET or len(secret) < 32):
            raise ValueError("Set JWT_SECRET to a random value of at least 32 characters.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
