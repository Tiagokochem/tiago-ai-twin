from typing import Any

import structlog

from twin.config import Settings

log = structlog.get_logger()


def build_callbacks(settings: Settings) -> list[Any]:
    """LangChain callbacks for Langfuse tracing, if configured.

    Works with Langfuse Cloud or a self-hosted instance (LANGFUSE_BASE_URL).
    """
    public = settings.langfuse_public_key
    secret = settings.langfuse_secret_key
    if not (public and secret and secret.get_secret_value()):
        return []
    try:
        from langfuse import Langfuse
        from langfuse.langchain import CallbackHandler
    except ImportError:
        log.warning("tracing.langfuse_not_installed")
        return []
    Langfuse(
        public_key=public,
        secret_key=secret.get_secret_value(),
        base_url=settings.langfuse_base_url,
        environment=settings.env,
    )
    log.info("tracing.langfuse_enabled", base_url=settings.langfuse_base_url)
    return [CallbackHandler(public_key=public)]
