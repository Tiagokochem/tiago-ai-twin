import pytest
from jinja2 import UndefinedError
from langchain_core.messages import AIMessage, HumanMessage

from tests.fakes import chunk
from twin.agent import context, routing
from twin.agent.citations import CitationStreamFilter, strip_invalid_markers
from twin.agent.prompts import PromptRegistry, default_registry
from twin.agent.schemas import Followups
from twin.config import REPO_ROOT
from twin.persona import load_persona
from twin.rag.embeddings import CachedEmbedder, HashEmbedder
from twin.rag.retriever import RetrievalResult, fuse_results


@pytest.mark.parametrize(
    "tokens",
    [
        ["Built it [1]", " and [7] more [2]."],
        ["Built it [", "1] and [", "7", "] more [2", "]."],
        list("Built it [1] and [7] more [2]."),
    ],
)
def test_citation_stream_filter_matches_final_text(tokens: list[str]) -> None:
    marker_filter = CitationStreamFilter(source_count=2)
    streamed = "".join(marker_filter.feed(t) for t in tokens) + marker_filter.flush()
    assert streamed == strip_invalid_markers("".join(tokens), 2)
    assert streamed == "Built it [1] and  more [2]."


def test_citation_stream_filter_passes_plain_brackets() -> None:
    marker_filter = CitationStreamFilter(source_count=3)
    text = "[link](x) [abc] [12345] trailing ["
    streamed = "".join(marker_filter.feed(c) for c in text) + marker_filter.flush()
    assert streamed == text


def test_prompt_registry_versions_and_strict_variables() -> None:
    registry = default_registry()
    persona = load_persona(REPO_ROOT / "persona.yaml")
    prompt = registry.render("router", persona=persona, default_lang="pt")
    assert prompt.ref.startswith("router@") and len(prompt.version) == 8
    assert registry.render("router", persona=persona, default_lang="en").version == prompt.version
    assert len(registry.version) == 10
    assert {"answer", "router", "grader", "job_fit_assess"} <= set(registry.names)
    with pytest.raises(UndefinedError):
        registry.render("answer", persona=persona)


def test_prompt_version_changes_with_content(tmp_path) -> None:  # type: ignore[no-untyped-def]
    (tmp_path / "a.j2").write_text("hello {{ name }}")
    before = PromptRegistry(tmp_path)
    (tmp_path / "a.j2").write_text("hi {{ name }}")
    after = PromptRegistry(tmp_path)
    assert before.render("a", name="x").version != after.render("a", name="x").version
    assert before.version != after.version


def test_answer_prompt_is_grounded_except_smalltalk() -> None:
    registry = default_registry()
    persona = load_persona(REPO_ROOT / "persona.yaml")
    common = {"persona": persona, "lang": "pt", "language": "Portuguese", "requirements": []}
    web = registry.render("answer", channel="web", mode="answer", **common).text
    whatsapp = registry.render("answer", channel="whatsapp", mode="answer", **common).text
    smalltalk = registry.render("answer", channel="web", mode="smalltalk", **common).text
    assert "<sources>" in web and "Markdown" in web
    assert "WhatsApp" in whatsapp
    assert "<sources>" not in smalltalk


def test_followups_are_truncated_not_rejected() -> None:
    result = Followups(questions=["a?", " ", "b?", "c?", "d?"])
    assert result.questions == ["a?", "b?", "c?"]


def test_history_respects_token_budget_and_keeps_latest() -> None:
    pasted = "x " * 5_000
    messages = [
        HumanMessage(pasted),
        AIMessage("ok"),
        *[m for i in range(30) for m in (HumanMessage(f"q{i} " * 20), AIMessage(f"a{i} " * 20))],
        HumanMessage("latest question"),
    ]
    trimmed = context.history(messages, max_tokens=400)
    assert trimmed[-1].content == "latest question"
    assert isinstance(trimmed[0], HumanMessage)
    assert len(trimmed) < len(messages)
    assert context.history([HumanMessage(pasted)], max_tokens=10)[0].content == pasted


def test_sources_message_wraps_documents() -> None:
    message = context.sources_message([chunk(1, "Skills", "Python").to_dict()])
    assert isinstance(message, HumanMessage)
    assert '<source id="1" title="Skills > Python">' in str(message.content)


async def test_cached_embedder_hits_cache() -> None:
    inner = HashEmbedder(8)
    calls: list[list[str]] = []
    original = inner.embed

    async def spy(texts: list[str]) -> list[list[float]]:
        calls.append(texts)
        return await original(texts)

    inner.embed = spy  # type: ignore[method-assign]
    cached = CachedEmbedder(inner, max_entries=2)
    first = await cached.embed(["a", "b", "a"])
    second = await cached.embed(["b", "c"])
    assert calls == [["a", "b"], ["c"]]
    assert first[0] == first[2] and second[0] == first[1]
    await cached.embed(["a"])  # evicted ("a" was least recently used)
    assert calls[-1] == ["a"]


def test_fuse_results_prefers_chunks_found_by_both_queries() -> None:
    a = RetrievalResult([chunk(1), chunk(2), chunk(3)])
    b = RetrievalResult([chunk(3), chunk(4)], degraded=True)
    fused = fuse_results([a, b], top_k=3)
    assert fused.chunks[0].chunk_id == 3
    assert len(fused.chunks) == 3 and fused.degraded


def test_followups_run_in_parallel_only_on_interactive_channels() -> None:
    assert routing.after_analyze({"intent": "about_tiago", "channel": "web"}) == [
        "retrieve",
        "followups",
    ]
    assert routing.after_analyze({"intent": "smalltalk", "channel": "widget"}) == [
        "answer",
        "followups",
    ]
    assert routing.after_analyze({"intent": "about_tiago", "channel": "whatsapp"}) == ["retrieve"]
    assert routing.after_analyze({"intent": "handoff", "channel": "web"}) == ["handoff"]
    assert routing.after_analyze({"intent": "off_topic", "channel": "web"}) == ["refuse"]
