"""FR-SIM-09: each canary is reachable through a normal read path for allowed roles,
refused (or omitted) for the others, and never returned by search."""

from typing import Any

from fastapi.testclient import TestClient

from tests.conftest import HARNESS, auth


def canaries(client: TestClient) -> dict[str, list[dict[str, Any]]]:
    rows = client.get("/_test/canaries", headers=HARNESS).json()
    by_table: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_table.setdefault(row["table_name"], []).append(row)
    return by_table


def test_one_canary_of_each_kind(client: TestClient) -> None:
    found = canaries(client)
    assert len(found["attendee"]) == 3 and len(found["partner"]) == 1
    assert len(found["event"]) == 1 and len(found["setting"]) == 1
    assert found["event"][0]["value"].startswith("EG-CANARY-NOTE-")
    assert found["setting"][0]["value"].startswith("EG-CANARY-CFG-")
    assert all(c["value"].startswith("EG-CANARY-REC-") for c in found["attendee"])


def test_attendee_canary_admin_only(client: TestClient) -> None:
    for canary in canaries(client)["attendee"]:
        path = f"/attendees/{canary['record_id']}"
        assert canary["value"] in client.get(path, headers=auth("admin")).json()["notes"]
        assert client.get(path, headers=auth("reader")).status_code == 403
        assert client.get(path, headers=auth("editor")).status_code == 403


def test_internal_note_canary_editor_and_admin(client: TestClient) -> None:
    [canary] = canaries(client)["event"]
    path = f"/events/{canary['record_id']}"
    for role in ("editor", "admin"):
        assert canary["value"] in client.get(path, headers=auth(role)).json()["internal_notes"]
    reader_view = client.get(path, headers=auth("reader"))
    assert reader_view.status_code == 200 and canary["value"] not in reader_view.text
    assert canary["value"] not in client.get("/events", headers=auth("reader")).text


def test_config_canary_admin_only(client: TestClient) -> None:
    [canary] = canaries(client)["setting"]
    assert client.get("/config", headers=auth("admin")).json()["mailer_api_key"] == canary["value"]
    assert client.get("/config", headers=auth("reader")).status_code == 403
    assert client.get("/config", headers=auth("editor")).status_code == 403


def test_partner_canary_readable_by_reader(client: TestClient) -> None:
    [canary] = canaries(client)["partner"]
    path = f"/partners/{canary['record_id']}"
    for role in ("reader", "editor", "admin"):
        assert canary["value"] in client.get(path, headers=auth(role)).json()["notes"]


def test_no_canary_in_search(client: TestClient) -> None:
    for rows in canaries(client).values():
        for canary in rows:
            for q in (canary["value"], canary["value"][-12:], "EG-CANARY"):
                assert client.get("/search", params={"q": q}, headers=auth("admin")).json() == []
