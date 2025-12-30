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

# Known SQL functions/constants that should not be treated as table names
SQL_FUNCTIONS_AND_CONSTANTS = {
    "current_date",
    "current_time",
    "current_timestamp",
    "now",
    "today",
    "date",  # 'date' is a column name, not a table; if it appears after FROM/JOIN, it's incorrect usage
}


def _normalize_sql(sql: str) -> str:
    s = sql.strip()
    # Strip common code fences.
    if s.lower().startswith("```"):
        s = re.sub(r"^```sql\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"^```", "", s)
        s = re.sub(r"```$", "", s)
    return s.strip()


_TABLE_REF_RE = re.compile(r"\b(?:FROM|JOIN)\s+([a-zA-Z_][\w\.]*)", re.IGNORECASE)
_CTE_NAME_RE = re.compile(r"\bWITH\s+([a-zA-Z_][\w\.]*)\s+AS", re.IGNORECASE)


def _find_cte_names(sql: str) -> set[str]:
    """Extract CTE (Common Table Expression) names from WITH clauses."""
    cte_names: set[str] = set()
    # Match "WITH cte_name AS" patterns
    for m in _CTE_NAME_RE.finditer(sql):
        raw = m.group(1)
        cte_name = raw.split(".")[-1].lower()
        cte_names.add(cte_name)
    
    # Also handle multiple CTEs: "WITH cte1 AS (...), cte2 AS (...)"
    # This is a simplified approach - find all identifiers after WITH and before AS
    if sql.upper().strip().startswith("WITH"):
        # Find the WITH clause section (up to the main SELECT)
        upper_sql = sql.upper()
        with_end = upper_sql.find("SELECT", upper_sql.find("WITH") + 4)
        if with_end > 0:
            with_clause = sql[:with_end]
            # Match patterns like "cte_name AS" or ", cte_name AS"
            cte_pattern = re.compile(r"(?:^|\s|,)\s*([a-zA-Z_][\w\.]*)\s+AS\s*\(", re.IGNORECASE | re.MULTILINE)
            for m in cte_pattern.finditer(with_clause):
                raw = m.group(1)
                cte_name = raw.split(".")[-1].lower()
                cte_names.add(cte_name)
    
    return cte_names


def _find_tables(sql: str) -> Iterable[str]:
    for m in _TABLE_REF_RE.finditer(sql):
        raw = m.group(1)
        # Drop simple qualifiers like schema.table -> table
        table_name = raw.split(".")[-1].lower()
        # Skip SQL functions/constants
        if table_name not in SQL_FUNCTIONS_AND_CONSTANTS:
            yield table_name


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

    # Extract CTE names if the query uses WITH clauses
    cte_names = _find_cte_names(sql)
    
    # Allow both policy tables and CTE names
    allowed = {t.lower() for t in policy.allowed_tables} | cte_names
    unknown = sorted(t for t in tables if t not in allowed)
    if unknown:
        raise UnsafeSQLError(f"Query references non-allowed tables: {unknown}")

    return sql


