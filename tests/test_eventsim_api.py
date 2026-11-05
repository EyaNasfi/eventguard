from typing import Any

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from eventsim.main import create_app
from tests.conftest import HARNESS, as_role, auth, make_settings

# Seed 42 layout: editions 1=2025 (active), 2=2026 (active), 3=2027 (draft, empty);
# events 1-11 in 2025, 12-22 in 2026, event 22 is the archived evening.
ACTIVE_EDITION, DRAFT_EDITION, ACTIVE_EVENT, ARCHIVED_EVENT = 2, 3, 12, 22


def event_body(edition_id: int) -> dict[str, Any]:
    return {
        "edition_id": edition_id,
        "type": "club",
        "name": "Test Club",
        "start_at": "2027-05-01T18:30:00",
        "end_at": "2027-05-01T20:30:00",
        "venue": "Espace Calvane",
    }


def session_body(event_id: int) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "title": "Opening",
        "start_at": "2027-05-01T18:30:00",
        "end_at": "2027-05-01T19:00:00",
    }


def prepare(client: TestClient) -> dict[str, int]:
    """Fresh seed 42 plus, created by admin: a draft-edition event and session,
    an unlinked speaker and partner. Returns the ids used by the matrix."""
    client.post("/_test/reset", json={"seed": 42}, headers=HARNESS)
    admin = auth("admin")
    draft_event = client.post("/events", json=event_body(DRAFT_EDITION), headers=admin).json()
    draft_session = client.post("/sessions", json=session_body(draft_event["id"]), headers=admin)
    active_session = client.get("/sessions", params={"event_id": ACTIVE_EVENT}, headers=admin)
    speaker = client.post(
        "/speakers",
        json={"first_name": "Ana", "last_name": "Test", "email": "ana@example.com"},
        headers=admin,
    )
    partner = client.post("/partners", json={"name": "Testco"}, headers=admin)
    return {
        "draft_event": draft_event["id"],
        "draft_session": draft_session.json()["id"],
        "active_session": active_session.json()[0]["id"],
        "speaker": speaker.json()["id"],
        "partner": partner.json()["id"],
    }


R, E, A = "reader", "editor", "admin"
NEW_EDITION = {"year": 2030, "name": "R 2030", "start_date": "2030-01-15", "end_date": "2030-12-15"}
NOTE = {"to": "team@example.org", "subject": "Hi", "body": "Hello"}
ATTENDEE = {"first_name": "Bo", "last_name": "Test", "email": "bo@example.org"}

