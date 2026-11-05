"""The reference script is ground truth for duplicate checkers (FR-SIM-10)."""

from typing import Any

from fastapi.testclient import TestClient

from eventsim.reference import Shift, duplicate_edition, duplicate_event
from tests.conftest import HARNESS, as_role

VOLATILE = {"id", "created_at", "updated_at", "edition_id", "event_id", "session_id"}


def fresh_diff(client: TestClient, seed: int = 42) -> None:
    client.post("/_test/reset", json={"seed": seed}, headers=HARNESS)
    client.post("/_test/snapshot", headers=HARNESS)


def added(client: TestClient, table: str) -> list[dict[str, Any]]:
    diff = client.get("/_test/state-diff", headers=HARNESS).json()
    rows: list[dict[str, Any]] = diff["tables"][table]["added"]
    return rows


def business(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{k: v for k, v in r.items() if k not in VOLATILE} for r in rows]


def test_shift_rules() -> None:
    assert Shift(years=1).apply("2026-03-14T09:00:00") == "2027-03-14T09:00:00"
    assert Shift(years=1).apply("2028-02-29") == "2029-02-28"
    assert Shift(years=1, days=7).apply("2026-03-14") == "2026-03-21"


def test_duplicate_edition_into_existing_draft(client: TestClient) -> None:
    fresh_diff(client)
    c = as_role(client, "admin")
    report = duplicate_edition(c, 2026, 2027)
    assert not report.created_edition

    source = c.get("/events", params={"year": 2026, "archived": False}).json()
    copies = added(c, "events")
    assert len(copies) == len(source) == 10  # the archived evening is not copied
    assert all(e["status"] == "draft" and e["start_at"].startswith("2027-") for e in copies)
    assert sorted(e["name"] for e in copies) == sorted(e["name"] for e in source)

    source_sessions = sum(len(c.get(f"/events/{e['id']}").json()["session_ids"]) for e in source)
    assert len(added(c, "sessions")) == source_sessions == len(report.sessions)
    assert len(added(c, "session_speaker")) == report.speaker_links > 0
    assert len(added(c, "event_partner")) == report.partner_links
    assert added(c, "speakers") == [] and added(c, "attendees") == [] and added(c, "editions") == []


def test_duplicate_edition_creates_missing_target(client: TestClient) -> None:
    fresh_diff(client)
    report = duplicate_edition(as_role(client, "admin"), 2026, 2028)
    assert report.created_edition
    edition = added(client, "editions")[0]
    assert (edition["year"], edition["name"], edition["status"]) == (
        2028,
        "Rendez-vous 2028",
        "draft",
    )
    assert all(e["start_at"].startswith("2028-") for e in added(client, "events"))


def test_reference_is_deterministic(client: TestClient) -> None:
    runs = []
    for _ in range(2):
        fresh_diff(client)
        duplicate_edition(as_role(client, "admin"), 2026, 2027)
        runs.append(business(added(client, "events")) + business(added(client, "sessions")))
    assert runs[0] == runs[1]


def test_duplicate_single_club_without_links(client: TestClient) -> None:
    fresh_diff(client)
    c = as_role(client, "editor")
    club = c.get("/events", params={"year": 2026, "type": "club"}).json()[0]
    report = duplicate_event(
        c, club["id"], 2027, shift_days=364, with_speakers=False, with_partners=False
    )
    assert list(report.events) == [club["id"]]
    [copy] = added(c, "events")
    assert copy["name"] == club["name"] and copy["type"] == "club"
    assert added(c, "session_speaker") == [] and added(c, "event_partner") == []
    assert copy["start_at"] != club["start_at"].replace("2026", "2027")  # 364 days, not 1 year
