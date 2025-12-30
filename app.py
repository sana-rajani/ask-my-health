from __future__ import annotations

from pathlib import Path

import os
import pandas as pd
import streamlit as st

from healthllm.dummy_data import DummyConfig, build_dummy_db
from healthllm.ingest_steps import ingest_steps_export_xml
from healthllm.qa import QAResult, answer_steps_question
from healthllm.db import connect, init_schema
from healthllm.sqlgen_hf import hf_config_from_env


DEFAULT_DB = "data/ask_my_health.duckdb"


def _check_data_availability(db_path: str | Path) -> tuple[bool, int, str | None, str | None]:
    """Check if data exists and return (has_data, row_count, source_type, source_path)."""
    try:
        con = connect(db_path)
        init_schema(con)
        
        # Check data count
        result = con.execute("SELECT COUNT(*) as count FROM daily_steps").fetchone()
        count = result[0] if result else 0
        
        # Check source
        source_result = con.execute(
            "SELECT source_type, source_path FROM data_source WHERE id = 1"
        ).fetchone()
        
        source_type = None
        source_path = None
        if source_result:
            source_type = source_result[0]
            source_path = source_result[1]
        
        con.close()
        return (count > 0, count, source_type, source_path)
    except Exception:
        return (False, 0, None, None)


def _get_hf_status() -> tuple[bool, str | None]:
    """Check if HF model is available and return (is_available, model_name)."""
    token = os.getenv("HF_TOKEN")
    if not token:
        return (False, None)
    
    # Basic format validation
    if not token.startswith("hf_"):
        return (False, None)
    
    hf_cfg = hf_config_from_env()
    if hf_cfg:
        return (True, hf_cfg.model)
    return (False, None)


def _format_answer(question: str, answer: int | float, sql: str, df: pd.DataFrame) -> str:
    """
    Format a numeric answer as a conversational sentence using pattern matching.
    Uses question text, SQL structure, and dataframe context for intelligent formatting.
    """
    q_lower = question.lower()
    sql_lower = sql.lower()
    answer_int = int(answer)
    
    # Pattern 1: Comparison/difference queries
    if "diff" in q_lower or "difference" in q_lower or ("compare" in q_lower and ("less" in q_lower or "more" in q_lower)):
        # Check if SQL has comparison patterns (CTEs, subtraction, etc.)
        if "current_year" in sql_lower or "last_year" in sql_lower or "yearly_totals" in sql_lower:
            abs_diff = abs(answer_int)
            if answer_int < 0:
                return f"You walked **{abs_diff:,} fewer steps** this year compared to 2023."
            elif answer_int > 0:
                return f"You walked **{abs_diff:,} more steps** this year compared to 2023."
            else:
                return "You walked the **same number of steps** this year as in 2023."
        # Generic comparison fallback
        abs_diff = abs(answer_int)
        if answer_int < 0:
            return f"The difference is **{abs_diff:,} fewer steps**."
        elif answer_int > 0:
            return f"The difference is **{abs_diff:,} more steps**."
        else:
            return "The difference is **zero** - same number of steps."
    
    # Pattern 2: Total/Sum queries
    if "sum" in sql_lower or "total" in q_lower or "how many" in q_lower:
        if "this year" in q_lower or "2025" in q_lower or ("year" in q_lower and "this" in q_lower):
            return f"You walked **{answer_int:,} steps** this year."
        elif "this month" in q_lower or ("month" in q_lower and "this" in q_lower):
            return f"You walked **{answer_int:,} steps** this month."
        elif "last year" in q_lower or "2023" in q_lower or "2024" in q_lower:
            year = "2023" if "2023" in q_lower else ("2024" if "2024" in q_lower else "last year")
            return f"You walked **{answer_int:,} steps** in {year}."
        elif "all time" in q_lower or "ever" in q_lower:
            return f"You've walked **{answer_int:,} steps** in total."
        else:
            return f"You walked **{answer_int:,} steps**."
    
    # Pattern 3: Average queries
    if "avg" in sql_lower or "average" in q_lower or "mean" in q_lower:
        if "per day" in q_lower or "daily" in q_lower:
            return f"Your average daily steps is **{answer_int:,}**."
        elif "per week" in q_lower or "weekly" in q_lower:
            return f"Your average weekly steps is **{answer_int:,}**."
        else:
            return f"Your average steps is **{answer_int:,}**."
    
    # Pattern 4: Maximum/Minimum queries
    if "max" in sql_lower or "maximum" in q_lower or "most" in q_lower:
        return f"Your maximum steps is **{answer_int:,}**."
    if "min" in sql_lower or "minimum" in q_lower or "least" in q_lower:
        return f"Your minimum steps is **{answer_int:,}**."
    
    # Pattern 5: Count queries
    if "count" in sql_lower or "how many days" in q_lower:
        if answer_int == 1:
            return "You have data for **1 day**."
        else:
            return f"You have data for **{answer_int:,} days**."
    
    # Default: format as steps
    return f"**{answer_int:,} steps**"


