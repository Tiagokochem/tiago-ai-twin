from tests.fakes import FakeRetriever, ScriptedProvider, chunk
from twin.agent.job_fit import (
    JobFitAssessment,
    JobFitService,
    JobRequirements,
    RequirementAssessment,
    _interleave,
)
from twin.config import REPO_ROOT
from twin.llm.gateway import LLMGateway
from twin.persona import load_persona
from twin.voice.speech import speakable


def test_interleave_round_robins_and_dedupes() -> None:
    a = [chunk(1), chunk(2), chunk(3)]
    b = [chunk(2), chunk(4)]
    merged = _interleave([a, b], limit=10)
    assert [c.chunk_id for c in merged] == [1, 2, 4, 3]
    assert len(_interleave([a, b], limit=2)) == 2


async def test_job_fit_extracts_retrieves_and_cites() -> None:
    provider = ScriptedProvider(
        structured={
            "JobRequirements": JobRequirements(
                role="AI Engineer", requirements=["Python", "LLM agents"]
            ),
            "JobFitAssessment": JobFitAssessment(
                score=78,
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


def test_speakable_strips_markdown_and_citations() -> None:
    text = "**Nuvartis** is live [1][2].\n\n- Built with [FastAPI](https://x.dev)\n- Contact https://wa.me/55"
    assert speakable(text) == "Nuvartis is live.\nBuilt with FastAPI\nContact"
