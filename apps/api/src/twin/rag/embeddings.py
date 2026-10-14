import hashlib
import math
from collections import OrderedDict
from typing import Protocol

from openai import AsyncOpenAI


class Embedder(Protocol):
    model: str
    dimensions: int

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class OpenAIEmbedder:
    def __init__(self, api_key: str, model: str, dimensions: int, batch_size: int = 64) -> None:
        self._client = AsyncOpenAI(api_key=api_key, max_retries=3, timeout=30)
        self.model = model
        self.dimensions = dimensions
        self._batch_size = batch_size

    async def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            batch = texts[start : start + self._batch_size]
            response = await self._client.embeddings.create(
                model=self.model, input=batch, dimensions=self.dimensions
            )
            vectors.extend(item.embedding for item in sorted(response.data, key=lambda d: d.index))
        return vectors


class HashEmbedder:
    """Deterministic, offline embedder for tests. Not semantically meaningful."""

    def __init__(self, dimensions: int = 1536) -> None:
        self.model = "hash"
        self.dimensions = dimensions

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def _vector(self, text: str) -> list[float]:
        values: list[float] = []
        counter = 0
        while len(values) < self.dimensions:
            digest = hashlib.sha256(f"{counter}:{text}".encode()).digest()
            values.extend((byte - 127.5) / 127.5 for byte in digest)
            counter += 1
        values = values[: self.dimensions]
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return [v / norm for v in values]


class CachedEmbedder:
    """LRU cache in front of an embedder. Query embeddings repeat a lot
    (suggested questions, evals, retries), and each one is a network call."""

    def __init__(self, inner: Embedder, max_entries: int = 2048) -> None:
        self.inner = inner
        self.model = inner.model
        self.dimensions = inner.dimensions
        self._max = max_entries
        self._cache: OrderedDict[str, list[float]] = OrderedDict()

    async def embed(self, texts: list[str]) -> list[list[float]]:
        missing = list(dict.fromkeys(t for t in texts if t not in self._cache))
        if missing:
            for text, vector in zip(missing, await self.inner.embed(missing), strict=True):
                self._cache[text] = vector
        for text in texts:
            self._cache.move_to_end(text)
        while len(self._cache) > self._max:
            self._cache.popitem(last=False)
        return [self._cache[t] for t in texts]
