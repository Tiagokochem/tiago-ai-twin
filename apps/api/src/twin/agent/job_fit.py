import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Literal

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, field_validator

from twin.agent.citations import extract_citations, strip_invalid_markers
from twin.agent.context import sources_message
from twin.agent.prompts import LANGUAGE_NAMES, PromptRegistry, default_registry
from twin.llm.gateway import LLMGateway
from twin.llm.usage import UsageTracker, track_usage
from twin.persona import Lang, Persona
from twin.rag.retriever import RetrievalResult, RetrievedChunk, Retriever

log = structlog.get_logger()

Status = Literal["met", "partial", "gap"]
STATUS_VALUE: dict[str, float] = {"met": 1.0, "partial": 0.5, "gap": 0.0}
MAX_REQUIREMENTS = 8
MAX_REQUIREMENT_CHARS = 160


class JobRequirements(BaseModel):
    role: str = Field(description="Job title, short")
    requirements: list[str] = Field(
        description="The 3 to 8 most important requirements, most important first, each a "
        "short phrase (e.g. '3+ years with Python', 'LLM agents in production')"
    )

    @field_validator("requirements")
    @classmethod
    def _clean(cls, value: list[str]) -> list[str]:
        cleaned = [" ".join(r.split())[:MAX_REQUIREMENT_CHARS] for r in value if r.strip()]
        return cleaned[:MAX_REQUIREMENTS]


class RequirementAssessment(BaseModel):
    requirement: str
    status: Status
    evidence: str = Field(
        description="One sentence citing sources like [2]. For gaps, say what is missing."
    )


class JobFitAssessment(BaseModel):
    summary: str = Field(description="Two or three sentences, honest, with citations")
    requirements: list[RequirementAssessment]
    strengths: list[str] = Field(description="Up to 3 strongest points for this role")
    gaps: list[str] = Field(description="Up to 3 honest gaps or things to verify in an interview")


def fit_score(statuses: list[str]) -> int:
    """0-100 from per-requirement statuses, earlier requirements weigh more.
    Deterministic, so a job description cannot talk the model into a score."""
    if not statuses:
        return 0
    weights = [len(statuses) - i for i in range(len(statuses))]
    total = sum(w * STATUS_VALUE.get(s, 0.0) for w, s in zip(weights, statuses, strict=True))
    return round(100 * total / sum(weights))


@dataclass
class JobFitResult:
    role: str
    score: int
    assessment: JobFitAssessment
    citations: list[dict[str, Any]]
    usage: dict[str, Any]
    latency_ms: int
    searches: list[str] = field(default_factory=list)
    tracker: UsageTracker = field(default_factory=UsageTracker)


def interleave(results: list[list[RetrievedChunk]], limit: int) -> list[RetrievedChunk]:
    """Round-robin over per-requirement rankings so each requirement gets evidence."""
    merged: list[RetrievedChunk] = []
    seen: set[int] = set()
    depth = max((len(r) for r in results), default=0)
    for i in range(depth):
        for ranking in results:
            if i < len(ranking) and ranking[i].chunk_id not in seen:
                seen.add(ranking[i].chunk_id)
                merged.append(ranking[i])
                if len(merged) == limit:
                    return merged
    return merged


def job_description_message(description: str, role: str = "", requirements: str = "") -> str:
    header = f"Role: {role}\nRequirements:\n{requirements}\n\n" if role else ""
    return f"{header}<job_description>\n{description}\n</job_description>"


class JobFitService:
    """Agentic job-fit analysis in three reusable steps: extract requirements,
    retrieve evidence for each one in parallel, assess against the sources.
    The chat graph reuses the first two steps for pasted job descriptions."""

    def __init__(
        self,
        llm: LLMGateway,
        retriever: Retriever,
        persona: Persona,
        prompts: PromptRegistry | None = None,
        per_requirement: int = 3,
        max_sources: int = 12,
    ) -> None:
        self.llm = llm
        self.retriever = retriever
        self.persona = persona
        self.prompts = prompts or default_registry()
        self.per_requirement = per_requirement
        self.max_sources = max_sources

    async def extract(self, description: str, lang: Lang) -> JobRequirements:
        prompt = self.prompts.render("job_fit_extract", language=LANGUAGE_NAMES[lang])
        return await self.llm.structured(
            "job_fit_extract",
            [SystemMessage(prompt.text), HumanMessage(job_description_message(description))],
            JobRequirements,
            tier="fast",
            prompt=prompt.ref,
        )

    async def gather_evidence(
        self, queries: list[str], lang: Lang
    ) -> tuple[list[RetrievedChunk], bool]:
        results = await asyncio.gather(
            *(self.retriever.search(q, lang, top_k=self.per_requirement) for q in queries),
            return_exceptions=True,
        )
        rankings: list[list[RetrievedChunk]] = []
        degraded = False
        for result in results:
            if isinstance(result, RetrievalResult):
                rankings.append(result.chunks)
                degraded = degraded or result.degraded
            else:
                log.warning("job_fit.search_failed", error=repr(result))
                degraded = True
        return interleave(rankings, self.max_sources), degraded

    async def analyze(self, description: str, lang: Lang) -> JobFitResult:
        started = time.perf_counter()
        with track_usage() as usage:
            extracted = await self.extract(description, lang)
            searches = extracted.requirements or [description[:400]]
            chunks, _ = await self.gather_evidence(searches, lang)
            documents = [c.to_dict() for c in chunks]

            prompt = self.prompts.render(
                "job_fit_assess",
                persona=self.persona,
                language=LANGUAGE_NAMES[lang],
            )
            requirements = "\n".join(f"- {r}" for r in searches)
            assessment = await self.llm.structured(
                "job_fit_assess",
                [
                    SystemMessage(prompt.text),
                    sources_message(documents),
                    HumanMessage(
                        job_description_message(description, extracted.role, requirements)
                    ),
                ],
                JobFitAssessment,
                tier="answer",
                prompt=prompt.ref,
            )

        n = len(documents)
        assessment.summary = strip_invalid_markers(assessment.summary, n)
        for item in assessment.requirements:
            item.evidence = strip_invalid_markers(item.evidence, n)
        cited_text = " ".join([assessment.summary, *(r.evidence for r in assessment.requirements)])
        return JobFitResult(
            role=extracted.role,
            score=fit_score([r.status for r in assessment.requirements]),
            assessment=assessment,
            citations=extract_citations(cited_text, documents),
            usage=usage.summary(),
            latency_ms=int((time.perf_counter() - started) * 1000),
            searches=searches,
            tracker=usage,
        )
