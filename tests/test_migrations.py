"""The migrations must build exactly the schema the models describe.

Runs on a throwaway SQLite file. CI also runs `alembic upgrade head` and `alembic check` against
PostgreSQL.
"""

from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect

from crm_api.db import Base, create_db_engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def alembic_config(url: str) -> Config:
    config = Config(toml_file=str(PROJECT_ROOT / "pyproject.toml"))
    config.set_main_option("sqlalchemy.url", url)
    return config


def test_upgrade_matches_models_and_downgrade_removes_everything(tmp_path: Path) -> None:
    url = f"sqlite:///{(tmp_path / 'migrations.db').as_posix()}"
    config = alembic_config(url)
    engine = create_db_engine(url)

    command.upgrade(config, "head")
    with engine.connect() as connection:
        diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    assert diff == [], (
        f"Models and migrations differ; run `alembic revision --autogenerate`: {diff}"
    )

    command.downgrade(config, "base")
    assert set(inspect(engine).get_table_names()) == {"alembic_version"}
    engine.dispose()
