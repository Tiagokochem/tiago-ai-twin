import re
from typing import Any

_MARKER = re.compile(r"\[(\d{1,2})\]")


def extract_citations(text: str, documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map [n] markers in the answer to the numbered sources, in order of
    first appearance. Markers outside the source range are ignored."""
    seen: list[int] = []
    for match in _MARKER.finditer(text):
        n = int(match.group(1))
        if 1 <= n <= len(documents) and n not in seen:
            seen.append(n)
    citations = []
    for n in seen:
        doc = documents[n - 1]
        citations.append(
            {
                "n": n,
                "document_key": doc["document_key"],
                "title": doc["title"],
                "heading": doc["heading"],
                "kind": doc["kind"],
                "url": doc.get("url"),
                "snippet": doc["content"][:280],
            }
        )
    return citations


def strip_invalid_markers(text: str, source_count: int) -> str:
    def replace(match: re.Match[str]) -> str:
        return match.group(0) if 1 <= int(match.group(1)) <= source_count else ""

    return _MARKER.sub(replace, text)
