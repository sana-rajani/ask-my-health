from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

import requests


class HuggingFaceSqlGenError(RuntimeError):
    pass


DEFAULT_MODEL = "defog/sqlcoder-7b-2"


@dataclass(frozen=True)
class HfConfig:
    token: str
    model: str = DEFAULT_MODEL
    timeout_s: int = 60


PROMPT_TEMPLATE = """You are an expert at writing DuckDB SQL.

Return ONLY a single SQL query (no explanations, no markdown).
Rules:
- Must be a single SELECT statement.
- Query only the table daily_steps(date DATE, steps BIGINT).
- Do not use any other tables.
- If the question asks for a single number, return exactly one row with column alias answer.
- Use date filters on daily_steps.date.

Schema:
daily_steps(date DATE, steps BIGINT)

Question: {question}
SQL:
"""


def _strip_code_fences(text: str) -> str:
    s = text.strip()
    s = re.sub(r"^```sql\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^```", "", s)
    s = re.sub(r"```$", "", s)
    return s.strip()


def _extract_sql_from_generated_text(prompt: str, generated: str) -> str:
    # Some endpoints return the prompt + completion. If so, remove the prompt prefix.
    if generated.startswith(prompt):
        generated = generated[len(prompt) :]
    return _strip_code_fences(generated).strip()


def generate_sql_hf(question: str, cfg: HfConfig) -> str:
    prompt = PROMPT_TEMPLATE.format(question=question.strip())
    url = f"https://api-inference.huggingface.co/models/{cfg.model}"
    headers = {"Authorization": f"Bearer {cfg.token}"}
    payload = {
        "inputs": prompt,
        "parameters": {"temperature": 0, "max_new_tokens": 256, "return_full_text": False},
        "options": {"wait_for_model": True},
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=cfg.timeout_s)
    if resp.status_code >= 400:
        raise HuggingFaceSqlGenError(f"HF request failed: {resp.status_code} {resp.text}")

    data: Any = resp.json()
    if isinstance(data, dict) and data.get("error"):
        raise HuggingFaceSqlGenError(f"HF error: {data.get('error')}")

    # Most common shape: [{"generated_text": "..."}]
    if isinstance(data, list) and data and isinstance(data[0], dict) and "generated_text" in data[0]:
        return _extract_sql_from_generated_text(prompt, str(data[0]["generated_text"]))

    # Fallback: try a best-effort extraction.
    return _strip_code_fences(str(data)).strip()


def hf_config_from_env() -> HfConfig | None:
    token = os.getenv("HF_TOKEN")
    if not token:
        return None
    model = os.getenv("HF_MODEL", DEFAULT_MODEL)
    return HfConfig(token=token, model=model)


