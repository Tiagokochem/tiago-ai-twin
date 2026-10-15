import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel

Lang = Literal["pt", "en"]


class Localized(BaseModel):
    pt: str
    en: str

    def get(self, lang: Lang) -> str:
        return self.pt if lang == "pt" else self.en


class LocalizedList(BaseModel):
    pt: list[str]
    en: list[str]

    def get(self, lang: Lang) -> list[str]:
        return self.pt if lang == "pt" else self.en


class Messages(BaseModel):
    disclaimer: Localized
    handoff: Localized
    unknown: Localized
    off_topic: Localized
    refusal: Localized
    unavailable: Localized
    limit_reached: Localized
    direct_contact: Localized
    whatsapp_welcome: Localized
    human_requested: Localized
    session_reset: Localized
    slow_down: Localized
    audio_failed: Localized


MessageName = Literal[
    "disclaimer",
    "handoff",
    "unknown",
    "off_topic",
    "refusal",
    "unavailable",
    "limit_reached",
    "direct_contact",
    "whatsapp_welcome",
    "human_requested",
    "session_reset",
    "slow_down",
    "audio_failed",
]


class Persona(BaseModel):
    name: str
    short_name: str
    role: Localized
    website: str
    email: str
    github: str | None = None
    location: str
    languages: list[Lang]
    default_language: Lang
    tone: Localized
    handoff_topics: list[str]
    known_names: list[str] = []
    starter_questions: LocalizedList
    messages: Messages
    owner_whatsapp: str | None = None

    @property
    def owner_contact_link(self) -> str:
        if self.owner_whatsapp:
            return f"https://wa.me/{self.owner_whatsapp}"
        return f"mailto:{self.email}"

    def message(self, name: MessageName, lang: Lang) -> str:
        template: Localized = getattr(self.messages, name)
        return template.get(lang).format(owner_contact_link=self.owner_contact_link)


def normalize_phone(number: str | None) -> str | None:
    digits = re.sub(r"\D", "", number or "")
    return digits or None


def load_persona(path: Path, owner_whatsapp: str | None = None) -> Persona:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["owner_whatsapp"] = normalize_phone(owner_whatsapp)
    return Persona.model_validate(data)
