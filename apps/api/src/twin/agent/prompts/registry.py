import hashlib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

TEMPLATES_DIR = Path(__file__).parent / "templates"


@dataclass(frozen=True)
class Prompt:
    name: str
    version: str
    text: str

    @property
    def ref(self) -> str:
        """`name@version`, stored with every LLM call."""
        return f"{self.name}@{self.version}"


def _digest(text: str, size: int) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:size]


class PromptRegistry:
    """Prompts live as Jinja templates next to the code. Each template is
    versioned by the hash of its content plus the shared partials, and
    the registry has an aggregate version that is persisted with every answer,
    so eval results and production traces can be tied to an exact prompt set."""

    def __init__(self, directory: Path = TEMPLATES_DIR) -> None:
        self._env = Environment(
            loader=FileSystemLoader(directory),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False,
        )
        sources = {p.stem: p.read_text(encoding="utf-8") for p in sorted(directory.glob("*.j2"))}
        partials = "".join(text for name, text in sources.items() if name.startswith("_"))
        self._versions = {
            name: _digest(text + partials, 8)
            for name, text in sources.items()
            if not name.startswith("_")
        }
        self.version = _digest("".join(sources.values()), 10)

    @property
    def names(self) -> list[str]:
        return sorted(self._versions)

    def render(self, name: str, /, **variables: Any) -> Prompt:
        text = self._env.get_template(f"{name}.j2").render(**variables).strip()
        return Prompt(name=name, version=self._versions[name], text=text)


@lru_cache
def default_registry() -> PromptRegistry:
    return PromptRegistry()
