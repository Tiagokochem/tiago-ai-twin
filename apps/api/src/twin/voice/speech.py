import re
import time
from collections.abc import AsyncIterator
from typing import Protocol

import structlog
from openai import AsyncOpenAI

from twin.config import Settings
from twin.persona import Lang

log = structlog.get_logger()

TRANSCRIBE_HINT = {
    "pt": "Entrevista de emprego com Tiago Kochem. Termos: Laravel, Python, FastAPI, LangGraph, "
    "RAG, pgvector, Nuvartis, DevBrief, Next.js.",
    "en": "Job interview with Tiago Kochem. Terms: Laravel, Python, FastAPI, LangGraph, RAG, "
    "pgvector, Nuvartis, DevBrief, Next.js.",
}

VOICE_INSTRUCTIONS = {
    "pt": "Fale em português do Brasil, em tom profissional, calmo e simpático, como um "
    "candidato confiante em uma entrevista.",
    "en": "Speak in clear English with a light Brazilian accent, in a calm, friendly and "
    "professional tone, like a confident candidate in an interview.",
}


class Speech(Protocol):
    async def transcribe(self, audio: bytes, filename: str, lang: Lang | None) -> str: ...

    def synthesize(self, text: str, lang: Lang) -> AsyncIterator[bytes]: ...


class OpenAISpeech:
    def __init__(
        self, api_key: str, stt_model: str, tts_model: str, voice: str, timeout: float = 60.0
    ) -> None:
        self._client = AsyncOpenAI(api_key=api_key, timeout=timeout)
        self.stt_model = stt_model
        self.tts_model = tts_model
        self.voice = voice

    async def transcribe(self, audio: bytes, filename: str, lang: Lang | None) -> str:
        started = time.perf_counter()
        if lang:
            result = await self._client.audio.transcriptions.create(
                model=self.stt_model,
                file=(filename, audio),
                language=lang,
                prompt=TRANSCRIBE_HINT[lang],
            )
        else:
            result = await self._client.audio.transcriptions.create(
                model=self.stt_model, file=(filename, audio), prompt=TRANSCRIBE_HINT["en"]
            )
        text = result.text.strip()
        log.info(
            "voice.transcribe",
            model=self.stt_model,
            bytes=len(audio),
            latency_ms=int((time.perf_counter() - started) * 1000),
        )
        return text

    async def synthesize(self, text: str, lang: Lang) -> AsyncIterator[bytes]:
        async with self._client.audio.speech.with_streaming_response.create(
            model=self.tts_model,
            voice=self.voice,
            input=text,
            instructions=VOICE_INSTRUCTIONS[lang],
            response_format="mp3",
        ) as response:
            async for chunk in response.iter_bytes(8192):
                yield chunk


def build_speech(settings: Settings) -> Speech | None:
    key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else ""
    if not key:
        return None
    return OpenAISpeech(key, settings.stt_model, settings.tts_model, settings.tts_voice)


_CITATION = re.compile(r"\s?\[\d{1,2}\]")
_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_URL = re.compile(r"(https?://|mailto:)\S+")
_MARKUP = re.compile(r"[*_`#>|]+")
_BULLET = re.compile(r"^\s*(?:[-•]|\d+[.)])\s+", re.MULTILINE)


def speakable(text: str) -> str:
    """Turn a Markdown answer with [n] citations into plain text for TTS."""
    text = _CITATION.sub("", text)
    text = _LINK.sub(r"\1", text)
    text = _URL.sub("", text)
    text = _BULLET.sub("", text)
    text = _MARKUP.sub("", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return re.sub(r"[ \t]{2,}", " ", text).strip()
