from __future__ import annotations

import argparse
from pathlib import Path

from healthllm.dummy_data import DummyConfig, build_dummy_db
from healthllm.ingest_steps import ingest_steps_export_xml


def main() -> None:
    parser = argparse.ArgumentParser(prog="healthllm", description="ask-my-health utilities (steps-only MVP).")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_dummy = sub.add_parser("init-dummy", help="Create a DuckDB file with deterministic dummy daily_steps.")
    p_dummy.add_argument("--db", type=str, default="data/ask_my_health.duckdb", help="Path to DuckDB file.")
    p_dummy.add_argument("--days", type=int, default=180, help="Number of days to generate.")
    p_dummy.add_argument("--seed", type=int, default=42, help="Random seed for deterministic data.")

    p_ingest = sub.add_parser("ingest-steps", help="Ingest Apple Health export.xml (steps only) into DuckDB.")
    p_ingest.add_argument("--xml", type=str, required=True, help="Path to apple_health_export/export.xml.")
    p_ingest.add_argument("--db", type=str, default="data/ask_my_health.duckdb", help="Path to DuckDB file.")
    p_ingest.add_argument(
        "--overwrite",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Overwrite existing daily_steps (default: true).",
    )

    args = parser.parse_args()

    if args.cmd == "init-dummy":
        path = build_dummy_db(Path(args.db), DummyConfig(days=args.days, seed=args.seed))
        print(f"Wrote dummy data to {path}")
        return

    if args.cmd == "ingest-steps":
        res = ingest_steps_export_xml(xml_path=args.xml, db_path=args.db, overwrite=args.overwrite)
        print(
            f"Ingested {res.step_records_seen} step records "
            f"({res.records_seen} total records scanned) into {res.days} days"
        )
        return

    raise RuntimeError(f"Unknown command: {args.cmd}")


if __name__ == "__main__":
    main()


