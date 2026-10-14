import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import frontmatter
from pydantic import BaseModel, Field, ValidationError

Lang = Literal["pt", "en"]
Kind = Literal["profile", "experience", "skills", "education", "project", "faq"]

_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


class FrontMatter(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    title: str
    lang: Lang
    kind: Kind
    url: str | None = None
    tags: list[str] = Field(default_factory=list)
    draft: bool = False


@dataclass(frozen=True)
class SourceDocument:
    meta: FrontMatter
    body: str
    path: str

    @property
    def key(self) -> str:
        return f"{self.meta.lang}/{self.meta.id}"


class KnowledgeError(ValueError):
    pass


def load_document(path: Path, root: Path) -> SourceDocument:
    post = frontmatter.load(path)
    try:
        meta = FrontMatter.model_validate(post.metadata)
    except ValidationError as exc:
        raise KnowledgeError(f"{path}: invalid front matter\n{exc}") from exc
    body = _HTML_COMMENT.sub("", post.content).strip()
    return SourceDocument(meta=meta, body=body, path=str(path.relative_to(root)))


def load_knowledge(root: Path) -> list[SourceDocument]:
    """Load every published markdown file under root; keys must be unique."""
    docs: list[SourceDocument] = []
    seen: dict[str, str] = {}
    for path in sorted(root.rglob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        doc = load_document(path, root)
        if doc.meta.draft or not doc.body:
            continue
        if doc.key in seen:
            raise KnowledgeError(f"duplicate key {doc.key}: {seen[doc.key]} and {doc.path}")
        seen[doc.key] = doc.path
        docs.append(doc)
    return docs
