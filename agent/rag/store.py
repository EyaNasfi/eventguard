"""The `VectorStore` interface and its implementations. To swap Chroma for another store,
change only this file (PL decision #4, S2-03).

`ChromaHttpStore` talks to a Chroma server (image chromadb/chroma 1.5.9) through its REST v2
API with plain httpx, so neither the gateway nor the retriever needs the chromadb package.
Each stored chunk carries a `digest` (content + embedding model), so ingestion re-embeds only
what changed.
"""

import math
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from agent.rag.sheets import Chunk


@dataclass(frozen=True)
class Hit:
    sheet_id: str
    title: str
    section: str
    text: str
    score: float  # cosine similarity, higher is closer


class VectorStore(Protocol):
    def upsert(
        self, chunks: list[Chunk], vectors: list[list[float]], digests: list[str]
    ) -> None: ...

    def digests(self) -> dict[str, str]:
        """chunk id -> digest of every stored chunk."""
        ...

    def remove(self, ids: list[str]) -> None:
        """Drop stale chunks from the index (vector index only; no business data)."""
        ...

    def query(self, vector: list[float], k: int) -> list[Hit]: ...


def _meta(c: Chunk, digest: str) -> dict[str, str]:
    return {"sheet_id": c.sheet_id, "title": c.title, "section": c.section, "digest": digest}


class MemoryStore:
    def __init__(self) -> None:
        self.rows: dict[str, tuple[Chunk, list[float], str]] = {}

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]], digests: list[str]) -> None:
        for chunk, vector, digest in zip(chunks, vectors, digests, strict=True):
            self.rows[chunk.id] = (chunk, vector, digest)

    def digests(self) -> dict[str, str]:
        return {i: row[2] for i, row in self.rows.items()}

    def remove(self, ids: list[str]) -> None:
        for i in ids:
            self.rows.pop(i, None)

    def query(self, vector: list[float], k: int) -> list[Hit]:
        def cos(a: list[float], b: list[float]) -> float:
            na = math.sqrt(sum(x * x for x in a)) or 1.0
            nb = math.sqrt(sum(x * x for x in b)) or 1.0
            return sum(x * y for x, y in zip(a, b, strict=True)) / (na * nb)

        scored = sorted(self.rows.values(), key=lambda r: cos(vector, r[1]), reverse=True)
        return [
            Hit(c.sheet_id, c.title, c.section, c.text, round(cos(vector, v), 4))
            for c, v, _ in scored[:k]
        ]


class ChromaHttpStore:
    def __init__(
        self,
        base_url: str,
        collection: str,
        tenant: str = "default_tenant",
        database: str = "default_database",
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.http = httpx.Client(base_url=base_url.rstrip("/"), timeout=30, transport=transport)
        self.prefix = f"/api/v2/tenants/{tenant}/databases/{database}/collections"
        created = self.http.post(
            self.prefix,
            json={
                "name": collection,
                "get_or_create": True,
                "configuration": {"hnsw": {"space": "cosine"}},
            },
        )
        created.raise_for_status()
        self.cid = created.json()["id"]

    def _post(self, action: str, body: dict[str, Any]) -> Any:
        r = self.http.post(f"{self.prefix}/{self.cid}/{action}", json=body)
        r.raise_for_status()
        return r.json() if r.content else None

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]], digests: list[str]) -> None:
        if not chunks:
            return
        self._post(
            "upsert",
            {
                "ids": [c.id for c in chunks],
                "embeddings": vectors,
                "documents": [c.text for c in chunks],
                "metadatas": [_meta(c, d) for c, d in zip(chunks, digests, strict=True)],
            },
        )

    def digests(self) -> dict[str, str]:
        got = self._post("get", {"include": ["metadatas"]})
        return {
            i: str((m or {}).get("digest", ""))
            for i, m in zip(got["ids"], got["metadatas"], strict=True)
        }

    def remove(self, ids: list[str]) -> None:
        if ids:
            self._post("delete", {"ids": ids})

    def query(self, vector: list[float], k: int) -> list[Hit]:
        result = self._post(
            "query",
            {
                "query_embeddings": [vector],
                "n_results": k,
                "include": ["documents", "metadatas", "distances"],
            },
        )
        hits = []
        for doc, meta, dist in zip(
            result["documents"][0], result["metadatas"][0], result["distances"][0], strict=True
        ):
            hits.append(
                Hit(meta["sheet_id"], meta["title"], meta["section"], doc, round(1 - dist, 4))
            )
        return hits
