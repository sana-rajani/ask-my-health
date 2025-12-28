from __future__ import annotations

import pytest

from healthllm.sql_guard import SqlPolicy, UnsafeSQLError, validate_sql


def test_validate_sql_allows_simple_select() -> None:
    sql = "SELECT SUM(steps) AS answer FROM daily_steps"
    out = validate_sql(sql, SqlPolicy(allowed_tables=("daily_steps",)))
    assert "SELECT" in out.upper()


def test_validate_sql_rejects_non_select() -> None:
    with pytest.raises(UnsafeSQLError):
        validate_sql("DELETE FROM daily_steps", SqlPolicy(allowed_tables=("daily_steps",)))


def test_validate_sql_rejects_other_tables() -> None:
    with pytest.raises(UnsafeSQLError):
        validate_sql("SELECT * FROM users", SqlPolicy(allowed_tables=("daily_steps",)))


