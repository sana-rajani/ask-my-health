from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd

from healthllm.db import Schema, connect, init_schema


HK_STEP_TYPE = "HKQuantityTypeIdentifierStepCount"


@dataclass(frozen=True)
class IngestResult:
    days: int
    records_seen: int
    step_records_seen: int


def _iter_records(xml_path: Path) -> Iterable[dict[str, str]]:
    # Stream parse to handle large exports.
    for _event, elem in ET.iterparse(str(xml_path), events=("end",)):
        if elem.tag == "Record":
            yield dict(elem.attrib)
            elem.clear()


def ingest_steps_export_xml(
    *,
    xml_path: str | Path,
    db_path: str | Path = "data/ask_my_health.duckdb",
    overwrite: bool = True,
) -> IngestResult:
    """
    Parse Apple Health export.xml and populate daily_steps(date, steps).

    Notes (v1):
    - We bucket by the local date embedded in startDate (YYYY-MM-DD prefix).
    - We sum all step records into that day.
    """
    xml_path = Path(xml_path).expanduser().resolve()
    db_path = Path(db_path).expanduser().resolve()

    totals: dict[str, float] = {}
    records_seen = 0
    step_records_seen = 0

    for attrs in _iter_records(xml_path):
        records_seen += 1
        if attrs.get("type") != HK_STEP_TYPE:
            continue

        step_records_seen += 1
        start = attrs.get("startDate")
        value = attrs.get("value")
        if not start or value is None:
            continue

        day = start[:10]  # 'YYYY-MM-DD'
        try:
            v = float(value)
        except ValueError:
            continue

        totals[day] = totals.get(day, 0.0) + v

    df = pd.DataFrame(
        {"date": pd.to_datetime(list(totals.keys()), errors="coerce"), "steps": list(totals.values())}
    ).dropna(subset=["date"])

    # Store as integers (steps are counts).
    df["steps"] = df["steps"].round().astype("int64")

    con = connect(db_path)
    init_schema(con)

    if overwrite:
        con.execute(f"DELETE FROM {Schema.DAILY_STEPS_TABLE}")

    con.register("df_daily_steps", df)
    con.execute(
        f"""
        INSERT INTO {Schema.DAILY_STEPS_TABLE}
        SELECT CAST(date AS DATE) AS date, CAST(steps AS BIGINT) AS steps
        FROM df_daily_steps
        """
    )
    
    # Set metadata to track source
    con.execute(f"DELETE FROM {Schema.DATA_SOURCE_TABLE}")
    con.execute(
        f"""
        INSERT INTO {Schema.DATA_SOURCE_TABLE} (id, source_type, source_path, last_updated)
        VALUES (1, 'export_xml', ?, ?)
        """,
        [str(xml_path), datetime.now()]
    )
    con.close()

    return IngestResult(days=int(df.shape[0]), records_seen=records_seen, step_records_seen=step_records_seen)


