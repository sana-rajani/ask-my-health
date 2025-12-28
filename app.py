from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from healthllm.dummy_data import DummyConfig, build_dummy_db
from healthllm.ingest_steps import ingest_steps_export_xml
from healthllm.qa import QAResult, answer_steps_question


DEFAULT_DB = "data/ask_my_health.duckdb"


def _render_result(res: QAResult) -> None:
    st.caption(f"Provider: `{res.used_provider}`")
    with st.expander("SQL (what the app ran)"):
        st.code(res.sql, language="sql")

    if res.scalar_answer is not None:
        st.metric("Answer", f"{int(res.scalar_answer):,}" if pd.notna(res.scalar_answer) else "0")
        return

    st.dataframe(res.dataframe, use_container_width=True)

    # Optional plot for common shapes
    cols = [c.lower() for c in res.dataframe.columns]
    if "date" in cols and "steps" in cols:
        df = res.dataframe.copy()
        # Keep original column names
        date_col = res.dataframe.columns[cols.index("date")]
        steps_col = res.dataframe.columns[cols.index("steps")]
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.sort_values(date_col)
        st.line_chart(df.set_index(date_col)[steps_col])

    if "week_start" in cols and "steps" in cols:
        df = res.dataframe.copy()
        week_col = res.dataframe.columns[cols.index("week_start")]
        steps_col = res.dataframe.columns[cols.index("steps")]
        df[week_col] = pd.to_datetime(df[week_col])
        df = df.sort_values(week_col)
        st.line_chart(df.set_index(week_col)[steps_col])


st.set_page_config(page_title="ask-my-health (steps)", layout="wide")
st.title("ask-my-health (steps-only v0.1)")
st.write("Ask step questions backed by DuckDB. The app shows you the SQL it ran.")

with st.sidebar:
    st.header("Data")
    db_path = st.text_input("DuckDB path", value=DEFAULT_DB)

    st.subheader("Option 1: Dummy data (recommended for first run)")
    days = st.number_input("Days", min_value=30, max_value=2000, value=180, step=30)
    seed = st.number_input("Seed", min_value=0, max_value=10_000, value=42, step=1)
    if st.button("Initialize dummy data"):
        path = build_dummy_db(db_path, DummyConfig(days=int(days), seed=int(seed)))
        st.success(f"Dummy data written to {path}")

    st.subheader("Option 2: Apple Health export.xml")
    xml_path = st.text_input("Path to export.xml", value="")
    if st.button("Ingest steps from export.xml"):
        if not xml_path.strip():
            st.error("Please provide a path to export.xml")
        else:
            res = ingest_steps_export_xml(xml_path=xml_path, db_path=db_path, overwrite=True)
            st.success(f"Ingested {res.step_records_seen} step records into {res.days} days")

    st.divider()
    st.header("LLM (optional)")
    st.write("If `HF_TOKEN` is set in your environment, the app will use Hugging Face text-to-SQL.")
    force_templates = st.checkbox("Force template mode (ignore HF_TOKEN)", value=False)
    hf_strict = st.checkbox("HF strict mode (no fallback)", value=False)

st.header("Ask a question")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

question = st.chat_input("e.g., How many steps did I walk this year?")
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        try:
            res = answer_steps_question(
                question=question, db_path=db_path, force_templates=force_templates, hf_strict=hf_strict
            )
            _render_result(res)
            st.session_state.messages.append({"role": "assistant", "content": "Done."})
        except Exception as e:  # noqa: BLE001
            st.error(str(e))
            st.session_state.messages.append({"role": "assistant", "content": f"Error: {e}"})