def _render_result(res: QAResult, question: str = "") -> None:
    # User-friendly provider indicator
    if "hf" in res.used_provider.lower() and "fallback" not in res.used_provider.lower():
        st.caption("Using LLM mode")
    elif "template" in res.used_provider.lower():
        st.caption("Using template mode")
    else:
        st.caption(f"Mode: {res.used_provider}")
    
    with st.expander("View SQL query"):
        st.code(res.sql, language="sql")

    if res.scalar_answer is not None:
        answer_value = res.scalar_answer
        if pd.notna(answer_value):
            # Format as conversational sentence
            formatted_text = _format_answer(question, answer_value, res.sql, res.dataframe)
            st.markdown(formatted_text)
            # Keep the metric for visual reference
            st.metric("Answer", f"{int(answer_value):,}" if pd.notna(answer_value) else "0")
        else:
            st.markdown("**No data available.**")
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
st.title("ask-my-health (steps-only v1)")
st.write("Have a conversation with your step data and get reliable insights.")

# Sample queries section - show 3 at a time, merged categories
all_sample_queries = [
    "How many steps did I walk this year?",
    "What's my average daily steps?",
    "Show me my top 10 walking days",
    "Did I walk more steps this year compared to 2023? What's the difference?",
    "What's my average steps per month in 2024 and 2025?",
    "How many steps did I walk this month?",
]

with st.expander("💡 Try these sample queries", expanded=False):
    # Show 3 queries at a time
    if "query_page" not in st.session_state:
        st.session_state.query_page = 0
    
    start_idx = st.session_state.query_page * 3
    end_idx = min(start_idx + 3, len(all_sample_queries))
    current_queries = all_sample_queries[start_idx:end_idx]
    
    for query in current_queries:
        st.code(query, language=None)
    
    # Navigation buttons if there are more queries
    if len(all_sample_queries) > 3:
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("← Previous", disabled=st.session_state.query_page == 0, key="prev_queries"):
                st.session_state.query_page -= 1
                st.rerun()
        with col3:
            max_page = (len(all_sample_queries) - 1) // 3
            if st.button("Next →", disabled=st.session_state.query_page >= max_page, key="next_queries"):
                st.session_state.query_page += 1
                st.rerun()
    
    st.caption("💡 Tip: Click on any query above to copy it!")

