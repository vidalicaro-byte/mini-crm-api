from sqlalchemy import String, column, select, table
from sqlalchemy.dialects import postgresql, sqlite

from crm_api.text import collation_key, natural_sort


def test_collation_ignores_accents_and_case_first() -> None:
    names = ["Zélia", "ana", "Álvaro", "Ana", "Agnes", "Ágata", "beatriz"]

    assert sorted(names, key=collation_key) == [
        "Ágata",
        "Agnes",
        "Álvaro",
        "Ana",
        "ana",
        "beatriz",
        "Zélia",
    ]


def test_natural_sort_compiles_per_database() -> None:
    name = column("name", String)
    query = select(name).select_from(table("t")).order_by(natural_sort(name))

    postgres_sql = str(query.compile(dialect=postgresql.dialect()))  # type: ignore[no-untyped-call]
    sqlite_sql = str(query.compile(dialect=sqlite.dialect()))

    assert 'COLLATE "pt-BR-x-icu"' in postgres_sql
    assert "COLLATE pt_br" in sqlite_sql


def test_punctuation_sorts_like_unicode() -> None:
    names = ["Costa, Xavier e Albuquerque", "Costa-Barros", "Costa Lima", "Costa2", "Costas"]

    assert sorted(names, key=collation_key) == [
        "Costa Lima",
        "Costa-Barros",
        "Costa, Xavier e Albuquerque",
        "Costa2",
        "Costas",
    ]
