import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from datetime import timedelta

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from twin import __version__
from twin.api import admin, channels, chat, health, job_fit, voice
from twin.config import Settings, get_settings
from twin.container import Container, build_container
from twin.db.session import get_engine, get_sessionmaker
from twin.logging import configure_logging
from twin.observability.requests import RequestContextMiddleware
from twin.observability.tracing import build_callbacks

log = structlog.get_logger()


async def sweep_idle_sessions(container: Container, every_seconds: float = 300) -> None:
    """Close idle interviews so the owner receives their summary."""
    max_idle = timedelta(minutes=container.settings.session_idle_minutes)
    while True:
        await asyncio.sleep(every_seconds)
        try:
            ended = await container.chat.end_idle_sessions(max_idle)
            if ended:
                log.info("sessions.idle_ended", count=ended)
        except Exception as exc:
            log.error("sessions.sweep_failed", error=repr(exc))


async def shutdown(container: Container) -> None:
    if container.whatsapp is not None:
        await container.whatsapp.drain()
    await container.chat.drain()


def create_app(container: Container | None = None, settings: Settings | None = None) -> FastAPI:
    settings = settings or (container.settings if container else get_settings())
    configure_logging(settings.log_level, json=settings.env == "production")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if container is not None:
            app.state.container = container
            yield
            await shutdown(container)
            return
        async with AsyncConnectionPool(
            settings.psycopg_url,
            max_size=10,
            kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
            open=False,
        ) as pool:
            checkpointer = AsyncPostgresSaver(pool)  # type: ignore[arg-type]
            await checkpointer.setup()
            built = build_container(
                settings, get_sessionmaker(), checkpointer, callbacks=build_callbacks(settings)
            )
            app.state.container = built
            sweeper = asyncio.create_task(sweep_idle_sessions(built))
            yield
            sweeper.cancel()
            with suppress(asyncio.CancelledError):
                await sweeper
            await shutdown(built)
        await get_engine().dispose()

    app = FastAPI(title="Tiago AI Digital Twin", version=__version__, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Widget-Key"],
        expose_headers=["X-Request-ID", "Retry-After"],
    )
    app.add_middleware(RequestContextMiddleware)
    app.include_router(health.router)
    app.include_router(chat.router)
    app.include_router(job_fit.router)
    app.include_router(voice.router)
    app.include_router(channels.router)
    app.include_router(admin.router)
    return app


def app_factory() -> FastAPI:
    return create_app()
