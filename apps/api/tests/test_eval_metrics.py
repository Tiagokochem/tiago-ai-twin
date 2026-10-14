from evals.common import (
    fact_recall,
    first_relevant_rank,
    load_golden,
    load_routing,
    retrieval_metrics,
)
from twin.config import REPO_ROOT
from twin.rag.loader import load_knowledge


def test_rank_and_metrics() -> None:
    assert first_relevant_rank(["a", "b", "c"], ["c", "x"]) == 3
    assert first_relevant_rank(["a"], ["x"]) is None

    metrics = retrieval_metrics([1, 2, None, 4], ks=(1, 3))
    assert metrics == {"hit@1": 0.25, "hit@3": 0.5, "mrr": round((1 + 0.5 + 0.25) / 4, 4)}


def test_fact_recall_supports_alternatives() -> None:
    assert fact_recall("Built with LangGraph and pgvector", ["langgraph", "pgvector|RAG"]) == 1
    assert fact_recall("Built with Laravel", ["Laravel", "Vue"]) == 0.5


def test_golden_set_references_existing_documents() -> None:
    ids = {d.meta.id for d in load_knowledge(REPO_ROOT / "knowledge")}
    cases = load_golden()

    assert len(cases) >= 40
    missing = {doc for case in cases for doc in case.expected_docs} - ids
    assert not missing, f"golden set references unknown documents: {missing}"
    assert len(load_routing()) >= 15
