"""The retriever service (S2-03): embeds a query and searches the vector store.

Runs as the `retriever` container: internal network (gateway, vector store) + egress (Gemini).
It holds the Gemini key so that the gateway needs neither the key nor internet access.

    POST /search {"query": "...", "k": 4} -> {"hits": [{sheet_id, title, section, text,
                                                         source: "procedure_sheet", score}]}
"""

import os
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from agent.rag.embed import Embedder, GeminiEmbedder
from agent.rag.store import ChromaHttpStore, VectorStore
from config.loader import read_file


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    k: int = Field(default=4, ge=1, le=10)


def build_app(store_factory: Any, embedder: Embedder) -> FastAPI:
    app = FastAPI(title="EventGuard retriever", docs_url=None, redoc_url=None)
    state: dict[str, VectorStore] = {}

    def store() -> VectorStore:
        if "store" not in state:  # lazy: the vector store may start after us
            state["store"] = store_factory()
        return state["store"]

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "embed_calls": embedder.calls}

    @app.post("/search")
    def search(body: SearchRequest) -> dict[str, Any]:
        hits = store().query(embedder.embed_query(body.query), body.k)
        return {
            "hits": [
                {
                    "sheet_id": h.sheet_id,
                    "title": h.title,
                    "section": h.section,
                    "text": h.text,
                    "source": "procedure_sheet",
                    "score": h.score,
                }
                for h in hits
            ]
        }

    return app


def create_app() -> FastAPI:
    """uvicorn --factory agent.rag.service:create_app"""
    retrieval = read_file().retrieval
    embedder = GeminiEmbedder(
        os.environ["GEMINI_API_KEY"], retrieval.embedding_model, retrieval.dimensions
    )
    url = os.environ.get("CHROMA_URL", "http://vectorstore:8000")
    return build_app(lambda: ChromaHttpStore(url, retrieval.collection), embedder)
