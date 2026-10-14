import re
from dataclasses import dataclass

from twin.rag.loader import SourceDocument

# Bump when the chunking strategy changes so every document is re-embedded.
CHUNKING_VERSION = "1"

_HEADING = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class TextChunk:
    ord: int
    heading: str
    content: str

    def embedding_text(self, title: str) -> str:
        """Prefix the chunk with its document/section path so it stays
        self-explanatory once retrieved in isolation."""
        path = title if self.heading == title else f"{title} > {self.heading}"
        return f"{path}\n\n{self.content}"


def _sections(body: str, title: str) -> list[tuple[str, str]]:
    matches = list(_HEADING.finditer(body))
    if not matches:
        return [(title, body.strip())]
    sections: list[tuple[str, str]] = []
    preamble = body[: matches[0].start()].strip()
    if preamble:
        sections.append((title, preamble))
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        text = body[match.end() : end].strip()
        if text:
            sections.append((match.group(2).strip(), text))
    return sections


def _split_long(text: str, max_chars: int) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    parts: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) <= max_chars or not current:
            current = candidate
        else:
            parts.append(current)
            current = paragraph
    if current:
        parts.append(current)
    return parts


def chunk_document(doc: SourceDocument, max_chars: int = 1200) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    for heading, text in _sections(doc.body, doc.meta.title):
        for part in _split_long(text, max_chars):
            chunks.append(TextChunk(ord=len(chunks), heading=heading, content=part))
    return chunks
