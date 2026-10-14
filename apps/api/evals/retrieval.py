"""Retrieval evaluation: hit@k and MRR over the golden set.

    uv run python -m evals.retrieval --mode hybrid   # needs OPENAI_API_KEY
    uv run python -m evals.retrieval --mode lexical  # full-text only, no API key

Requires the knowledge base to be ingested in DATABASE_URL.
"""

import argparse
import asyncio
import sys
from typing import Any

from evals.common import first_relevant_rank, load_golden, retrieval_metrics, write_report
from twin.config import get_settings
from twin.container import build_embedder_or_none
from twin.db.session import get_engine, get_sessionmaker
from twin.rag.retriever import HybridRetriever


async def run(mode: str, top_k: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    settings = get_settings()
    embedder = build_embedder_or_none(settings) if mode == "hybrid" else None
    if mode == "hybrid" and embedder is None:
        raise SystemExit("hybrid mode needs OPENAI_API_KEY (or use --mode lexical)")
    retriever = HybridRetriever(get_sessionmaker(), embedder)

    rows: list[dict[str, Any]] = []
    for case in load_golden():
        result = await retriever.search(case.question, case.lang, top_k=top_k)
        docs = [c.document_key.split("/", 1)[1] for c in result.chunks]
        rank = first_relevant_rank(docs, case.expected_docs)
        rows.append(
            {
                "id": case.id,
                "lang": case.lang,
                "question": case.question,
                "rank": rank,
                "retrieved": docs,
                "expected": case.expected_docs,
            }
        )
    await get_engine().dispose()

    summary: dict[str, Any] = {
        "mode": mode,
        "top_k": top_k,
        "cases": len(rows),
        **retrieval_metrics([r["rank"] for r in rows], (1, 3, top_k)),
    }
    for lang in ("pt", "en"):
        summary[lang] = retrieval_metrics(
            [r["rank"] for r in rows if r["lang"] == lang], (1, 3, top_k)
        )
    return summary, rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["hybrid", "lexical"], default="hybrid")
    parser.add_argument("--top-k", type=int, default=6)
    parser.add_argument("--min-hit", type=float, default=0.0, help="fail below this hit@k")
    args = parser.parse_args()

    summary, rows = asyncio.run(run(args.mode, args.top_k))
    path = write_report(f"retrieval-{args.mode}", summary, rows)
    for row in rows:
        if row["rank"] is None or row["rank"] > 3:
            print(f"  miss  {row['lang']} {row['id']:24} got {row['retrieved'][:3]}")
    print({k: v for k, v in summary.items() if not isinstance(v, dict)})
    print(f"report: {path}")
    if summary[f"hit@{args.top_k}"] < args.min_hit:
        sys.exit(f"hit@{args.top_k} {summary[f'hit@{args.top_k}']} < {args.min_hit}")


if __name__ == "__main__":
    main()
