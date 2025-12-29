# ask-my-health
Ask questions about your Apple Health export and get reliable, SQL-backed insights locally—a **wellness-whisperer** for your data.

This is a **steps-only v0.1** MVP:

- Ingest Apple Health `export.xml` into a local DuckDB
- Build a simple curated table: `daily_steps(date, steps)`
- Ask questions like “how many steps did I walk this year?”
- The LLM generates **SQL**; DuckDB executes it for correct totals

## Privacy

- Your Apple Health export stays on your machine.
- If you enable the hosted Hugging Face model, the app sends only:
  - your question
  - the table schema (column names/types)

## Quickstart (dev)

```bash
cd /Users/sana.rajani/Desktop/repos/ask-my-health
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
streamlit run app.py
```

## Hugging Face (optional)

Set:

- `HF_TOKEN` (your Hugging Face access token)
- `HF_MODEL` (optional, default `deepseek-ai/DeepSeek-V3.2:novita`)

If `HF_TOKEN` is not set, the app falls back to a small set of built-in SQL templates for common step questions.

## Blogs

- `blog/01-making-health-data-searchable.md` (non-technical)
- `blog/02-dev-blueprint-text-to-sql-duckdb-guardrails.md` (developer)