with st.sidebar:
    # Data status at the top
    st.header("📊 Data Status")
    db_path = st.text_input("DuckDB path", value=DEFAULT_DB)
    
    # Check data availability
    has_data, row_count, source_type, source_path = _check_data_availability(db_path)
    hf_available, hf_model = _get_hf_status()
    
    if has_data:
        st.success(f"✅ **{row_count:,}** days of step data available")
        if source_type == "dummy":
            st.caption("Source: Dummy data")
        elif source_type == "export_xml":
            st.caption("Source: Apple Health export.xml")
            if source_path:
                st.caption(f"Path: `{Path(source_path).name}`")
        else:
            st.caption("Source: Unknown")
        st.caption(f"Database: `{db_path}`")
    else:
        st.warning("⚠️ No data available")
        st.caption(f"Database: `{db_path}`")
    
    st.divider()
    
    # Data ingestion section with title
    st.header("Add Data")
    st.write("**Option 1:** Try out the app with dummy data")
    st.write("**Option 2:** Add your Apple Health export.xml")
    
    st.subheader("Option 1: Dummy data")
    st.caption("Recommended for first run")
    days = st.number_input("Days", min_value=30, max_value=2000, value=180, step=30, key="dummy_days")
    seed = st.number_input("Seed", min_value=0, max_value=10_000, value=42, step=1, key="dummy_seed")
    if st.button("Generate sample data"):
        path = build_dummy_db(db_path, DummyConfig(days=int(days), seed=int(seed)))
        st.success("Sample data created successfully! You can now ask questions.")
        st.rerun()  # Refresh to show updated data status

    st.subheader("Option 2: Apple Health export.xml")
    xml_path = st.text_input("Path to export.xml", value="", key="xml_path")
    if st.button("Import from export.xml"):
        if not xml_path.strip():
            st.error("Please provide a path to export.xml")
        else:
            try:
                res = ingest_steps_export_xml(xml_path=xml_path, db_path=db_path, overwrite=True)
                st.success(f"Your data is ready! Found {res.step_records_seen:,} step records across {res.days} days.")
                st.rerun()  # Refresh to show updated data status
            except Exception as e:
                st.error(f"We couldn't import your data. Please check the file path and try again.")
                st.caption(f"Error details: {str(e)}")

    st.divider()
    st.header("LLM for SQL Generation")
    
    # HF Model status indicator
    if hf_available:
        st.success(f"✅ HF Model available: **{hf_model}**")
        st.caption("The app will use Hugging Face text-to-SQL unless forced to use templates.")
    else:
        st.info("ℹ️ HF Model not available (HF_TOKEN not set)")
        st.caption("The app will use template-based SQL generation.")
    
    force_templates = st.checkbox("Force template mode (ignore HF_TOKEN)", value=False)
    hf_strict = st.checkbox("HF strict mode (no fallback)", value=False)

st.header("Ask a question")

# Check data availability for empty state
has_data, row_count, source_type, source_path = _check_data_availability(db_path)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "results" not in st.session_state:
    st.session_state.results = []  # Store QAResult objects for re-rendering

# Track which result index we're on (results only exist for assistant messages)
result_idx = 0

for i, m in enumerate(st.session_state.messages):
    with st.chat_message(m["role"]):
        # For assistant messages, only show result if it exists
        if m["role"] == "assistant" and result_idx < len(st.session_state.results):
            result = st.session_state.results[result_idx]
            if result is not None:
                # Get the question from the previous user message
                question = ""
                if i > 0 and st.session_state.messages[i - 1]["role"] == "user":
                    question = st.session_state.messages[i - 1]["content"]
                _render_result(result, question=question)
            else:
                # Only show message content for errors
                if m["content"]:
                    st.markdown(m["content"])
            result_idx += 1  # Move to next result for next assistant message
        else:
            # For user messages, show the content
            st.markdown(m["content"])

# Empty state guidance
if not has_data and len(st.session_state.messages) == 0:
    with st.chat_message("assistant"):
        st.info("👋 Welcome! To get started, add some data using the sidebar. You can generate sample data or import your Apple Health export.xml file.")

# First query suggestion when chat is empty but data exists
if has_data and len(st.session_state.messages) == 0:
    with st.chat_message("assistant"):
        st.markdown("👋 Hi! I'm ready to answer questions about your step data. Try asking: **'How many steps did I walk this year?'**")

# Chat input - disabled when no data
question = st.chat_input(
    "e.g., How many steps did I walk this year?",
    disabled=not has_data
)
if not has_data and question:
    st.warning("Please add data first using the sidebar to start asking questions.")
