from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb


@dataclass(frozen=True)
class Schema:
    DAILY_STEPS_TABLE: str = "daily_steps"
    DATA_SOURCE_TABLE: str = "data_source"


def ensure_parent_dir(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)


def connect(db_path: str | Path) -> duckdb.DuckDBPyConnection:
    path = Path(db_path).expanduser().resolve()
    ensure_parent_dir(path)
    return duckdb.connect(str(path))


def init_schema(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_steps (
          date DATE PRIMARY KEY,
          steps BIGINT
        )
        """
    )
    # Add metadata table to track data source
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS data_source (
          id INTEGER PRIMARY KEY,
          source_type TEXT NOT NULL,
          source_path TEXT,
          last_updated TIMESTAMP NOT NULL
        )
        """
    )


