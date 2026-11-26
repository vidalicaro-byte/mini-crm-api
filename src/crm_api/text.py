"""Sorting text the way a Brazilian reader expects: "Ágata" next to "Agnes", "ana" next to "Ana".

Database defaults differ (SQLite compares bytes, so "Á" lands after "Z"; PostgreSQL depends on
how the server was installed), so text columns are sorted with an explicit collation:
PostgreSQL's ICU "pt-BR" collation, and on SQLite an equivalent function registered in db.py.
"""

import unicodedata
from typing import Any

from sqlalchemy import String
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.compiler import SQLCompiler
from sqlalchemy.sql.expression import ColumnElement
from sqlalchemy.sql.visitors import InternalTraversal

SQLITE_COLLATION = "pt_br"
POSTGRES_COLLATION = '"pt-BR-x-icu"'


# Unicode's default order (used by ICU, PostgreSQL and the browser's Intl.Collator) puts spaces
# and punctuation before digits and letters, in this order: "Costa-Barros" before "Costa, Xavier".
# ASCII order differs ("," < "-"), so map them to low code points that follow Unicode's order.
_PUNCTUATION_ORDER = " _-,;:!?.'\"()[]{}@*/\\&#%`^+<=>|~$"
_PUNCTUATION_RANK = {ord(char): chr(rank + 1) for rank, char in enumerate(_PUNCTUATION_ORDER)}


def collation_key(text: str) -> tuple[str, str]:
    """Letters first, ignoring accents and case; accents and case only break ties."""
    decomposed = unicodedata.normalize("NFKD", text)
    base = "".join(char for char in decomposed if not unicodedata.combining(char)).casefold()
    return base.translate(_PUNCTUATION_RANK), text


def sqlite_collation(left: str, right: str) -> int:
    left_key, right_key = collation_key(left), collation_key(right)
    return (left_key > right_key) - (left_key < right_key)


class natural_sort(ColumnElement[str]):  # noqa: N801  (reads like a SQL function in queries)
    """`ORDER BY natural_sort(Contact.name)` sorts with the pt-BR collation on every database."""

    inherit_cache = True
    type = String()
    _traverse_internals = [("column", InternalTraversal.dp_clauseelement)]  # noqa: RUF012

    def __init__(self, column: ColumnElement[str] | Any) -> None:
        self.column = column


@compiles(natural_sort)
def _compile_default(element: natural_sort, compiler: SQLCompiler, **kw: Any) -> str:
    return compiler.process(element.column, **kw)


@compiles(natural_sort, "postgresql")
def _compile_postgresql(element: natural_sort, compiler: SQLCompiler, **kw: Any) -> str:
    return f"{compiler.process(element.column, **kw)} COLLATE {POSTGRES_COLLATION}"


@compiles(natural_sort, "sqlite")
def _compile_sqlite(element: natural_sort, compiler: SQLCompiler, **kw: Any) -> str:
    return f"{compiler.process(element.column, **kw)} COLLATE {SQLITE_COLLATION}"
