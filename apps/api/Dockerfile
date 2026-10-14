FROM python:3.12-slim AS base

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --all-extras --no-install-project

COPY README.md alembic.ini ./
COPY migrations ./migrations
COPY src ./src
COPY evals ./evals
RUN uv sync --frozen --no-dev --all-extras

RUN useradd --create-home --uid 1000 twin
USER twin

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn twin.main:app_factory --factory --host 0.0.0.0 --port 8000 --root-path /api --proxy-headers --forwarded-allow-ips='*'"]
