from __future__ import annotations

from healthllm.dummy_data import DummyConfig, generate_daily_steps


def test_generate_daily_steps_deterministic() -> None:
    df1 = generate_daily_steps(DummyConfig(days=30, seed=123))
    df2 = generate_daily_steps(DummyConfig(days=30, seed=123))
    assert df1.equals(df2)
    assert df1.shape[0] == 30
    assert (df1["steps"] >= 0).all()


