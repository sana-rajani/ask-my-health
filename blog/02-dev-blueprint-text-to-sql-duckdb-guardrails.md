# Developer blueprint: LLM → SQL over DuckDB (steps-only Apple Health)

This repo is a **local-first** pattern for “ask questions about my data” where the LLM is *not* the calculator.

## Why LLM → SQL?

LLMs are great at translating intent (“steps this year”) into a formal query, but they’re not reliable calculators.

So the core contract is:

- **LLM**: generate a *single* DuckDB SQL `SELECT` query.
- **DuckDB**: execute the query and compute the true numeric answer.
- **App**: show the SQL for transparency.

## Architecture (v1)

- Ingest: Apple Health `export.xml` → aggregate into `daily_steps(date, steps)`
- Q&A: question → SQL generator (HF model or templates) → SQL guardrails → DuckDB execute → display result

## Data model

`daily_steps(date DATE, steps BIGINT)` is intentionally simple so most queries are `SUM/AVG/GROUP BY`.

Keeping a curated table reduces:

- prompt complexity
- query complexity
- failure rate

## SQL safety guardrails

The app enforces:

- **SELECT-only** queries
- **table allow-list** (`daily_steps` only in v1)
- blocks common write/escape keywords: `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `DROP`, `ATTACH`, `COPY`, `ALTER`, `PRAGMA`

## Provider strategy

v1 supports:

- **Hosted HF** (default model: `deepseek-ai/DeepSeek-V3.2:novita`)
- **No-token fallback** using a small template router for “golden questions” so demo/testing always works

## Testing strategy

- Deterministic **dummy dataset** with known totals (so you can test answers)
- Small synthetic XML fixture for ingestion tests
- Guardrail tests (reject non-SELECT SQL, reject other tables)


