"""S2-03: procedure sheets, ingestion and the retriever service, offline (no Gemini)."""

from dataclasses import replace
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from google.genai import errors

from agent.rag.embed import GeminiEmbedder, HashingEmbedder, document_text, query_text
from agent.rag.ingest import ingest
from agent.rag.service import build_app
from agent.rag.sheets import SECTIONS, chunks, load_sheets, parse_sheet
from agent.rag.store import ChromaHttpStore, MemoryStore

TOPICS = {
    "PROC-01": "edition",
    "PROC-02": "conference",
    "PROC-03": "club",
    "PROC-04": "evening",
    "PROC-05": "dates",
    "PROC-06": "speakers",
    "PROC-07": "partners",
    "PROC-08": "session",
    "PROC-09": "single event",
    "PROC-10": "whole edition",
    "PROC-11": "unarchive",
    "PROC-12": "pre-archiving",
    "PROC-13": "rollover",
    "PROC-14": "roles",
    "PROC-15": "notify",
    "PROC-16": "duplicate speaker",
    "PROC-17": "naming",
    "PROC-18": "escalation",
}


def test_eighteen_sheets_with_valid_front_matter_and_sections() -> None:
    sheets = load_sheets()
    assert [s.meta.id for s in sheets] == sorted(TOPICS)
    for sheet in sheets:
        assert tuple(sheet.sections) == SECTIONS, sheet.meta.id
        assert 200 <= sheet.words <= 400, (sheet.meta.id, sheet.words)
        assert set(sheet.meta.roles) <= {"reader", "editor", "admin"}
        assert TOPICS[sheet.meta.id].lower() in sheet.meta.title.lower(), sheet.meta.id


def test_archive_edition_sheet_states_no_cascade() -> None:
    sheet = next(s for s in load_sheets() if s.meta.id == "PROC-10")
    assert "no cascade" in sheet.sections["Purpose"].lower()


def test_sheets_never_mention_delete_as_an_action() -> None:
    for sheet in load_sheets():
        steps = sheet.sections["Steps"].lower()
        assert "delete_" not in steps and "call delete" not in steps


def test_bad_front_matter_is_rejected() -> None:
    with pytest.raises(ValueError):
        parse_sheet("# no front matter")


def test_chunk_ids_are_stable_and_unique() -> None:
    ids = [c.id for c in chunks(load_sheets())]
    assert len(ids) == len(set(ids)) == 18 * len(SECTIONS)
    assert "PROC-03#steps" in ids


def test_ingestion_is_idempotent() -> None:
    store, embedder = MemoryStore(), HashingEmbedder()
    first = ingest(load_sheets(), store, embedder)
    snapshot = dict(store.rows)
    second = ingest(load_sheets(), store, embedder)
    assert first.chunks == second.chunks == len(store.rows) == 90
    assert first.embedded == 90 and first.embed_calls == 1
    assert store.rows == snapshot
    assert second.embedded == 0 and second.embed_calls == 0 and second.removed == 0


def test_ingestion_re_embeds_only_changed_chunks() -> None:
    store, embedder = MemoryStore(), HashingEmbedder()
    sheets = load_sheets()
    ingest(sheets, store, embedder)
    first = sheets[0]
    edited = replace(first, sections={**first.sections, "Purpose": "Changed purpose text."})
    report = ingest([edited, *sheets[1:]], store, embedder)
    assert report.embedded == 1 and report.removed == 0


def test_new_embedding_model_re_embeds_everything() -> None:
    store = MemoryStore()
    ingest(load_sheets(), store, HashingEmbedder(256))
    assert ingest(load_sheets(), store, HashingEmbedder(128)).embedded == 90


def test_ingestion_removes_stale_chunks() -> None:
    store, embedder = MemoryStore(), HashingEmbedder()
    ingest(load_sheets(), store, embedder)
    report = ingest(load_sheets()[:17], store, embedder)
    assert report.removed == len(SECTIONS)
    assert not any(i.startswith("PROC-18") for i in store.digests())


@pytest.mark.parametrize(
    ("query", "sheet"),
    [
        ("duplicate a club", "PROC-03"),
        ("how do I archive a whole edition", "PROC-10"),
        ("escalation when the platform refuses", "PROC-18"),
    ],
)
def test_retrieval_finds_the_right_sheet(query: str, sheet: str) -> None:
    store, embedder = MemoryStore(), HashingEmbedder()
    ingest(load_sheets(), store, embedder)
    hits = store.query(embedder.embed_query(query), 4)
    assert sheet in [h.sheet_id for h in hits]


def test_retriever_service_marks_hits_as_procedure_sheets() -> None:
    store, embedder = MemoryStore(), HashingEmbedder()
    ingest(load_sheets(), store, embedder)
    client = TestClient(build_app(lambda: store, embedder))
    assert client.get("/health").json()["status"] == "ok"
    hits = client.post("/search", json={"query": "duplicate a club", "k": 3}).json()["hits"]
    assert len(hits) == 3 and hits[0]["sheet_id"] == "PROC-03"
    assert {h["source"] for h in hits} == {"procedure_sheet"}
    assert client.post("/search", json={"query": ""}).status_code == 422


