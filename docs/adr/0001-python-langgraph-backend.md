# ADR 0001: Python, FastAPI and LangGraph for the backend

- Status: accepted
- Date: 2026-10-14

## Context

The original idea listed a TypeScript stack (Node, LangGraph.js, Zod). The
project targets AI Engineer roles, where Python is the dominant language, and
the owner wanted to use Python.

## Decision

Backend in Python 3.12 with FastAPI, LangGraph (Python) for the agent,
LangChain only as the chat-model adapter, Pydantic for structured outputs,
SQLAlchemy async + asyncpg, and `uv` for dependency management.

## Consequences

- The richest LangGraph features (Postgres checkpointer, custom stream
  events) are available and mature in Python.
- The frontend is a separate Next.js app; the contract between them is a
  small REST + SSE API.
- Strict mypy and ruff keep the Python codebase at a typed, production standard.
