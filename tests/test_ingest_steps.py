from __future__ import annotations

from pathlib import Path

import duckdb

from healthllm.ingest_steps import ingest_steps_export_xml


def test_ingest_steps_export_xml_aggregates_by_day(tmp_path: Path) -> None:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <HealthData locale="en_US">
      <Record type="HKQuantityTypeIdentifierStepCount" sourceName="iPhone" unit="count" value="100"
              startDate="2025-01-01 10:00:00 -0700" endDate="2025-01-01 10:05:00 -0700"/>
      <Record type="HKQuantityTypeIdentifierStepCount" sourceName="iPhone" unit="count" value="50"
              startDate="2025-01-01 12:00:00 -0700" endDate="2025-01-01 12:05:00 -0700"/>
      <Record type="HKQuantityTypeIdentifierStepCount" sourceName="iPhone" unit="count" value="25"
              startDate="2025-01-02 09:00:00 -0700" endDate="2025-01-02 09:05:00 -0700"/>
      <Record type="HKQuantityTypeIdentifierHeartRate" sourceName="Watch" unit="count/min" value="80"
              startDate="2025-01-01 10:00:00 -0700" endDate="2025-01-01 10:01:00 -0700"/>
    </HealthData>
    """

    xml_path = tmp_path / "export.xml"
    xml_path.write_text(xml, encoding="utf-8")
    db_path = tmp_path / "test.duckdb"

    res = ingest_steps_export_xml(xml_path=xml_path, db_path=db_path, overwrite=True)
    assert res.days == 2
    assert res.step_records_seen == 3

    con = duckdb.connect(str(db_path))
    rows = con.execute("SELECT date, steps FROM daily_steps ORDER BY date").fetchall()
    assert rows[0][1] == 150
    assert rows[1][1] == 25
    con.close()


