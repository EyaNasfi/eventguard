"""Ingest the procedure sheets into the vector store (S2-03).

Idempotent and cheap to re-run: chunk ids are stable (`PROC-03#steps`); each stored chunk
keeps a digest of its text and of the embedding model, so only new or changed chunks are
embedded; chunks whose sheet or section no longer exists are removed from the index. A second
run on unchanged sheets makes no Gemini call.

Inside the lab (the retriever container has the Gemini key and reaches the vector store):
    docker compose exec retriever python -m agent.rag.ingest
"""

import argparse
import hashlib
import os
import sys
from dataclasses import dataclass

from agent.rag.embed import Embedder, GeminiEmbedder
from agent.rag.sheets import Chunk, Sheet, chunks, load_sheets
from agent.rag.store import ChromaHttpStore, VectorStore
from config.loader import read_file


@dataclass(frozen=True)
class IngestReport:
    sheets: int
    chunks: int
    embedded: int
    removed: int
    embed_calls: int


def digest(chunk: Chunk, fingerprint: str) -> str:
    raw = "\n".join((fingerprint, chunk.title, chunk.section, chunk.text))
    return hashlib.sha256(raw.encode()).hexdigest()


def ingest(sheets: list[Sheet], store: VectorStore, embedder: Embedder) -> IngestReport:
    parts = chunks(sheets)
    stored = store.digests()
    wanted = {c.id: digest(c, embedder.fingerprint) for c in parts}
    changed = [c for c in parts if stored.get(c.id) != wanted[c.id]]
    before = embedder.calls
    if changed:
        vectors = embedder.embed_documents([(c.title, c.text) for c in changed])
        store.upsert(changed, vectors, [wanted[c.id] for c in changed])
    stale = sorted(set(stored) - set(wanted))
    store.remove(stale)
    return IngestReport(len(sheets), len(parts), len(changed), len(stale), embedder.calls - before)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--chroma-url", default=os.environ.get("CHROMA_URL", "http://vectorstore:8000")
    )
    args = parser.parse_args(argv)
    retrieval = read_file().retrieval
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise SystemExit("GEMINI_API_KEY is not set")
    embedder = GeminiEmbedder(key, retrieval.embedding_model, retrieval.dimensions)
    store = ChromaHttpStore(args.chroma_url, retrieval.collection)
    report = ingest(load_sheets(), store, embedder)
    print(
        f"{report.sheets} sheets, {report.chunks} chunks in '{retrieval.collection}' "
        f"({retrieval.embedding_model}, {retrieval.dimensions} dims): embedded {report.embedded}, "
        f"removed {report.removed} stale; Gemini embedding calls: {report.embed_calls}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
