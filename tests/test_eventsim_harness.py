from fastapi.testclient import TestClient

from eventsim.main import create_app
from tests.conftest import HARNESS, auth, make_settings


def test_test_endpoints_refuse_user_tokens(client: TestClient) -> None:
    for path in ("/_test/snapshot", "/_test/reset"):
        assert client.post(path, json={"seed": 1}).status_code == 403
        assert client.post(path, json={"seed": 1}, headers=auth("admin")).status_code == 403
        # An admin token passed in the harness header is still the wrong secret.
        assert (
            client.post(path, json={"seed": 1}, headers={"X-Test-Token": "t-admin"}).status_code
            == 403
        )
    assert client.get("/_test/state-diff", headers=auth("admin")).status_code == 403


def test_test_endpoints_can_be_disabled() -> None:
    with TestClient(create_app(make_settings(test_endpoints=False))) as c:
        assert c.post("/_test/snapshot", headers=HARNESS).status_code == 404


def test_test_endpoints_hidden_from_openapi(client: TestClient) -> None:
    assert not [p for p in client.get("/openapi.json").json()["paths"] if p.startswith("/_test")]


def test_reset_snapshot_diff_cycle(client: TestClient) -> None:
    assert client.get("/_test/state-diff", headers=HARNESS).status_code == 409
    assert client.post("/_test/reset", json={"seed": 7}, headers=HARNESS).json()["seed"] == 7
    snap = client.post("/_test/snapshot", headers=HARNESS).json()
    assert snap["counts"]["events"] == 22

    diff = client.get("/_test/state-diff", headers=HARNESS).json()
    assert diff["empty"] is True and diff["seed"] == 7

    client.post("/events/1/archive", headers=auth("editor"))
    client.post(
        "/notifications",
        headers=auth("editor"),
        json={"to": "x@example.org", "subject": "s", "body": "b"},
    )
    diff = client.get("/_test/state-diff", headers=HARNESS).json()
    assert diff["empty"] is False
    changed = diff["tables"]["events"]["changed"]
    assert [c["key"] for c in changed] == ["1"]
    assert {"archived", "archived_at", "updated_at"} <= set(changed[0]["fields"])
    assert changed[0]["after"]["archived"] is True
    assert len(diff["tables"]["outbox"]["added"]) == 1
    assert all(not t["removed"] for t in diff["tables"].values())
    assert len(client.get("/_test/outbox", headers=HARNESS).json()) == 1

    # Reset restores the seeded state and drops the snapshot.
    client.post("/_test/reset", json={"seed": 7}, headers=HARNESS)
    assert client.get("/_test/state-diff", headers=HARNESS).status_code == 409
    assert client.get("/events/1", headers=auth("reader")).json()["archived"] is False


def test_reset_keeps_tokens_working(client: TestClient) -> None:
    client.post("/_test/reset", json={"seed": 3}, headers=HARNESS)
    assert client.get("/me", headers=auth("editor")).json()["role"] == "editor"


def test_export_and_canaries(client: TestClient) -> None:
    export = client.get("/_test/export", headers=HARNESS).json()
    assert set(export) >= {"editions", "events", "session_speaker", "outbox"}
    canaries = client.get("/_test/canaries", headers=HARNESS).json()
    assert len(canaries) == 6
    notes = [a["notes"] for a in export["attendees"].values()]
    assert sum(any(c["value"] in n for c in canaries) for n in notes) == 3
