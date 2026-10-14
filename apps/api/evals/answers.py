"""End-to-end evaluation of the agent with real LLM providers.

    uv run python -m evals.answers              # golden set (pt + en) and routing
    uv run python -m evals.answers --limit 10   # quick run

Metrics:
- routing accuracy (intent and handoff reason) on datasets/routing.yaml
- fact recall: expected facts present in the answer
- citation rate: answers that cite at least one source
- faithfulness and relevance (1-5) judged by an LLM against the sources
- latency, tokens and cost per answer
"""

import argparse
import asyncio
import statistics
import sys
import time
import uuid
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel, Field

from evals.common import fact_recall, load_golden, load_routing, write_report
from twin.agent import prompts
from twin.agent.graph import AgentDeps, Analysis, build_graph
from twin.agent.state import turn_input
from twin.config import get_settings
from twin.container import build_embedder_or_none
from twin.db.session import get_engine, get_sessionmaker
from twin.llm.gateway import LLMGateway
from twin.llm.providers import build_providers
from twin.llm.usage import track_usage
from twin.persona import Persona, load_persona
from twin.rag.retriever import HybridRetriever


class Judgement(BaseModel):
    faithfulness: int = Field(ge=1, le=5, description="5 = every claim is supported")
    relevance: int = Field(ge=1, le=5, description="5 = fully answers the question")
    unsupported_claims: list[str] = Field(default_factory=list)


JUDGE_PROMPT = """You grade answers produced by an assistant that speaks on behalf of a job \
candidate. Compare the ANSWER with the SOURCES.
- faithfulness (1-5): 5 if every factual claim about the candidate is supported by the \
SOURCES; lower it for each unsupported or contradicted claim. Saying "I don't have that \
information" is faithful.
- relevance (1-5): 5 if the answer directly and completely addresses the QUESTION.
- unsupported_claims: list each claim not supported by the SOURCES (empty if none)."""


async def judge(
    llm: LLMGateway, question: str, answer: str, documents: list[dict[str, Any]]
) -> Judgement:
    sources = "\n\n".join(
        f"[{i}] {d['title']} > {d['heading']}\n{d['content']}"
        for i, d in enumerate(documents, start=1)
    )
    return await llm.structured(
        "judge",
        [
            SystemMessage(JUDGE_PROMPT),
            HumanMessage(f"QUESTION:\n{question}\n\nSOURCES:\n{sources}\n\nANSWER:\n{answer}"),
        ],
        Judgement,
        tier="answer",
    )


async def eval_routing(llm: LLMGateway, persona: Persona) -> tuple[dict[str, Any], list[Any]]:
    rows = []
    for case in load_routing():
        result = await llm.structured(
            "analyze",
            [SystemMessage(prompts.router_prompt(persona)), HumanMessage(case["question"])],
            Analysis,
        )
        ok = result.intent == case["intent"] and (
            "reason" not in case or result.handoff_reason == case["reason"]
        )
        rows.append(
            {
                "question": case["question"].strip()[:80],
                "expected": case["intent"],
                "expected_reason": case.get("reason"),
                "got": result.intent,
                "got_reason": result.handoff_reason,
                "ok": ok,
            }
        )
    intent_ok = sum(1 for r in rows if r["expected"] == r["got"]) / len(rows)
    full_ok = sum(1 for r in rows if r["ok"]) / len(rows)
    return {"intent_accuracy": round(intent_ok, 4), "full_accuracy": round(full_ok, 4)}, rows


async def eval_answers(
    llm: LLMGateway, persona: Persona, limit: int | None
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    settings = get_settings()
    retriever = HybridRetriever(get_sessionmaker(), build_embedder_or_none(settings))
    graph = build_graph(AgentDeps(llm=llm, retriever=retriever, persona=persona), InMemorySaver())

    rows: list[dict[str, Any]] = []
    for case in load_golden()[:limit]:
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        started = time.perf_counter()
        with track_usage() as usage:
            await graph.ainvoke(turn_input(case.question, case.lang, "eval"), config)  # type: ignore[arg-type]
        state = (await graph.aget_state(config)).values  # type: ignore[arg-type]
        latency = time.perf_counter() - started
        answer = state.get("response", "")
        documents = state.get("documents", [])
        verdict = await judge(llm, case.question, answer, documents)
        rows.append(
            {
                "id": case.id,
                "lang": case.lang,
                "intent": state.get("intent"),
                "handoff": state.get("handoff_reason"),
                "fact_recall": round(fact_recall(answer, case.facts), 3),
                "cited": bool(state.get("citations")),
                "faithfulness": verdict.faithfulness,
                "relevance": verdict.relevance,
                "unsupported_claims": verdict.unsupported_claims,
                "latency_s": round(latency, 2),
                "tokens": usage.total_tokens,
                "cost_usd": round(usage.total_cost_usd, 6),
                "answer": answer,
            }
        )
        print(
            f"  {case.lang} {case.id:24} facts={rows[-1]['fact_recall']:.2f} "
            f"faith={verdict.faithfulness} rel={verdict.relevance} {latency:.1f}s"
        )

    n = len(rows) or 1
    latencies = [r["latency_s"] for r in rows] or [0.0]
    summary = {
        "cases": len(rows),
        "fact_recall": round(sum(r["fact_recall"] for r in rows) / n, 4),
        "citation_rate": round(sum(1 for r in rows if r["cited"]) / n, 4),
        "faithfulness": round(sum(r["faithfulness"] for r in rows) / n, 3),
        "relevance": round(sum(r["relevance"] for r in rows) / n, 3),
        "handoff_rate": round(sum(1 for r in rows if r["handoff"]) / n, 4),
        "latency_p50_s": round(statistics.median(latencies), 2),
        "latency_p95_s": round(sorted(latencies)[int(0.95 * (len(latencies) - 1))], 2),
        "cost_per_answer_usd": round(sum(r["cost_usd"] for r in rows) / n, 6),
    }
    return summary, rows


async def run(limit: int | None) -> dict[str, Any]:
    settings = get_settings()
    providers = build_providers(settings)
    if not providers:
        raise SystemExit("set OPENAI_API_KEY and/or DEEPSEEK_API_KEY")
    llm = LLMGateway(providers, settings.llm_timeout_seconds)
    persona = load_persona(settings.persona_path, settings.whatsapp_owner_number)

    routing, routing_rows = await eval_routing(llm, persona)
    write_report("routing", routing, routing_rows)
    for row in routing_rows:
        if not row["ok"]:
            print(f"  route miss: {row['question']!r} expected {row['expected']} got {row['got']}")

    answers, answer_rows = await eval_answers(llm, persona, limit)
    write_report("answers", answers, answer_rows)
    await get_engine().dispose()
    return {"routing": routing, "answers": answers}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--min-faithfulness", type=float, default=0.0)
    args = parser.parse_args()

    result = asyncio.run(run(args.limit))
    print(result)
    if result["answers"]["faithfulness"] < args.min_faithfulness:
        sys.exit(f"faithfulness below {args.min_faithfulness}")


if __name__ == "__main__":
    main()
