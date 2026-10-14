# ADR 0003: A thin LLM gateway with provider fallback and usage tracking

- Status: accepted
- Date: 2026-10-14

## Context

The twin must keep working when OpenAI is slow or down, and every answer
should show its cost and latency (the "glass box"). LangChain's generic
fallbacks hide which provider answered and do not record per-node usage.

## Decision

A small `LLMGateway` calls providers in priority order (OpenAI, then
DeepSeek through its OpenAI-compatible API) with a timeout per attempt. Each
attempt is recorded (node, provider, model, latency, tokens, estimated cost,
fallback flag, error) into a `ContextVar` tracker, which the chat service
persists per message. Streams fall back only before the first token.
Structured outputs use function calling, which both providers support.

## Consequences

- Fallbacks are visible in the UI trace and in `/admin/metrics`.
- Tests use scripted providers behind the same protocol, so the whole graph
  and API are tested without network calls.
- Prices live in one table and are estimates; they need updating when list
  prices change.
