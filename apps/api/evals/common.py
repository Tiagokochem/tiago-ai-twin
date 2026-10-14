import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

EVALS_DIR = Path(__file__).parent
DATASETS = EVALS_DIR / "datasets"
REPORTS = EVALS_DIR / "reports"
HISTORY = REPORTS / "history.jsonl"


@dataclass(frozen=True)
class GoldenCase:
    id: str
    lang: str
    question: str
    expected_docs: list[str]
    facts: list[str]


def load_golden(langs: tuple[str, ...] = ("pt", "en")) -> list[GoldenCase]:
    data = yaml.safe_load((DATASETS / "golden.yaml").read_text(encoding="utf-8"))
    cases = []
    for raw in data["cases"]:
        for lang in langs:
            cases.append(
                GoldenCase(
                    id=raw["id"],
                    lang=lang,
                    question=raw[lang]["question"],
                    expected_docs=raw["expected_docs"],
                    facts=raw[lang].get("facts", []),
                )
            )
    return cases


def load_routing() -> list[dict[str, Any]]:
    data = yaml.safe_load((DATASETS / "routing.yaml").read_text(encoding="utf-8"))
    return list(data["cases"])


def load_redteam() -> list[dict[str, Any]]:
    data = yaml.safe_load((DATASETS / "redteam.yaml").read_text(encoding="utf-8"))
    return list(data["cases"])


def first_relevant_rank(retrieved_docs: list[str], expected: list[str]) -> int | None:
    """1-based rank of the first retrieved chunk whose document is expected."""
    for rank, doc in enumerate(retrieved_docs, start=1):
        if doc in expected:
            return rank
    return None


def retrieval_metrics(ranks: list[int | None], ks: tuple[int, ...] = (1, 3, 6)) -> dict[str, float]:
    n = len(ranks) or 1
    metrics = {f"hit@{k}": sum(1 for r in ranks if r is not None and r <= k) / n for k in ks}
    metrics["mrr"] = sum(1 / r for r in ranks if r is not None) / n
    return {k: round(v, 4) for k, v in metrics.items()}


def fact_recall(answer: str, facts: list[str]) -> float:
    if not facts:
        return 1.0
    text = answer.lower()
    hits = sum(1 for fact in facts if any(alt.lower() in text for alt in fact.split("|")))
    return hits / len(facts)


def write_report(name: str, summary: dict[str, Any], rows: list[dict[str, Any]]) -> Path:
    REPORTS.mkdir(exist_ok=True)
    path = REPORTS / f"{name}.json"
    path.write_text(
        json.dumps({"summary": summary, "cases": rows}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    lines = [f"# {name}", "", "| metric | value |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in summary.items() if not isinstance(v, dict | list)]
    for key, value in summary.items():
        if isinstance(value, dict):
            lines += ["", f"## {key}", "", "| metric | value |", "|---|---|"]
            lines += [f"| {k} | {v} |" for k, v in value.items()]
    (REPORTS / f"{name}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    append_history(name, summary)
    return path


def _git_sha() -> str | None:
    if sha := os.environ.get("GITHUB_SHA"):
        return sha[:12]
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None


def append_history(name: str, summary: dict[str, Any]) -> None:
    """One line per run, so metric drift can be traced to a commit and prompt version."""
    entry = {
        "at": datetime.now(UTC).isoformat(timespec="seconds"),
        "eval": name,
        "git_sha": _git_sha(),
        **summary,
    }
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]
