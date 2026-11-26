"""Database engine, session factory and the declarative base shared by every model."""

from collections.abc import Iterator
from typing import Any

from sqlalchemy import Connection, Engine, MetaData, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from crm_api.config import get_settings
from crm_api.text import SQLITE_COLLATION, sqlite_collation

# Predictable constraint names, so Alembic can find (and drop) them in later migrations.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def create_db_engine(url: str, **kwargs: Any) -> Engine:
    if url.startswith("sqlite"):
        # FastAPI may use a session in a different thread from the one that opened it.
        kwargs.setdefault("connect_args", {"check_same_thread": False})
    else:
        # Serverless Postgres (Neon) closes idle connections when it scales to zero; test each
        # pooled connection before use instead of failing the first request after a pause.
        kwargs.setdefault("pool_pre_ping", True)
        if "-pooler." in url:
            # PgBouncer in transaction mode: don't rely on server-side prepared statements.
            kwargs.setdefault("connect_args", {"prepare_threshold": None})
    engine = create_engine(url, **kwargs)
    if engine.dialect.name == "sqlite":
        event.listen(engine, "connect", _configure_sqlite_connection)
        event.listen(engine, "begin", _begin_sqlite_transaction)
    return engine


def _configure_sqlite_connection(dbapi_connection: Any, _record: Any) -> None:
    # Python's sqlite3 driver starts transactions on its own terms, which breaks SAVEPOINTs (and
    # so the per-test rollback). Turn that off and let SQLAlchemy emit BEGIN itself (below).
    dbapi_connection.isolation_level = None
    # SQLite's built-in lower() only knows ASCII ("Á" stays "Á"); use Python's, like PostgreSQL.
    dbapi_connection.create_function("lower", 1, _lower, deterministic=True)
    dbapi_connection.create_collation(SQLITE_COLLATION, sqlite_collation)
    cursor = dbapi_connection.cursor()
    # SQLite ignores foreign keys unless asked, per connection; PostgreSQL always enforces them.
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _lower(value: str | None) -> str | None:
    return value.lower() if value is not None else None


def _begin_sqlite_transaction(connection: Connection) -> None:
    connection.exec_driver_sql("BEGIN")


engine = create_db_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed afterwards."""
    with SessionLocal() as session:
        yield session
