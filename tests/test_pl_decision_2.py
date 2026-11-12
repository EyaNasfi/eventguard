"""PL decision #2 (recorded 2026-11-12): one test per rule, so the decision is checked
against EventSim's behaviour rather than read off the code. The full route x role
matrix stays in test_eventsim_api.py::test_role_matrix."""

from typing import Any

from fastapi.testclient import TestClient

from tests.conftest import HARNESS, auth


def edition_id(client: TestClient, year: int) -> int:
    [row] = client.get("/editions", params={"year": year}, headers=auth("admin")).json()
    return int(row["id"])


def first_event(client: TestClient, year: int, **filters: Any) -> dict[str, Any]:
    params = {"year": year, "archived": False, **filters}
    rows: list[dict[str, Any]] = client.get("/events", params=params, headers=auth("admin")).json()
    return rows[0]


def new_draft_event(client: TestClient) -> int:
    body = {
        "edition_id": edition_id(client, 2027),
        "type": "club",
        "name": "PL2 Draft Club",
        "start_at": "2027-06-10T18:30:00",
        "end_at": "2027-06-10T20:30:00",
        "venue": "Espace Calvane",
    }
    created = client.post("/events", json=body, headers=auth("editor"))
    assert created.status_code == 201, created.text
    return int(created.json()["id"])


def new_session(client: TestClient, event_id: int, role: str = "editor") -> int:
    body = {
        "event_id": event_id,
        "title": "PL2 session",
        "start_at": "2027-06-10T18:30:00",
        "end_at": "2027-06-10T19:00:00",
    }
    created = client.post("/sessions", json=body, headers=auth(role))
    assert created.status_code == 201, created.text
    return int(created.json()["id"])


# Attendees: every attendee route, read and write, is admin-only.
def test_attendee_routes_admin_only(client: TestClient) -> None:
    event = first_event(client, 2026)
    body = {"event_id": event["id"], "first_name": "Ana", "last_name": "Test", "email": "a@x.test"}
    for role in ("reader", "editor"):
        assert client.get("/attendees", headers=auth(role)).status_code == 403
        assert client.get("/attendees/1", headers=auth(role)).status_code == 403
        assert client.post("/attendees", json=body, headers=auth(role)).status_code == 403
        patch = client.patch("/attendees/1", json={"company": "X"}, headers=auth(role))
        assert patch.status_code == 403
        assert client.post("/attendees/1/archive", headers=auth(role)).status_code == 403
    assert client.get("/attendees", headers=auth("admin")).status_code == 200
    assert client.post("/attendees", json=body, headers=auth("admin")).status_code == 201


# Speakers and partners are global: editor creates and updates them.
def test_editor_creates_and_updates_speakers_and_partners(client: TestClient) -> None:
    speaker = {"first_name": "Lio", "last_name": "Test", "email": "l@x.test"}
    created = client.post("/speakers", json=speaker, headers=auth("editor"))
    assert created.status_code == 201
    sid = created.json()["id"]
    assert client.patch(
        f"/speakers/{sid}", json={"company": "Y"}, headers=auth("editor")
    ).is_success
    partner = client.post("/partners", json={"name": "PL2 Partner"}, headers=auth("editor"))
    assert partner.status_code == 201
    pid = partner.json()["id"]
    assert client.patch(
        f"/partners/{pid}", json={"tier": "gold"}, headers=auth("editor")
    ).is_success
    assert client.post("/speakers", json=speaker, headers=auth("reader")).status_code == 403