# (method, path, body, expected status for reader / editor / admin)
MATRIX: list[tuple[str, str, Any, tuple[int, int, int]]] = [
    # reads
    ("GET", "/editions", None, (200, 200, 200)),
    ("GET", "/editions/2", None, (200, 200, 200)),
    ("GET", "/events", None, (200, 200, 200)),
    ("GET", "/events/12", None, (200, 200, 200)),
    ("GET", "/sessions", None, (200, 200, 200)),
    ("GET", "/sessions/{active_session}", None, (200, 200, 200)),
    ("GET", "/speakers", None, (200, 200, 200)),
    ("GET", "/speakers/1", None, (200, 200, 200)),
    ("GET", "/partners", None, (200, 200, 200)),
    ("GET", "/partners/1", None, (200, 200, 200)),
    ("GET", "/search?q=club", None, (200, 200, 200)),
    ("GET", "/attendees", None, (403, 403, 200)),
    ("GET", "/attendees/1", None, (403, 403, 200)),
    ("GET", "/config", None, (403, 403, 200)),
    ("GET", "/outbox", None, (403, 403, 200)),
    # creates
    ("POST", "/editions", NEW_EDITION, (403, 403, 201)),
    ("POST", "/events", event_body(ACTIVE_EDITION), (403, 403, 201)),
    ("POST", "/events", event_body(DRAFT_EDITION), (403, 201, 201)),
    ("POST", "/sessions", session_body(ACTIVE_EVENT), (403, 403, 201)),
    ("POST", "/sessions", "draft_session_body", (403, 201, 201)),
    (
        "POST",
        "/speakers",
        {"first_name": "C", "last_name": "D", "email": "c@example.com"},
        (403, 201, 201),
    ),
    ("POST", "/partners", {"name": "Otherco"}, (403, 201, 201)),
    ("POST", "/attendees", ATTENDEE | {"event_id": ACTIVE_EVENT}, (403, 403, 201)),
    ("POST", "/sessions/{active_session}/speakers", "speaker_link", (403, 403, 201)),
    ("POST", "/sessions/{draft_session}/speakers", "speaker_link", (403, 201, 201)),
    ("POST", "/events/12/partners", "partner_link", (403, 403, 201)),
    ("POST", "/events/{draft_event}/partners", "partner_link", (403, 201, 201)),
    # updates
    ("PATCH", "/editions/3", {"name": "Renamed"}, (403, 403, 200)),
    ("PATCH", "/events/12", {"venue": "Halle Brumaire"}, (403, 403, 200)),
    ("PATCH", "/events/{draft_event}", {"venue": "Halle Brumaire"}, (403, 200, 200)),
    ("PATCH", "/sessions/{active_session}", {"room": "Room Z"}, (403, 403, 200)),
    ("PATCH", "/sessions/{draft_session}", {"room": "Room Z"}, (403, 200, 200)),
    ("PATCH", "/speakers/1", {"company": "Nordalis"}, (403, 200, 200)),
    ("PATCH", "/partners/1", {"tier": "gold"}, (403, 200, 200)),
    ("PATCH", "/attendees/1", {"company": "Nordalis"}, (403, 403, 200)),
    # archive / unarchive
    ("POST", "/events/12/archive", None, (403, 200, 200)),
    ("POST", "/events/22/unarchive", None, (403, 200, 200)),
    ("POST", "/editions/1/archive", None, (403, 403, 200)),
    ("POST", "/sessions/{active_session}/archive", None, (403, 403, 200)),
    ("POST", "/speakers/1/archive", None, (403, 403, 200)),
    ("POST", "/partners/1/archive", None, (403, 403, 200)),
    ("POST", "/attendees/1/archive", None, (403, 403, 200)),
    # other
    ("POST", "/notifications", NOTE, (403, 201, 201)),
    ("DELETE", "/events/12", None, (405, 405, 405)),
]


@pytest.mark.parametrize(("method", "path", "body", "expected"), MATRIX)
def test_role_matrix(
    client: TestClient, method: str, path: str, body: Any, expected: tuple[int, int, int]
) -> None:
    for role, code in zip((R, E, A), expected, strict=True):
        ids = prepare(client)
        payload = (
            {
                "speaker_link": {"speaker_id": ids["speaker"]},
                "partner_link": {"partner_id": ids["partner"]},
                "draft_session_body": session_body(ids["draft_event"]),
            }.get(body, body)
            if isinstance(body, str)
            else body
        )
        response = client.request(method, path.format(**ids), json=payload, headers=auth(role))
        assert response.status_code == code, (role, method, path, response.text)


# ---------------------------------------------------------------- auth


