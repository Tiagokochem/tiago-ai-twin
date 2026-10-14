from typing import Any

from twin.agent.prompts.registry import Prompt, PromptRegistry, default_registry

LANGUAGE_NAMES = {"pt": "Brazilian Portuguese", "en": "English"}


def format_sources(documents: list[dict[str, Any]]) -> str:
    """Numbered sources wrapped in tags so the model treats them as data."""
    blocks = []
    for n, doc in enumerate(documents, start=1):
        path = (
            doc["title"] if doc["heading"] == doc["title"] else f"{doc['title']} > {doc['heading']}"
        )
        blocks.append(f'<source id="{n}" title="{path}">\n{doc["content"]}\n</source>')
    return "\n".join(blocks)


__all__ = ["LANGUAGE_NAMES", "Prompt", "PromptRegistry", "default_registry", "format_sources"]
