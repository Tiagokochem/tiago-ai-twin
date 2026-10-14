# Tiago AI - Digital Twin

Open source Agentic AI project: a bilingual (PT/EN) digital twin that lets
recruiters interview Tiago Kochem by chat, voice or WhatsApp while he is
offline. Answers are grounded in real sources via hybrid RAG and always cite
them; salary, offers and unknown topics are handed off to the real Tiago.

> Work in progress. Phase 1 (foundation + knowledge ingestion) is done.

## Stack

- **Backend:** Python 3.12, FastAPI, LangGraph, PostgreSQL + pgvector
- **LLMs:** OpenAI (primary), DeepSeek (fallback)
- **Frontend:** Next.js (planned), embeddable widget, WhatsApp via Evolution API
- **Infra:** Docker Compose + Caddy (automatic HTTPS)

## Repository layout

```
apps/api/        FastAPI + RAG pipeline (+ LangGraph agent, next phase)
knowledge/       markdown sources for RAG, pt/ and en/
persona.yaml     persona, tone, handoff rules and messages
infra/Caddyfile  reverse proxy / TLS
docker-compose.yml
```

## Quick start

```bash
cp .env.example .env          # set POSTGRES_PASSWORD, OPENAI_API_KEY, ADMIN_TOKEN
docker compose up -d --build  # postgres, api, caddy
docker compose exec api python -m twin.rag.ingest
curl -k https://localhost/api/health
```

### Deploying on a VPS without a domain

Set `PUBLIC_HOST` to the VPS IP in [sslip.io](https://sslip.io) form
(`203.0.113.10` -> `203-0-113-10.sslip.io`). Caddy obtains a Let's Encrypt
certificate for it, so HTTPS sites (e.g. Vercel) can call the API without
mixed-content errors. Ports 80 and 443 must be open.

## Development

```bash
cd apps/api
uv sync
uv run pytest                                   # unit tests
TEST_DATABASE_URL=postgresql+asyncpg://twin:<password>@localhost:5432/twin_test \
  uv run pytest -m integration                  # needs Postgres
```
