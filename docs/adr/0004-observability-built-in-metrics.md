# ADR 0004: Built-in metrics first, Langfuse optional

- Status: accepted
- Date: 2026-10-14

## Context

The plan mentioned Langfuse for tracing. Self-hosting Langfuse v3 requires
ClickHouse, Redis and S3-compatible storage, which is heavy for a small VPS
that also hosts other services.

## Decision

Persist one row per LLM call in Postgres and expose aggregated metrics at
`GET /v1/admin/metrics` (turns, p50/p95 latency, cost, intents, handoff
reasons, per-node and per-provider errors and fallbacks, daily series).
Langfuse is an optional extra: when keys are set, a LangChain callback sends
traces to Langfuse Cloud or any self-hosted instance.

## Consequences

- Observability works with zero extra infrastructure and is covered by tests.
- Deep trace inspection (prompt-level) requires enabling Langfuse.