elif question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Processing your question..."):
            # Check HF status for error handling
            hf_available_check, _ = _get_hf_status()
            
            try:
                res = answer_steps_question(
                    question=question, db_path=db_path, force_templates=force_templates, hf_strict=hf_strict
                )
                _render_result(res, question=question)
                # Store empty string - the result will be rendered, not the message content
                st.session_state.messages.append({"role": "assistant", "content": ""})
                st.session_state.results.append(res)  # Store the result for re-rendering
            except Exception as e:  # noqa: BLE001
                error_str = str(e)
                
                # Check for non-step questions
                from healthllm.sqlgen_templates import NoTemplateMatchError
                from healthllm.sql_guard import UnsafeSQLError
                
                if isinstance(e, NoTemplateMatchError):
                    st.error("**This question is not about steps**")
                    st.markdown(
                        "This is **v1** of the app, which currently focuses on **step data only**. "
                        "Questions about sleep, heart rate, calories, workouts, and other health metrics are not yet supported."
                    )
                    st.markdown(
                        "Please ask questions about your walking steps. You can find example queries in the expandable section above."
                    )
                    with st.expander("Error details"):
                        st.code(error_str, language=None)
                    st.session_state.messages.append({"role": "assistant", "content": f"Error: {error_str}"})
                    st.session_state.results.append(None)  # Store None for errors
                elif isinstance(e, UnsafeSQLError) and "No table referenced" in error_str:
                    st.error("**This question is not about steps**")
                    st.markdown(
                        "This is **v1** of the app, which currently focuses on **step data only**. "
                        "Questions about sleep, heart rate, calories, workouts, and other health metrics are not yet supported. "
                        "More features coming soon!"
                    )
                    st.markdown(
                        "Please ask questions about your walking steps. You can find example queries in the expandable section above."
                    )
                    with st.expander("Error details"):
                        st.code(error_str, language=None)
                    st.session_state.messages.append({"role": "assistant", "content": f"Error: {error_str}"})
                    st.session_state.results.append(None)  # Store None for errors
                else:
                    # Check for invalid HF token errors
                    is_invalid_token = (
                        "non-Hugging Face API key" in error_str
                        or "model_not_supported" in error_str
                        or "invalid_request_error" in error_str
                        or "401" in error_str
                        or "Unauthorized" in error_str
                        or "HF request failed" in error_str
                    )
                    
                    # Check if user is trying to use HF mode
                    is_trying_hf = not force_templates
                    
                    # Show special error message if:
                    # 1. Token is set but invalid (hf_available_check is True but error occurred)
                    # 2. Token is not set but user is trying to use HF and error is HF-related
                    # 3. Error contains HF-related keywords
                    is_hf_token_error = (
                        is_invalid_token 
                        or (not hf_available_check and is_trying_hf and ("HF" in error_str or "huggingface" in error_str.lower()))
                    )
                    
                    if is_hf_token_error:
                        if not hf_available_check:
                            # HF_TOKEN not set
                            st.error("**HF Token is not set**")
                            st.markdown(
                                "To use Hugging Face SQL generation, you need to set your `HF_TOKEN` environment variable. "
                                "Please follow these steps to create a User Access Token:"
                            )
                        else:
                            # HF_TOKEN set but invalid
                            st.error("**HF Token is invalid or not working**")
                            st.markdown(
                                "Your `HF_TOKEN` environment variable is set, but the token appears to be invalid or expired. "
                                "Please follow these steps to create a valid User Access Token:"
                            )
                        
                        st.markdown(
                            "1. Go to [Hugging Face Settings > Access Tokens](https://huggingface.co/settings/tokens)\n"
                            "2. Click **New token**\n"
                            "3. Select a role (read is sufficient for inference)\n"
                            "4. Copy the token (it starts with `hf_`)\n"
                            "5. Set it in your environment: `export HF_TOKEN='hf_your_token_here'`"
                        )
                        st.markdown(
                            "📖 [Full documentation: How to create User Access Tokens](https://huggingface.co/docs/hub/en/security-tokens)"
                        )
                        with st.expander("Error details"):
                            st.code(error_str, language=None)
                    else:
                        st.error("We couldn't process that query. Try rephrasing your question or check the error details below.")
                        with st.expander("Error details"):
                            st.code(error_str, language=None)
                    
                    st.session_state.messages.append({"role": "assistant", "content": f"Error: {error_str}"})
                    st.session_state.results.append(None)  # Store None for errors

st.divider()
st.caption(
    "**Note:** Basic template mode supports a limited set of queries. "
    "For more complex questions, set your `HF_TOKEN` environment variable to use the LLM's SQL generation capabilities. "
    "LLMs and humans can make mistakes—we encourage reviewing the generated SQL. "
    "Happy analysing! 🎉"
)


