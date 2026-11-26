"""Reset the database to the demo data.

uv run python -m crm_api.seed             # replace everything with the demo data
uv run python -m crm_api.seed --if-empty  # only when there are no users yet (container start)
"""

import argparse

from sqlalchemy import select

from crm_api.db import SessionLocal
from crm_api.models import User
from crm_api.seed import load_seed


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--if-empty", action="store_true", help="skip if the database has users")
    args = parser.parse_args(argv)

    with SessionLocal() as session:
        if args.if_empty and session.scalar(select(User.id).limit(1)) is not None:
            print("Seed skipped: the database already has data.")
            return
        counts = load_seed(session)
    print("Seed loaded:", ", ".join(f"{count} {table}" for table, count in counts.items()))


if __name__ == "__main__":
    main()
