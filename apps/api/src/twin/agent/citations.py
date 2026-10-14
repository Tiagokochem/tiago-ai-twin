import re
from typing import Any

_MARKER = re.compile(r"\[(\d{1,2})\]")
_SENTENCE = re.compile(r"(?<=[.!?])\s+")


def extract_citations(
    text: str, documents: list[dict[str, Any]], *, query: str = ""
) -> list[dict[str, Any]]:
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
                "snippet": best_snippet(doc["content"], _claims_for(text, n) or query),
            }
        )
    return citations


def _claims_for(text: str, n: int) -> str:
    """Sentences of the answer that cite source n."""
    return " ".join(s for s in _SENTENCE.split(text) if f"[{n}]" in s)


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"\w+", text.lower()) if len(w) > 3}


def best_snippet(content: str, claim: str, size: int = 280) -> str:
    """The passage window that overlaps most with the claim it supports, so
    the UI shows the evidence instead of the first lines of the chunk."""
    sentences = [s.strip() for s in _SENTENCE.split(content) if s.strip()]
    if not sentences or not claim:
        return content[:size]
    target = _words(claim)
    best, best_score = 0, -1
    for i in range(len(sentences)):
        score = len(_words(" ".join(sentences[i : i + 2])) & target)
        if score > best_score:
            best, best_score = i, score
    window = ""
    for sentence in sentences[best:]:
        if window and len(window) + len(sentence) > size:
            break
        window = f"{window} {sentence}".strip()
    return window[:size]


def strip_invalid_markers(text: str, source_count: int) -> str:
    def replace(match: re.Match[str]) -> str:
        return match.group(0) if 1 <= int(match.group(1)) <= source_count else ""

    return _MARKER.sub(replace, text)


class CitationStreamFilter:
    """Removes invalid [n] markers from a token stream.

    A '[' is held back until it can be decided (closing ']' or a non-digit),
    so what the user sees while streaming equals the stored answer."""

    def __init__(self, source_count: int) -> None:
        self.source_count = source_count
        self._held = ""

    def feed(self, token: str) -> str:
        out: list[str] = []
        for char in token:
            if self._held:
                self._held += char
                if char == "]":
                    out.append(strip_invalid_markers(self._held, self.source_count))
                    self._held = ""
                elif not char.isdigit() or len(self._held) > 4:
                    out.append(self._held)
                    self._held = ""
            elif char == "[":
                self._held = char
            else:
                out.append(char)
        return "".join(out)

    def flush(self) -> str:
        held, self._held = self._held, ""
        return held
