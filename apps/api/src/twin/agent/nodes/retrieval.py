import asyncio

import structlog
from langchain_core.messages import HumanMessage, SystemMessage

from twin.agent.deps import AgentDeps, Node, emit
from twin.agent.prompts import LANGUAGE_NAMES
from twin.agent.schemas import Grade, Rewrite
from twin.agent.state import TwinState
from twin.rag.retriever import fuse_results

log = structlog.get_logger()

MAX_QUESTION_QUERY_CHARS = 300


def make_retrieve(deps: AgentDeps) -> Node:
    async def retrieve_job_fit(state: TwinState) -> TwinState:
        assert deps.job_fit is not None
        extracted = await deps.job_fit.extract(state["question"], state["lang"])
        queries = extracted.requirements or [state["search_query"]]
        chunks, degraded = await deps.job_fit.gather_evidence(queries, state["lang"])
        return {
            "requirements": extracted.requirements,
            "documents": [c.to_dict() for c in chunks],
            "degraded": state.get("degraded", False) or degraded,
        }

    async def retrieve(state: TwinState) -> TwinState:
        emit("status", "searching")
        if state.get("intent") == "job_fit":
            return await retrieve_job_fit(state)

        # Multi-query: the router's standalone keyword query plus the raw
        # question (first attempt only), fused with RRF.
        queries = [state["search_query"]]
        question = state["question"][:MAX_QUESTION_QUERY_CHARS]
        if not state.get("retries") and question.casefold() != queries[0].casefold():
            queries.append(question)
        results = await asyncio.gather(
            *(deps.retriever.search(q, state["lang"], top_k=deps.top_k) for q in queries)
        )
        fused = fuse_results(results, deps.top_k)
        return {
            "documents": [c.to_dict() for c in fused.chunks],
            "degraded": state.get("degraded", False) or fused.degraded,
        }

    return retrieve


def make_grade(deps: AgentDeps) -> Node:
    async def grade(state: TwinState) -> TwinState:
        documents = state.get("documents", [])
        if not documents or state.get("intent") == "job_fit":
            return {}
        passages = "\n\n".join(
            f"<passage id={i}>\n{d['title']} > {d['heading']}\n{d['content']}\n</passage>"
            for i, d in enumerate(documents)
        )
        prompt = deps.prompts.render("grader")
        try:
            result = await deps.llm.structured(
                "grade",
                [
                    SystemMessage(prompt.text),
                    HumanMessage(
                        f"Question: {state['question']}\n"
                        f"Search query: {state['search_query']}\n\n{passages}"
                    ),
                ],
                Grade,
                prompt=prompt.ref,
            )
        except Exception as exc:
            # Fail open: the answer prompt is grounded anyway, and dropping
            # every passage would turn a transient error into a handoff.
            log.warning("agent.grade_failed", error=repr(exc))
            return {}
        keep = sorted({i for i in result.relevant_ids if 0 <= i < len(documents)})
        return {"documents": [documents[i] for i in keep]}

    return grade


def make_rewrite(deps: AgentDeps) -> Node:
    async def rewrite(state: TwinState) -> TwinState:
        prompt = deps.prompts.render("rewrite", language=LANGUAGE_NAMES[state["lang"]])
        result = await deps.llm.structured(
            "rewrite",
            [
                SystemMessage(prompt.text),
                HumanMessage(
                    f"Question: {state['question']}\nPrevious query: {state['search_query']}"
                ),
            ],
            Rewrite,
            prompt=prompt.ref,
        )
        return {
            "search_query": result.query.strip() or state["search_query"],
            "retries": state.get("retries", 0) + 1,
        }

    return rewrite
