from __future__ import annotations

import re
from dataclasses import dataclass


class NoTemplateMatchError(ValueError):
    pass


@dataclass(frozen=True)
class TemplateMatch:
    sql: str
    matched_rule: str


def _norm(q: str) -> str:
    q = q.strip().lower()
    q = re.sub(r"\s+", " ", q)
    return q


def generate_sql_from_templates(question: str) -> TemplateMatch:
    """
    Very small intent router for the steps-only MVP.

    This exists so the app works without an HF token and so tests can run deterministically.
    """
    q = _norm(question)

    if "steps" not in q and "walk" not in q and "step" not in q:
        raise NoTemplateMatchError("This v1 only supports step questions.")

    # Single-number queries (alias answer)
    if "this year" in q or "in 2025" in q or "this yr" in q:
        return TemplateMatch(
            matched_rule="sum_this_year",
            sql="""
            SELECT COALESCE(SUM(steps), 0) AS answer
            FROM daily_steps
            WHERE date >= date_trunc('year', current_date)
              AND date <  date_trunc('year', current_date) + INTERVAL '1 year'
            """.strip(),
        )

    if "this month" in q:
        return TemplateMatch(
            matched_rule="sum_this_month",
            sql="""
            SELECT COALESCE(SUM(steps), 0) AS answer
            FROM daily_steps
            WHERE date >= date_trunc('month', current_date)
              AND date <  date_trunc('month', current_date) + INTERVAL '1 month'
            """.strip(),
        )

    if "average" in q or "avg" in q:
        # Default: average steps per day over all available data.
        return TemplateMatch(
            matched_rule="avg_per_day_all_time",
            sql="""
            SELECT COALESCE(AVG(steps), 0) AS answer
            FROM daily_steps
            """.strip(),
        )

    # Table-shaped queries
    m = re.search(r"top\s+(\d+)", q)
    if m:
        n = int(m.group(1))
        n = max(1, min(n, 50))
        return TemplateMatch(
            matched_rule="top_n_days",
            sql=f"""
            SELECT date, steps
            FROM daily_steps
            ORDER BY steps DESC, date DESC
            LIMIT {n}
            """.strip(),
        )

    if "top" in q and "day" in q:
        return TemplateMatch(
            matched_rule="top_10_days_default",
            sql="""
            SELECT date, steps
            FROM daily_steps
            ORDER BY steps DESC, date DESC
            LIMIT 10
            """.strip(),
        )

    if "weekday" in q or "day of week" in q:
        return TemplateMatch(
            matched_rule="weekday_average",
            sql="""
            SELECT
              strftime(date, '%w') AS weekday_num,
              AVG(steps) AS avg_steps
            FROM daily_steps
            GROUP BY 1
            ORDER BY 1
            """.strip(),
        )

    if "trend" in q or "weekly" in q or "last 12 weeks" in q:
        return TemplateMatch(
            matched_rule="weekly_trend_last_12_weeks",
            sql="""
            SELECT
              date_trunc('week', date) AS week_start,
              SUM(steps) AS steps
            FROM daily_steps
            WHERE date >= current_date - INTERVAL '84 days'
            GROUP BY 1
            ORDER BY 1
            """.strip(),
        )

    raise NoTemplateMatchError("No matching template rule for this question yet.")


