from twin.rag.chunking import chunk_document
from twin.rag.loader import FrontMatter, SourceDocument


def _doc(body: str) -> SourceDocument:
    meta = FrontMatter(id="doc", title="Doc", lang="en", kind="project")
    return SourceDocument(meta=meta, body=body, path="en/doc.md")


def test_splits_by_heading_and_keeps_preamble() -> None:
    chunks = chunk_document(_doc("Intro text.\n\n## Problem\nSlow.\n\n## Solution\nFast."))

    assert [(c.heading, c.content) for c in chunks] == [
        ("Doc", "Intro text."),
        ("Problem", "Slow."),
        ("Solution", "Fast."),
    ]
    assert [c.ord for c in chunks] == [0, 1, 2]


def test_long_sections_split_on_paragraph_boundaries() -> None:
    paragraphs = [f"Paragraph {i} " + "x" * 80 for i in range(10)]
    chunks = chunk_document(_doc("## Big\n" + "\n\n".join(paragraphs)), max_chars=300)

    assert len(chunks) > 1
    assert all(c.heading == "Big" for c in chunks)
    assert all(len(c.content) <= 300 for c in chunks)
    assert "\n\n".join(c.content for c in chunks) == "\n\n".join(paragraphs)


def test_embedding_text_includes_section_path() -> None:
    chunk = chunk_document(_doc("## Problem\nSlow."))[0]

    assert chunk.embedding_text("Doc") == "Doc > Problem\n\nSlow."
