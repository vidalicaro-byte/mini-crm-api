from functools import lru_cache
from typing import Self

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Only good for local development and tests; production must set JWT_SECRET.
DEV_JWT_SECRET = "dev-only-insecure-secret-change-me-0123456789"  # noqa: S105


class Settings(BaseSettings):
    """Application settings read from environment variables (and an optional .env file)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Mini-CRM API"
    environment: str = "development"
    # SQLite file in the project folder for local development; PostgreSQL in CI and production.
    database_url: str = "sqlite:///./crm.db"

    jwt_secret: SecretStr = SecretStr(DEV_JWT_SECRET)
    jwt_algorithm: str = "HS256"
    # Same lifetime as the front end's mock API: a working day.
    jwt_expire_minutes: int = 8 * 60

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, url: str) -> str:
        """Hosts give `postgres://` or `postgresql://` URLs; SQLAlchemy needs the driver name."""
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url.removeprefix(prefix)
        return url

    @model_validator(mode="after")
    def require_real_secret_in_production(self) -> Self:
        secret = self.jwt_secret.get_secret_value()
        if self.environment == "production" and (secret == DEV_JWT_SECRET or len(secret) < 32):
            raise ValueError("Set JWT_SECRET to a random value of at least 32 characters.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
