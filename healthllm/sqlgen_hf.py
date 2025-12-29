from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

from huggingface_hub import InferenceClient


class HuggingFaceSqlGenError(RuntimeError):
    pass


DEFAULT_MODEL = "deepseek-ai/DeepSeek-V3.2:novita"


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
    """
    Generate SQL using Hugging Face Inference API with chat completions.
    
    Uses InferenceClient (like the notebook) which supports chat completions API,
    required for models like deepseek-ai/DeepSeek-V3.2:novita.
    """
    prompt = PROMPT_TEMPLATE.format(question=question.strip())
    
    try:
        client = InferenceClient(api_key=cfg.token)
        
        completion = client.chat.completions.create(
            model=cfg.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        
        # Extract SQL from the response
        sql = completion.choices[0].message.content
        
        # Clean up the SQL (remove code fences if any)
        return _strip_code_fences(sql.strip())
        
    except Exception as e:
        error_msg = str(e)
        raise HuggingFaceSqlGenError(f"HF request failed: {error_msg}")


def hf_config_from_env() -> HfConfig | None:
    token = os.getenv("HF_TOKEN")
    if not token:
        return None
    model = os.getenv("HF_MODEL", DEFAULT_MODEL)
    return HfConfig(token=token, model=model)


