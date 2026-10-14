from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from twin import __version__
from twin.api import admin, chat, health
from twin.config import Settings, get_settings
from twin.container import Container, build_container
from twin.db.session import get_engine, get_sessionmaker
from twin.logging import configure_logging


def create_app(container: Container | None = None, settings: Settings | None = None) -> FastAPI:
    settings = settings or (container.settings if container else get_settings())
    configure_logging(settings.log_level, json=settings.env == "production")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if container is not None:
            app.state.container = container
            yield
            await container.chat.drain()
            return
        async with AsyncConnectionPool(
            settings.psycopg_url,
            max_size=10,
            kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
            open=False,
        ) as pool:
            checkpointer = AsyncPostgresSaver(pool)  # type: ignore[arg-type]
            await checkpointer.setup()
            built = build_container(settings, get_sessionmaker(), checkpointer)
            app.state.container = built
            yield
            await built.chat.drain()
        await get_engine().dispose()

    app = FastAPI(title="Tiago AI Digital Twin", version=__version__, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Widget-Key"],
    )
    app.include_router(health.router)
    app.include_router(chat.router)
    app.include_router(admin.router)
    return app


def app_factory() -> FastAPI:
    return create_app()
