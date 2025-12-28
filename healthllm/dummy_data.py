from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import math
from pathlib import Path
import random

import pandas as pd

from healthllm.db import Schema, connect, init_schema


@dataclass(frozen=True)
class DummyConfig:
    days: int = 180
    seed: int = 42
    start_date: date | None = None


def generate_daily_steps(cfg: DummyConfig) -> pd.DataFrame:
    """Generate deterministic daily step totals for demo/testing."""
    start = cfg.start_date or (date.today() - timedelta(days=cfg.days - 1))
    rng = random.Random(cfg.seed)

    dates = [start + timedelta(days=i) for i in range(cfg.days)]

    # A stable, human-looking pattern: weekly rhythm + gentle trend + noise.
    weekday_boost = [0.95, 1.0, 1.05, 1.03, 1.02, 1.15, 1.1]  # Mon..Sun
    base = 7200
    trend_start, trend_end = -500.0, 700.0
    noise_scale = 900.0

    steps = []
    for i, d in enumerate(dates):
        mult = weekday_boost[d.weekday()]
        frac = 0.0 if cfg.days <= 1 else i / (cfg.days - 1)
        trend = trend_start + (trend_end - trend_start) * frac
        noise = rng.gauss(0.0, noise_scale)
        # Add a subtle seasonal wave so plots look nicer.
        seasonal = 250.0 * math.sin(2 * math.pi * frac)
        s = (base + trend + seasonal + noise) * mult
        steps.append(int(max(0, round(s))))

    return pd.DataFrame({"date": pd.to_datetime(dates), "steps": steps})


def build_dummy_db(db_path: str | Path, cfg: DummyConfig = DummyConfig()) -> Path:
    """Create/overwrite a DuckDB file populated with dummy daily_steps."""
    path = Path(db_path).expanduser().resolve()

    con = connect(path)
    init_schema(con)

    df = generate_daily_steps(cfg)

    # Overwrite the table contents for reproducibility.
    con.execute(f"DELETE FROM {Schema.DAILY_STEPS_TABLE}")
    con.register("df_daily_steps", df)
    con.execute(
        f"INSERT INTO {Schema.DAILY_STEPS_TABLE} SELECT CAST(date AS DATE) AS date, CAST(steps AS BIGINT) AS steps FROM df_daily_steps"
    )
    con.close()
    return path


