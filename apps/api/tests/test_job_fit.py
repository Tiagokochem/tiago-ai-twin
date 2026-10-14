from tests.fakes import FakeRetriever, ScriptedProvider, chunk
from twin.agent.job_fit import (
    JobFitAssessment,
    JobFitService,
    JobRequirements,
    RequirementAssessment,
    fit_score,
    interleave,
)
from twin.config import REPO_ROOT
from twin.llm.gateway import LLMGateway
from twin.persona import load_persona
from twin.voice.speech import speakable


def test_interleave_round_robins_and_dedupes() -> None:
    a = [chunk(1), chunk(2), chunk(3)]
    b = [chunk(2), chunk(4)]
    merged = interleave([a, b], limit=10)
    assert [c.chunk_id for c in merged] == [1, 2, 4, 3]
    assert len(interleave([a, b], limit=2)) == 2


async def test_job_fit_extracts_retrieves_and_cites() -> None:
    provider = ScriptedProvider(
        structured={
            "JobRequirements": JobRequirements(
                role="AI Engineer", requirements=["Python", "LLM agents"]
            ),
            "JobFitAssessment": JobFitAssessment(
                summary="Strong fit [1], agents in own products [2][9].",
                requirements=[
                    RequirementAssessment(
                        requirement="Python", status="met", evidence="FastAPI [1]."
                    ),
                    RequirementAssessment(
                        requirement="LLM agents", status="partial", evidence="Own products [2]."
                    ),
                ],
                strengths=["Python"],
                gaps=["Scale"],
            ),
        }
    )
    retriever = FakeRetriever([chunk(1, "Skills"), chunk(2, "Nuvartis")])
    persona = load_persona(REPO_ROOT / "persona.yaml")
    service = JobFitService(LLMGateway([provider]), retriever, persona)

    result = await service.analyze("We need a Python AI engineer to build agents.", "en")

    assert result.role == "AI Engineer"
    assert [q for q, _ in retriever.queries] == ["Python", "LLM agents"]
    assert result.assessment.summary.endswith("[2].")  # [9] does not exist and is removed
    assert [c["n"] for c in result.citations] == [1, 2]
    assert result.usage["llm_calls"] == 2
    assert result.score == 83  # met (weight 2) + partial (weight 1)


def test_fit_score_is_deterministic_and_rank_weighted() -> None:
    assert fit_score([]) == 0
    assert fit_score(["met", "met"]) == 100
    assert fit_score(["gap", "gap"]) == 0
    assert fit_score(["met", "gap"]) > fit_score(["gap", "met"])


def test_speakable_strips_markdown_and_citations() -> None:
    text = "**Nuvartis** is live [1][2].\n\n- Built with [FastAPI](https://x.dev)\n- Contact https://wa.me/55"
    assert speakable(text) == "Nuvartis is live.\nBuilt with FastAPI\nContact"
