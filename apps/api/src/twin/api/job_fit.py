from typing import Any, Literal

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from twin.agent.state import Lang
from twin.api.deps import ContainerDep, rate_limited
from twin.llm.gateway import AllProvidersFailedError

log = structlog.get_logger()

router = APIRouter(prefix="/v1", tags=["job-fit"])


class JobFitIn(BaseModel):
    description: str = Field(min_length=60)
    lang: Lang = "pt"


class RequirementOut(BaseModel):
    requirement: str
    status: Literal["met", "partial", "gap"]
    evidence: str


class JobFitOut(BaseModel):
    role: str
    score: int
    summary: str
    requirements: list[RequirementOut]
    strengths: list[str]
    gaps: list[str]
    citations: list[dict[str, Any]]
    searches: list[str]
    latency_ms: int
    usage: dict[str, Any]


@router.post("/job-fit", response_model=JobFitOut, dependencies=[Depends(rate_limited)])
async def job_fit(body: JobFitIn, container: ContainerDep) -> JobFitOut:
    limit = container.settings.max_job_description_chars
    if len(body.description) > limit:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"description longer than {limit} characters"
        )
    try:
        result = await container.job_fit.analyze(body.description.strip(), body.lang)
    except AllProvidersFailedError as exc:
        log.error("job_fit.providers_failed", error=str(exc))
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "LLM unavailable") from exc
    a = result.assessment
    return JobFitOut(
        role=result.role,
        score=a.score,
        summary=a.summary,
        requirements=[RequirementOut(**r.model_dump()) for r in a.requirements],
        strengths=a.strengths,
        gaps=a.gaps,
        citations=result.citations,
        searches=result.searches,
        latency_ms=result.latency_ms,
        usage=result.usage,
    )
