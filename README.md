# ask-my-health
Have a conversation with your Apple Health export and get reliable, SQL-backed insights locally—a **wellness-whisperer** for your data.

This is a **steps-only v1** MVP:

- Ingest Apple Health `export.xml` into a local DuckDB
- Build a simple curated table: `daily_steps(date, steps)`
- Ask questions like "how many steps did I walk this year?"
- The LLM generates **SQL**; DuckDB executes it for correct totals
- **Features**: Data source tracking, sample queries, and improved error handling

## Privacy

- Your Apple Health export stays on your machine.
- If you enable the hosted Hugging Face model, the app sends only:
  - your question
  - the table schema (column names/types)

## Quickstart (dev)

```bash
cd ask-my-health
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
streamlit run app.py
```

## Getting Your Apple Health Data

### Method 1: Export from the Health App (XML)

1. **Open Health**: Launch the Apple Health app on your iPhone
2. **Go to Profile**: Tap your profile picture or initials in the top-right corner
3. **Select Export**: Scroll down and tap on **Export All Health Data**
4. **Confirm**: Tap **Export**, then choose how to share or save the generated XML file
5. **Save**: Save to iCloud Drive or anywhere on your Mac and note the path
6. **Unzip**: If you saved it to Files, find the zip file, tap it to unzip, and you'll find `export.xml` and other files

**Example workflow:**
- Export from Health app → Save to Files → Choose iCloud Drive
- On your Mac, the file will be in: `/Users/your-username/Library/Mobile Documents/com~apple~CloudDocs/Documents/health/health data/apple_health_export_2025/export.xml`
- Other example paths:
  - Local: `/Users/your-username/Downloads/apple_health_export/export.xml`
  - Relative: `data/raw_data/december_2025/export.xml`

## Data Setup

The app supports two ways to add data:

1. **Generate sample data** (recommended for first run): Use the sidebar to create dummy step data for testing
2. **Import your Apple Health export.xml**: Provide the path to your `export.xml` file in the sidebar (see example paths above)

The app tracks the data source and displays it in the sidebar.

## Hugging Face (optional)

Set your Hugging Face token:

```bash
export HF_TOKEN='hf_your_token_here'
```

**Token Requirements:**
- Must be a valid Hugging Face User Access Token (starts with `hf_`)
- Create one at [Hugging Face Settings > Access Tokens](https://huggingface.co/settings/tokens)
- See [documentation](https://huggingface.co/docs/hub/en/security-tokens) for details

**Optional:** Set a custom model (default: `deepseek-ai/DeepSeek-V3.2:novita`):

```bash
export HF_MODEL='your-model-name'
```

If `HF_TOKEN` is not set or invalid, the app falls back to a small set of built-in SQL templates for common step questions. The app will show helpful error messages if your token is invalid or missing.

**Note:** The `export` command sets the variable temporarily for your current terminal session. To make it permanent, add it to your shell config file (e.g., `~/.zshrc`).

## Features

- **Conversational interface**: Ask questions naturally and get formatted answers
- **Sample queries**: Browse example questions to get started
- **Data status**: See at a glance how much data you have and where it came from
- **SQL transparency**: View the exact SQL query generated for each question
- **Error handling**: Clear, helpful error messages with guidance

## Blogs

- `blog/01-making-health-data-searchable.md` (non-technical)
- `blog/02-dev-blueprint-text-to-sql-duckdb-guardrails.md` (developer)
