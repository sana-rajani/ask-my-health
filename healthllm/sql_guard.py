from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

class UnsafeSQLError(ValueError):
    pass


@dataclass(frozen=True)
class SqlPolicy:
    allowed_tables: tuple[str, ...] = ("daily_steps",)


DISALLOWED_KEYWORDS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "CREATE",
    "DROP",
    "ATTACH",
    "COPY",
    "ALTER",
    "PRAGMA",
)


def _normalize_sql(sql: str) -> str:
    s = sql.strip()
    # Strip common code fences.
    if s.lower().startswith("```"):
        s = re.sub(r"^```sql\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"^```", "", s)
        s = re.sub(r"```$", "", s)
    return s.strip()


_TABLE_REF_RE = re.compile(r"\b(?:FROM|JOIN)\s+([a-zA-Z_][\w\.]*)", re.IGNORECASE)


def _find_tables(sql: str) -> Iterable[str]:
    for m in _TABLE_REF_RE.finditer(sql):
        raw = m.group(1)
        # Drop simple qualifiers like schema.table -> table
        yield raw.split(".")[-1]


def validate_sql(sql: str, policy: SqlPolicy = SqlPolicy()) -> str:
    """
    Validate that SQL is safe for this app.

    Requirements:
    - single statement
    - SELECT-only (CTEs ok)
    - only allow-listed tables
    """
    sql = _normalize_sql(sql)
    if not sql:
        raise UnsafeSQLError("Empty SQL.")

    upper = sql.upper()
    if not upper.lstrip().startswith("SELECT") and not upper.lstrip().startswith("WITH"):
        raise UnsafeSQLError("Only SELECT queries are allowed.")

    # Prevent multiple statements.
    # (We allow a single trailing semicolon, but not internal statement separators.)
    stripped = sql.strip()
    if ";" in stripped[:-1]:
        raise UnsafeSQLError("Only a single SQL statement is allowed.")
    if stripped.endswith(";"):
        sql = stripped[:-1].strip()
        upper = sql.upper()

    for kw in DISALLOWED_KEYWORDS:
        if kw in upper:
            raise UnsafeSQLError(f"Disallowed keyword found: {kw}")

    tables = {t.lower() for t in _find_tables(sql)}
    if not tables:
        raise UnsafeSQLError("No table referenced.")

    allowed = {t.lower() for t in policy.allowed_tables}
    unknown = sorted(t for t in tables if t not in allowed)
    if unknown:
        raise UnsafeSQLError(f"Query references non-allowed tables: {unknown}")

    return sql