def test_gemini_prefixes_follow_the_docs() -> None:
    assert document_text("T", "body") == "title: T | text: body"
    assert document_text("", "body") == "title: none | text: body"
    assert query_text("q") == "task: search result | query: q"


def test_gemini_embedder_retries_on_429_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    slept: list[float] = []
    embedder = GeminiEmbedder("fake-key", "gemini-embedding-2", 8, sleep=slept.append)
    attempts = {"n": 0}

    class Embedding:
        values = [0.1] * 8

    class Result:
        def __init__(self, n: int) -> None:
            self.embeddings = [Embedding() for _ in range(n)]

    def fake_embed(model: str, contents: list[Any], config: Any) -> Result:
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise errors.ClientError(429, {"error": {"message": "quota", "status": "RESOURCE"}})
        return Result(len(contents))

    monkeypatch.setattr(embedder.client.models, "embed_content", fake_embed)
    assert len(embedder.embed_documents([("a", "b"), ("c", "d")])) == 2
    assert slept == [2.0, 4.0] and embedder.calls == 3


def test_gemini_embedder_waits_for_the_api_retry_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    slept: list[float] = []
    embedder = GeminiEmbedder("fake-key", "gemini-embedding-2", 8, sleep=slept.append)
    attempts = {"n": 0}
    body = {
        "error": {
            "message": "quota",
            "status": "RESOURCE_EXHAUSTED",
            "details": [{"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "49s"}],
        }
    }

    class Embedding:
        values = [0.1] * 8

    class Result:
        embeddings = [Embedding()]

    def fake_embed(model: str, contents: list[Any], config: Any) -> Result:
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise errors.ClientError(429, body)
        return Result()

    monkeypatch.setattr(embedder.client.models, "embed_content", fake_embed)
    embedder.embed_query("x")
    assert slept == [50.0]


def test_gemini_embedder_paces_texts_per_minute(monkeypatch: pytest.MonkeyPatch) -> None:
    now = {"t": 0.0}
    slept: list[float] = []

    def sleep(seconds: float) -> None:
        slept.append(seconds)
        now["t"] += seconds

    embedder = GeminiEmbedder(
        "fake-key", "m", 8, texts_per_minute=50, sleep=sleep, clock=lambda: now["t"]
    )

    class Embedding:
        values = [0.1] * 8

    def fake_embed(model: str, contents: list[Any], config: Any) -> Any:
        return type("R", (), {"embeddings": [Embedding() for _ in contents]})()

    monkeypatch.setattr(embedder.client.models, "embed_content", fake_embed)
    embedder.embed_documents([("t", str(i)) for i in range(80)])  # batches of 40
    assert embedder.calls == 2 and len(slept) == 1 and slept[0] == pytest.approx(60.5)


def test_gemini_embedder_does_not_retry_other_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    embedder = GeminiEmbedder("fake-key", "gemini-embedding-2", 8, sleep=lambda _: None)

    def fake_embed(model: str, contents: list[Any], config: Any) -> Any:
        raise errors.ClientError(400, {"error": {"message": "bad", "status": "INVALID"}})

    monkeypatch.setattr(embedder.client.models, "embed_content", fake_embed)
    with pytest.raises(errors.ClientError):
        embedder.embed_query("x")
    assert embedder.calls == 1


def test_chroma_http_store_speaks_the_v2_api() -> None:
    seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path))
        path = request.url.path
        if path.endswith("/collections"):
            return httpx.Response(200, json={"id": "c1"})
        if path.endswith("/query"):
            return httpx.Response(
                200,
                json={
                    "documents": [["text"]],
                    "metadatas": [[{"sheet_id": "PROC-03", "title": "T", "section": "Steps"}]],
                    "distances": [[0.25]],
                },
            )
        if path.endswith("/get"):
            return httpx.Response(
                200, json={"ids": ["PROC-03#steps"], "metadatas": [{"digest": "d1"}]}
            )
        return httpx.Response(200, json={})

    store = ChromaHttpStore(
        "http://vs:8000", "procedures_v1", transport=httpx.MockTransport(handler)
    )
    [part] = [c for c in chunks(load_sheets()) if c.id == "PROC-03#steps"]
    store.upsert([], [], [])
    store.upsert([part], [[0.0, 1.0]], ["d1"])
    assert store.digests() == {"PROC-03#steps": "d1"}
    store.remove([])
    store.remove(["x"])
    [hit] = store.query([0.0, 1.0], 1)
    assert hit.sheet_id == "PROC-03" and hit.score == 0.75
    prefix = "/api/v2/tenants/default_tenant/databases/default_database/collections"
    assert ("POST", f"{prefix}/c1/upsert") in seen
    assert ("POST", f"{prefix}/c1/delete") in seen
