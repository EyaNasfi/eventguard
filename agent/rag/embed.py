"""Embedders. `GeminiEmbedder` is the real one (model from config/configurations.yaml);
`HashingEmbedder` is a deterministic offline stand-in for tests.

gemini-embedding-2 has no task_type; the official docs (checked 2026-11-12) use text prefixes:
documents `title: {title} | text: {content}`, queries `task: search result | query: {content}`.
Several texts must be sent as one `Content` each: a list of plain strings is merged into a
single embedding (found by test on 2026-11-12).

Free tier (seen 2026-11-12): the limit is 100 embedded *texts* per minute per model, counted per
text, not per request. The embedder paces itself under `texts_per_minute` and, on a 429, waits
for the `retryDelay` that the API returns.
"""

import hashlib
import math
import re
import time
from collections import deque
from collections.abc import Callable, Sequence
from typing import Protocol

from google import genai
from google.genai import errors, types


class Embedder(Protocol):
    calls: int
    fingerprint: str  # model + dimensions: a change forces re-embedding

    def embed_documents(self, items: Sequence[tuple[str, str]]) -> list[list[float]]:
        """items: (title, text) pairs."""
        ...

    def embed_query(self, query: str) -> list[float]: ...


def document_text(title: str, text: str) -> str:
    return f"title: {title or 'none'} | text: {text}"


def query_text(query: str) -> str:
    return f"task: search result | query: {query}"


def retry_delay(exc: errors.APIError) -> float | None:
    """Seconds from the API's RetryInfo ('49s'), when present."""
    details = (exc.details or {}).get("error", {}).get("details", []) if exc.details else []
    for d in details:
        if str(d.get("@type", "")).endswith("RetryInfo"):
            match = re.match(r"([\d.]+)s", str(d.get("retryDelay", "")))
            if match:
                return float(match.group(1))
    return None


class GeminiEmbedder:
    BATCH = 40

    def __init__(
        self,
        api_key: str,
        model: str,
        dimensions: int,
        retries: int = 5,
        texts_per_minute: int = 90,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.dimensions = dimensions
        self.fingerprint = f"{model}:{dimensions}"
        self.retries = retries
        self.texts_per_minute = texts_per_minute
        self.sleep = sleep
        self.clock = clock
        self.calls = 0
        self.texts = 0
        self._sent: deque[tuple[float, int]] = deque()

    def _pace(self, n: int) -> None:
        while True:
            now = self.clock()
            while self._sent and now - self._sent[0][0] >= 60:
                self._sent.popleft()
            if sum(c for _, c in self._sent) + n <= self.texts_per_minute or not self._sent:
                self._sent.append((now, n))
                return
            self.sleep(60 - (now - self._sent[0][0]) + 0.5)

    def _embed(self, texts: list[str]) -> list[list[float]]:
        contents = [types.Content(parts=[types.Part(text=t)]) for t in texts]
        config = types.EmbedContentConfig(output_dimensionality=self.dimensions)
        delay = 2.0
        for attempt in range(self.retries + 1):
            self._pace(len(texts))
            try:
                self.calls += 1
                self.texts += len(texts)
                result = self.client.models.embed_content(
                    model=self.model, contents=contents, config=config
                )
                vectors = [list(e.values or []) for e in result.embeddings or []]
                if len(vectors) != len(texts):
                    raise RuntimeError(f"asked {len(texts)} embeddings, got {len(vectors)}")
                return vectors
            except errors.APIError as exc:
                if exc.code not in (429, 500, 503) or attempt == self.retries:
                    raise
                self.sleep(max(delay, (retry_delay(exc) or 0) + 1))
                delay *= 2
        raise RuntimeError("unreachable")

    def embed_documents(self, items: Sequence[tuple[str, str]]) -> list[list[float]]:
        texts = [document_text(title, text) for title, text in items]
        out: list[list[float]] = []
        for start in range(0, len(texts), self.BATCH):
            out.extend(self._embed(texts[start : start + self.BATCH]))
        return out

    def embed_query(self, query: str) -> list[float]:
        return self._embed([query_text(query)])[0]


class HashingEmbedder:
    """Bag-of-words hashed into a fixed vector, L2-normalised. Offline and deterministic."""

    def __init__(self, dimensions: int = 256) -> None:
        self.dimensions = dimensions
        self.fingerprint = f"hashing:{dimensions}"
        self.calls = 0

    def _vector(self, text: str) -> list[float]:
        vec = [0.0] * self.dimensions
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            if len(word) < 3:
                continue
            h = int(hashlib.sha256(word.encode()).hexdigest(), 16)
            vec[h % self.dimensions] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, items: Sequence[tuple[str, str]]) -> list[list[float]]:
        self.calls += 1
        return [self._vector(f"{title} {text}") for title, text in items]

    def embed_query(self, query: str) -> list[float]:
        self.calls += 1
        return self._vector(query)
