# twin-api

FastAPI + LangGraph backend for the Tiago AI Digital Twin.

```bash
uv sync                                   # install deps
uv run alembic upgrade head               # create schema (Postgres must be running)
uv run python -m twin.rag.ingest --dry-run  # list documents and chunks
uv run python -m twin.rag.ingest          # embed and store knowledge/
uv run uvicorn twin.main:app_factory --factory --reload  # http://localhost:8000/docs
uv run pytest                             # unit tests
```
