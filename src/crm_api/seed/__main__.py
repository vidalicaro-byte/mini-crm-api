"""`uv run python -m crm_api.seed`: reset the database to the demo data."""

from crm_api.db import SessionLocal
from crm_api.seed import load_seed


def main() -> None:
    with SessionLocal() as session:
        counts = load_seed(session)
    print("Seed loaded:", ", ".join(f"{count} {table}" for table, count in counts.items()))


if __name__ == "__main__":
    main()
