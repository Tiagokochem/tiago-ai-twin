from dataclasses import dataclass
from typing import Any

from langgraph.types import Checkpointer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from twin.agent.graph import AgentDeps, build_graph
from twin.agent.job_fit import JobFitService
from twin.channels.notify import LogNotifier, Notifier
from twin.chat.service import ChatLimits, ChatService
from twin.config import Settings
from twin.llm.gateway import LLMGateway
from twin.llm.providers import build_providers
from twin.persona import Persona, load_persona
from twin.rag.embeddings import Embedder, OpenAIEmbedder
from twin.rag.retriever import HybridRetriever, Retriever
from twin.security.rate_limit import RateLimiter
from twin.voice.speech import Speech, build_speech


@dataclass
class Container:
    settings: Settings
    persona: Persona
    gateway: LLMGateway
    retriever: Retriever
    chat: ChatService
    rate_limiter: RateLimiter
    job_fit: JobFitService
    speech: Speech | None
    extras: dict[str, Any]


def build_embedder_or_none(settings: Settings) -> Embedder | None:
    if settings.openai_api_key and settings.openai_api_key.get_secret_value():
        return OpenAIEmbedder(
            api_key=settings.openai_api_key.get_secret_value(),
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
        )
    return None


def build_container(
    settings: Settings,
    sessionmaker: async_sessionmaker[AsyncSession],
    checkpointer: Checkpointer,
    *,
    gateway: LLMGateway | None = None,
    retriever: Retriever | None = None,
    notifier: Notifier | None = None,
    callbacks: list[Any] | None = None,
    speech: Speech | None = None,
) -> Container:
    persona = load_persona(settings.persona_path, settings.whatsapp_owner_number)
    gateway = gateway or LLMGateway(build_providers(settings), settings.llm_timeout_seconds)
    retriever = retriever or HybridRetriever(sessionmaker, build_embedder_or_none(settings))
    graph = build_graph(AgentDeps(llm=gateway, retriever=retriever, persona=persona), checkpointer)
    chat = ChatService(
        graph,
        sessionmaker,
        persona,
        notifier or LogNotifier(),
        ChatLimits(settings.session_max_messages, settings.session_max_tokens),
        callbacks=callbacks,
    )
    return Container(
        settings=settings,
        persona=persona,
        gateway=gateway,
        retriever=retriever,
        chat=chat,
        rate_limiter=RateLimiter(settings.rate_limit_per_minute, settings.rate_limit_per_day),
        job_fit=JobFitService(gateway, retriever, persona),
        speech=speech or build_speech(settings),
        extras={},
    )
