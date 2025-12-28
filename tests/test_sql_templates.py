from __future__ import annotations

import pytest

from healthllm.sqlgen_templates import NoTemplateMatchError, generate_sql_from_templates


def test_templates_steps_this_year() -> None:
    m = generate_sql_from_templates("How many steps did I walk this year?")
    assert "SUM" in m.sql.upper()
    assert "date_trunc('year'" in m.sql


def test_templates_top_days_default() -> None:
    m = generate_sql_from_templates("What are my top days by steps?")
    assert "ORDER BY" in m.sql.upper()
    assert "LIMIT 10" in m.sql.upper()


def test_templates_reject_non_steps() -> None:
    with pytest.raises(NoTemplateMatchError):
        generate_sql_from_templates("How many hours did I sleep?")


