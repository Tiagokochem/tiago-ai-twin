from pathlib import Path

import pytest

from twin.config import REPO_ROOT
from twin.rag.loader import KnowledgeError, load_knowledge


def test_loads_published_documents_and_strips_comments(knowledge_dir: Path) -> None:
    docs = load_knowledge(knowledge_dir)

    assert sorted(d.key for d in docs) == ["en/profile", "pt/profile"]
    pt = next(d for d in docs if d.key == "pt/profile")
    assert "nota interna" not in pt.body
    assert pt.path == "pt/perfil.md"


def test_rejects_duplicate_keys(knowledge_dir: Path) -> None:
    (knowledge_dir / "pt" / "copia.md").write_text(
        "---\nid: profile\ntitle: Cópia\nlang: pt\nkind: profile\n---\nTexto.\n",
        encoding="utf-8",
    )
    with pytest.raises(KnowledgeError, match="duplicate key pt/profile"):
        load_knowledge(knowledge_dir)


def test_rejects_invalid_front_matter(knowledge_dir: Path) -> None:
    (knowledge_dir / "pt" / "ruim.md").write_text(
        "---\nid: Ruim Id\ntitle: X\nlang: es\nkind: profile\n---\nTexto.\n",
        encoding="utf-8",
    )
    with pytest.raises(KnowledgeError, match="invalid front matter"):
        load_knowledge(knowledge_dir)


def test_repository_knowledge_is_valid_and_bilingual() -> None:
    docs = load_knowledge(REPO_ROOT / "knowledge")
    pt = {d.meta.id for d in docs if d.meta.lang == "pt"}
    en = {d.meta.id for d in docs if d.meta.lang == "en"}

    assert pt, "knowledge/ has no Portuguese documents"
    assert pt == en, f"documents missing a translation: {sorted(pt ^ en)}"