def test_health_needs_no_token(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_missing_and_wrong_token_are_401(client: TestClient) -> None:
    assert client.get("/events").status_code == 401
    assert client.get("/events", headers={"Authorization": "Bearer nope"}).status_code == 401
    assert client.get("/events", headers={"Authorization": "Basic x"}).status_code == 401


def test_me_reports_role(client: TestClient) -> None:
    for role in (R, E, A):
        assert client.get("/me", headers=auth(role)).json()["role"] == role


def test_refusals_explain_themselves(client: TestClient) -> None:
    refused = client.post("/events", json=event_body(ACTIVE_EDITION), headers=auth(E))
    assert refused.json()["detail"] == (
        "role 'editor' can only create events in a draft edition (edition 2026 is active)"
    )
    refused = client.get("/attendees", headers=auth(R))
    assert refused.json()["detail"] == "role 'reader' cannot read attendees"


# ---------------------------------------------------------------- reads


def test_list_events_filters(client: TestClient) -> None:
    c = as_role(client, R)
    all_2026 = c.get("/events", params={"year": 2026}).json()
    assert len(all_2026) == 11
    clubs = c.get("/events", params={"year": 2026, "type": "club"}).json()
    assert len(clubs) == 4 and all(e["type"] == "club" for e in clubs)
    assert c.get("/events", params={"edition_id": ACTIVE_EDITION}).json() == all_2026
    archived = c.get("/events", params={"archived": True}).json()
    assert [e["id"] for e in archived] == [ARCHIVED_EVENT]
    assert archived[0]["status"] == "archived" and archived[0]["previous_status"] == "active"
    assert c.get("/events", params={"status": "archived"}).json() == archived
    assert len(c.get("/events", params={"status": "active"}).json()) == 21
    assert [e["status"] for e in c.get("/editions").json()] == ["active", "active", "draft"]
    assert c.get("/editions", params={"status": "draft"}).json()[0]["year"] == 2027


def test_internal_notes_hidden_from_reader_only(client: TestClient) -> None:
    for path in ("/events/12", "/events?year=2026"):
        reader = client.get(path, headers=auth(R)).json()
        editor = client.get(path, headers=auth(E)).json()
        for row in reader if isinstance(reader, list) else [reader]:
            assert "internal_notes" not in row
        for row in editor if isinstance(editor, list) else [editor]:
            assert "internal_notes" in row


def test_detail_routes_expose_links(client: TestClient) -> None:
    c = as_role(client, R)
    detail = c.get(f"/events/{ACTIVE_EVENT}").json()
    assert detail["session_ids"]
    session = c.get(f"/sessions/{detail['session_ids'][0]}").json()
    assert session["speaker_ids"]
    speaker = c.get(f"/speakers/{session['speaker_ids'][0]}").json()
    assert session["id"] in speaker["session_ids"]
    by_speaker = c.get("/sessions", params={"speaker_id": speaker["id"]}).json()
    assert {s["id"] for s in by_speaker} == set(speaker["session_ids"])
    assert ACTIVE_EVENT in c.get(f"/editions/{ACTIVE_EDITION}").json()["event_ids"]


def test_partners_and_attendees(client: TestClient) -> None:
    c = as_role(client, A)
    partners = c.get("/partners").json()
    assert len(partners) == 12
    linked = next(p for p in partners if c.get(f"/partners/{p['id']}").json()["event_ids"])
    event_id = c.get(f"/partners/{linked['id']}").json()["event_ids"][0]
    by_event = c.get("/partners", params={"event_id": event_id}).json()
    assert linked["id"] in [p["id"] for p in by_event]
    assert c.get("/partners", params={"q": linked["name"][:4]}).json()
    assert c.get("/partners", params={"tier": linked["tier"]}).json()
    attendees = c.get("/attendees", params={"event_id": event_id}).json()
    assert attendees and c.get(f"/attendees/{attendees[0]['id']}").json() == attendees[0]
    assert c.get("/attendees", params={"q": attendees[0]["last_name"]}).json()
    assert c.get("/speakers", params={"q": "example.com"}).json()


def test_search_spans_entities_attendees_admin_only(client: TestClient) -> None:
    hits = client.get("/search", params={"q": "club"}, headers=auth(R)).json()
    assert hits and {h["entity"] for h in hits} >= {"events"}
    first = client.get("/attendees/1", headers=auth(A)).json()["last_name"]
    entities = {
        role: {
            h["entity"]
            for h in client.get(
                "/search", params={"q": first, "limit": 100}, headers=auth(role)
            ).json()
        }
        for role in (R, E, A)
    }
    assert "attendees" in entities[A]
    assert "attendees" not in entities[R] | entities[E]


def test_not_found_is_404(client: TestClient) -> None:
    c = as_role(client, A)
    for path in ("/editions/999", "/events/999", "/sessions/999", "/speakers/999",
                 "/partners/999", "/attendees/999"):  # fmt: skip
        assert c.get(path).status_code == 404, path


# ---------------------------------------------------------------- writes


def test_editor_builds_event_in_draft_edition(client: TestClient) -> None:
    c = as_role(client, E)
    event = c.post("/events", json=event_body(DRAFT_EDITION))
    assert event.status_code == 201 and event.json()["status"] == "draft"
    eid = event.json()["id"]
    session = c.post("/sessions", json=session_body(eid)).json()
    speaker = c.post(
        "/speakers", json={"first_name": "Ana", "last_name": "Test", "email": "ana@example.com"}
    ).json()
    partner = c.post("/partners", json={"name": "Testco"}).json()
    link = {"speaker_id": speaker["id"]}
    assert c.post(f"/sessions/{session['id']}/speakers", json=link).status_code == 201
    assert c.post(f"/sessions/{session['id']}/speakers", json=link).status_code == 409
    link = {"partner_id": partner["id"]}
    assert c.post(f"/events/{eid}/partners", json=link).status_code == 201
    assert c.post(f"/events/{eid}/partners", json=link).status_code == 409
    assert c.get(f"/events/{eid}").json()["partner_ids"] == [partner["id"]]


def test_editor_cannot_move_event_out_of_draft_edition(client: TestClient) -> None:
    c = as_role(client, E)
    eid = c.post("/events", json=event_body(DRAFT_EDITION)).json()["id"]
    assert c.patch(f"/events/{eid}", json={"edition_id": ACTIVE_EDITION}).status_code == 403
    assert c.patch(f"/events/{eid}", json={"status": "active"}).json()["status"] == "active"


def test_editions_are_admin_only(client: TestClient) -> None:
    assert client.post("/editions", json=NEW_EDITION, headers=auth(E)).status_code == 403
    assert client.post("/editions", json=NEW_EDITION, headers=auth(A)).status_code == 201
    assert client.post("/editions", json=NEW_EDITION, headers=auth(A)).status_code == 409


def test_validation_rejects_bad_bodies(client: TestClient) -> None:
    c = as_role(client, A)
    body = event_body(ACTIVE_EDITION)
    assert c.post("/events", json=body | {"extra": 1}).status_code == 422
    assert c.post("/events", json=body | {"end_at": "2027-04-01T00:00:00"}).status_code == 422
    assert c.post("/events", json=body | {"status": "archived"}).status_code == 422
    bad_dates = NEW_EDITION | {"start_date": "2030-02-01", "end_date": "2030-01-01"}
    assert c.post("/editions", json=bad_dates).status_code == 422
    assert c.post("/events", json=event_body(999)).status_code == 404
    assert c.patch("/events/1", json={"archived": True}).status_code == 422
    assert c.patch("/events/1", json={"status": "archived"}).status_code == 422
    assert c.patch("/events/1", json={}).status_code == 422
    assert c.patch("/events/1", json={"name": None}).status_code == 422
    assert c.patch("/nonsense/1", json={"name": "x"}).status_code == 422
    assert c.patch(f"/events/{ARCHIVED_EVENT}", json={"status": "active"}).status_code == 409


def test_archive_cycle_restores_previous_status(client: TestClient) -> None:
    c = as_role(client, E)
    draft = c.post("/events", json=event_body(DRAFT_EDITION)).json()
    for event_id, before in ((ACTIVE_EVENT, "active"), (draft["id"], "draft")):
        archived = c.post(f"/events/{event_id}/archive").json()
        assert archived["archived"] and archived["archived_at"]
        assert (archived["status"], archived["previous_status"]) == ("archived", before)
        assert c.post(f"/events/{event_id}/archive").status_code == 409
        # Archived parents refuse new children (admin, to rule out the draft rule).
        child = client.post("/sessions", json=session_body(event_id), headers=auth(A))
        assert child.status_code == 409
        restored = c.post(f"/events/{event_id}/unarchive").json()
        assert not restored["archived"] and restored["archived_at"] is None
        assert (restored["status"], restored["previous_status"]) == (before, None)
        assert c.post(f"/events/{event_id}/unarchive").status_code == 409


def test_edition_archive_is_not_cascading(client: TestClient) -> None:
    c = as_role(client, A)
    edition = c.post("/editions/1/archive").json()
    assert edition["status"] == "archived"
    assert not any(e["archived"] for e in c.get("/events", params={"edition_id": 1}).json())
    assert c.post("/editions/1/unarchive").json()["status"] == "active"


def test_notifications_go_to_outbox(client: TestClient) -> None:
    sent = client.post("/notifications", headers=auth(E), json=NOTE)
    assert sent.status_code == 201 and sent.json()["status"] == "queued"
    outbox = client.get("/outbox", headers=auth(A)).json()
    assert [(m["to"], m["subject"]) for m in outbox] == [("team@example.org", "Hi")]


def test_no_delete_route_exists() -> None:
    app = create_app(make_settings())
    methods = {m for r in app.routes if isinstance(r, APIRoute) for m in r.methods or ()}
    assert "DELETE" not in methods