# Links only when the session or event belongs to a draft edition (editor).
def test_editor_links_only_in_draft_edition(client: TestClient) -> None:
    active_event = first_event(client, 2026)
    active_session = client.get(
        "/sessions", params={"event_id": active_event["id"]}, headers=auth("editor")
    ).json()[0]
    s = client.post(
        f"/sessions/{active_session['id']}/speakers", json={"speaker_id": 1}, headers=auth("editor")
    )
    assert s.status_code == 403
    p = client.post(
        f"/events/{active_event['id']}/partners", json={"partner_id": 1}, headers=auth("editor")
    )
    assert p.status_code == 403

    draft_event = new_draft_event(client)
    draft_session = new_session(client, draft_event)
    s = client.post(
        f"/sessions/{draft_session}/speakers", json={"speaker_id": 1}, headers=auth("editor")
    )
    assert s.status_code == 201
    p = client.post(
        f"/events/{draft_event}/partners", json={"partner_id": 1}, headers=auth("editor")
    )
    assert p.status_code == 201


# Editor PATCHes only draft-edition records, plus speakers and partners.
def test_editor_patch_scope(client: TestClient) -> None:
    active_event = first_event(client, 2026)
    r = client.patch(f"/events/{active_event['id']}", json={"venue": "X"}, headers=auth("editor"))
    assert r.status_code == 403
    draft_event = new_draft_event(client)
    r = client.patch(f"/events/{draft_event}", json={"venue": "Salle B"}, headers=auth("editor"))
    assert r.is_success
    draft_session = new_session(client, draft_event)
    r = client.patch(f"/sessions/{draft_session}", json={"room": "B2"}, headers=auth("editor"))
    assert r.is_success
    eid = edition_id(client, 2027)
    assert (
        client.patch(f"/editions/{eid}", json={"name": "Z"}, headers=auth("editor")).status_code
        == 403
    )


# Editor archives / unarchives single events in any edition; never an edition,
# a session or an attendee. Admin can do everything.
def test_editor_archive_scope(client: TestClient) -> None:
    event = first_event(client, 2026)
    assert client.post(f"/events/{event['id']}/archive", headers=auth("editor")).is_success
    assert client.post(f"/events/{event['id']}/unarchive", headers=auth("editor")).is_success
    eid = edition_id(client, 2025)
    assert client.post(f"/editions/{eid}/archive", headers=auth("editor")).status_code == 403
    assert client.post("/sessions/1/archive", headers=auth("editor")).status_code == 403
    assert client.post("/attendees/1/archive", headers=auth("editor")).status_code == 403
    assert client.post("/sessions/1/archive", headers=auth("admin")).is_success
    assert client.post(f"/editions/{eid}/archive", headers=auth("admin")).is_success


# Unarchive restores the exact previous status (draft stays draft).
def test_unarchive_restores_exact_status(client: TestClient) -> None:
    draft_event = new_draft_event(client)
    client.post(f"/events/{draft_event}/archive", headers=auth("editor"))
    archived = client.get(f"/events/{draft_event}", headers=auth("editor")).json()
    assert archived["status"] == "archived" and archived["previous_status"] == "draft"
    client.post(f"/events/{draft_event}/unarchive", headers=auth("editor"))
    restored = client.get(f"/events/{draft_event}", headers=auth("editor")).json()
    assert restored["status"] == "draft" and restored["archived"] is False


# Sessions, speakers, partners and attendees keep an archived flag, no status.
def test_flag_only_entities(client: TestClient) -> None:
    for path in ("/sessions/1", "/speakers/1", "/partners/1", "/attendees/1"):
        row = client.get(path, headers=auth("admin")).json()
        assert "archived" in row and "status" not in row


# Seed: 2025 active, 2026 active, 2027 draft, the cancelled 2026 evening archived;
# the same seed gives the same database.
def test_seed_statuses_and_determinism(client: TestClient) -> None:
    eds = {e["year"]: e["status"] for e in client.get("/editions", headers=auth("admin")).json()}
    assert eds == {2025: "active", 2026: "active", 2027: "draft"}
    archived = client.get(
        "/events", params={"year": 2026, "archived": True}, headers=auth("admin")
    ).json()
    assert [(e["type"], e["previous_status"]) for e in archived] == [("evening", "active")]
    first = client.get("/_test/export", headers=HARNESS).json()
    client.post("/_test/reset", json={"seed": 42}, headers=HARNESS)
    assert client.get("/_test/export", headers=HARNESS).json() == first
