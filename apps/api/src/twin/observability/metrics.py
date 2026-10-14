from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_WINDOW = "now() - make_interval(days => :days)"


async def _rows(db: AsyncSession, sql: str, days: int) -> list[dict[str, Any]]:
    result = await db.execute(text(sql), {"days": days})
    return [dict(row._mapping) for row in result]


def _round(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{k: round(v, 6) if isinstance(v, float) else v for k, v in r.items()} for r in rows]


async def collect_metrics(db: AsyncSession, days: int = 7) -> dict[str, Any]:
    """Operational metrics computed from sessions, messages and llm_calls."""
    overview = await _rows(
        db,
        f"""
        SELECT
          count(*)                                        AS sessions,
          count(*) FILTER (WHERE handoff_at IS NOT NULL)  AS sessions_with_handoff,
          coalesce(sum(total_tokens), 0)                  AS tokens,
          coalesce(sum(total_cost_usd), 0)::float         AS cost_usd,
          coalesce(avg(message_count), 0)::float          AS avg_user_messages
        FROM chat_sessions WHERE created_at >= {_WINDOW}
        """,
        days,
    )
    turns = await _rows(
        db,
        f"""
        SELECT
          count(*)                                                           AS turns,
          percentile_cont(0.5) WITHIN GROUP (ORDER BY latency_ms)::float     AS p50_ms,
          percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms)::float    AS p95_ms,
          count(*) FILTER (WHERE handoff_reason IS NOT NULL)                 AS handoffs,
          count(*) FILTER (WHERE degraded)                                   AS degraded,
          count(*) FILTER (WHERE jsonb_array_length(citations) > 0)          AS with_citations
        FROM chat_messages
        WHERE role = 'assistant' AND created_at >= {_WINDOW}
        """,
        days,
    )
    by_channel = await _rows(
        db,
        f"""
        SELECT channel, count(*) AS sessions FROM chat_sessions
        WHERE created_at >= {_WINDOW} GROUP BY channel ORDER BY sessions DESC
        """,
        days,
    )
    intents = await _rows(
        db,
        f"""
        SELECT coalesce(intent, 'unknown') AS intent, count(*) AS turns FROM chat_messages
        WHERE role = 'assistant' AND created_at >= {_WINDOW}
        GROUP BY 1 ORDER BY turns DESC
        """,
        days,
    )
    handoff_reasons = await _rows(
        db,
        f"""
        SELECT handoff_reason AS reason, count(*) AS turns FROM chat_messages
        WHERE handoff_reason IS NOT NULL AND created_at >= {_WINDOW}
        GROUP BY 1 ORDER BY turns DESC
        """,
        days,
    )
    nodes = await _rows(
        db,
        f"""
        SELECT
          node,
          count(*)                                                         AS calls,
          count(*) FILTER (WHERE NOT ok)                                   AS errors,
          percentile_cont(0.5) WITHIN GROUP (ORDER BY latency_ms)::float   AS p50_ms,
          percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms)::float  AS p95_ms,
          sum(input_tokens)                                                AS input_tokens,
          sum(output_tokens)                                               AS output_tokens,
          sum(cost_usd)::float                                             AS cost_usd
        FROM llm_calls WHERE created_at >= {_WINDOW}
        GROUP BY node ORDER BY calls DESC
        """,
        days,
    )
    providers = await _rows(
        db,
        f"""
        SELECT
          provider, model,
          count(*)                              AS calls,
          count(*) FILTER (WHERE NOT ok)        AS errors,
          count(*) FILTER (WHERE fallback AND ok) AS fallback_successes,
          sum(cost_usd)::float                  AS cost_usd
        FROM llm_calls WHERE created_at >= {_WINDOW}
        GROUP BY provider, model ORDER BY calls DESC
        """,
        days,
    )
    daily = await _rows(
        db,
        f"""
        SELECT date_trunc('day', created_at)::date::text AS day,
               count(*) AS calls, sum(cost_usd)::float AS cost_usd,
               sum(input_tokens + output_tokens) AS tokens
        FROM llm_calls WHERE created_at >= {_WINDOW}
        GROUP BY 1 ORDER BY 1
        """,
        days,
    )
    return {
        "window_days": days,
        "overview": _round(overview)[0],
        "turns": _round(turns)[0],
        "channels": by_channel,
        "intents": intents,
        "handoff_reasons": handoff_reasons,
        "nodes": _round(nodes),
        "providers": _round(providers),
        "daily": _round(daily),
    }
