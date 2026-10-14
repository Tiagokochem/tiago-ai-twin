from pathlib import Path

import pytest


@pytest.fixture
def knowledge_dir(tmp_path: Path) -> Path:
    root = tmp_path / "knowledge"
    (root / "pt").mkdir(parents=True)
    (root / "en").mkdir(parents=True)
    (root / "pt" / "perfil.md").write_text(
        "---\nid: profile\ntitle: Perfil\nlang: pt\nkind: profile\n---\n"
        "Introdução.\n\n## Resumo\nDesenvolvedor full stack.\n\n<!-- nota interna -->\n"
        "## Stack\nLaravel e Python.\n",
        encoding="utf-8",
    )
    (root / "en" / "profile.md").write_text(
        "---\nid: profile\ntitle: Profile\nlang: en\nkind: profile\n---\n"
        "## Summary\nFull stack developer.\n",
        encoding="utf-8",
    )
    (root / "en" / "draft.md").write_text(
        "---\nid: wip\ntitle: WIP\nlang: en\nkind: faq\ndraft: true\n---\nNot ready.\n",
        encoding="utf-8",
    )
    return root
