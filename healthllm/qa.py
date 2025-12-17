from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from healthllm.db import connect, init_schema
from healthllm.sql_guard import SqlPolicy, validate_sql
from healthllm.sqlgen_hf import hf_config_from_env, generate_sql_hf
from healthllm.sqlgen_templates import generate_sql_from_templates


@dataclass(frozen=True)
class QAResult:
    sql: str
    dataframe: pd.DataFrame
    scalar_answer: Any | None
    used_provider: str  # "hf" or "templates"


def _execute_sql(con: duckdb.DuckDBPyConnection, sql: str) -> pd.DataFrame:
    rel = con.sql(sql)
    return rel.df()


def answer_steps_question(
    *,
    question: str,
    db_path: str | Path = "data/ask_my_health.duckdb",
    force_templates: bool = False,
) -> QAResult:
    """
    Answer a steps-only question by generating safe SQL and executing locally in DuckDB.

    Provider selection:
    - If HF_TOKEN is set (and not force_templates): use HF text-to-SQL
    - Else: use small template router
    """
    question = question.strip()
    if not question:
        raise ValueError("Question is empty.")

    hf_cfg = None if force_templates else hf_config_from_env()
    used_provider = "templates"

    if hf_cfg is not None:
        sql = generate_sql_hf(question, hf_cfg)
        used_provider = "hf"
    else:
        match = generate_sql_from_templates(question)
        sql = match.sql

    sql = validate_sql(sql, SqlPolicy(allowed_tables=("daily_steps",)))

    con = connect(db_path)
    init_schema(con)
    df = _execute_sql(con, sql)
    con.close()

    scalar = None
    if df.shape[0] == 1 and "answer" in df.columns:
        scalar = df.iloc[0]["answer"]

    return QAResult(sql=sql, dataframe=df, scalar_answer=scalar, used_provider=used_provider)


