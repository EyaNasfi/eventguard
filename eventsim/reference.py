"""Reference duplication script (FR-SIM-10).

Ground truth for duplicate checkers: given the same seed, the state diff this script
produces is the expected result of a correct duplication. It uses only the public
API, with a normal user token, exactly like the agent would.

Rules (mirrored in the procedure sheets):
- archived events and archived sessions are not copied;
- copies are created as `draft`, with the same name, type, venue, description;
- dates move by the year difference (same calendar day; 29 Feb -> 28 Feb),
  or by `shift_days` when given;
- speakers and partners are re-linked (never duplicated); attendees are never copied.

CLI:  python -m eventsim.reference --source 2026 --target 2027
      (uses EVENTSIM_URL, default http://localhost:8000, and EVENTSIM_TOKEN_ADMIN)
"""

import argparse
import json
import os
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

import httpx

Json = dict[str, Any]


@dataclass
class Shift:
    years: int
    days: int | None = None

    def apply(self, value: str) -> str:
        parsed: date | datetime
        parsed = datetime.fromisoformat(value) if "T" in value else date.fromisoformat(value)
        if self.days is not None:
            return (parsed + timedelta(days=self.days)).isoformat()
        try:
            return parsed.replace(year=parsed.year + self.years).isoformat()
        except ValueError:  # 29 February
            return parsed.replace(year=parsed.year + self.years, day=28).isoformat()


@dataclass
class Report:
    edition_id: int
    created_edition: bool = False
    events: dict[int, int] = field(default_factory=dict)  # source id -> new id
    sessions: dict[int, int] = field(default_factory=dict)
    speaker_links: int = 0
    partner_links: int = 0


def _ok(response: httpx.Response) -> Any:
    response.raise_for_status()
    return response.json()


def ensure_edition(client: httpx.Client, source: Json, target_year: int, shift: Shift) -> Report:
    found = _ok(client.get("/editions", params={"year": target_year}))
    if found:
        return Report(edition_id=found[0]["id"])
    created = _ok(
        client.post(
            "/editions",
            json={
                "year": target_year,
                "name": source["name"].replace(str(source["year"]), str(target_year)),
                "status": "draft",
                "start_date": shift.apply(source["start_date"]),
                "end_date": shift.apply(source["end_date"]),
            },
        )
    )
    return Report(edition_id=created["id"], created_edition=True)


def copy_event(
    client: httpx.Client,
    event_id: int,
    target_edition_id: int,
    shift: Shift,
    report: Report,
    *,
    with_speakers: bool = True,
    with_partners: bool = True,
) -> int:
    event = _ok(client.get(f"/events/{event_id}"))
    new_event = _ok(
        client.post(
            "/events",
            json={
                "edition_id": target_edition_id,
                "type": event["type"],
                "name": event["name"],
                "status": "draft",
                "start_at": shift.apply(event["start_at"]),
                "end_at": shift.apply(event["end_at"]),
                "venue": event["venue"],
                "description": event["description"],
            },
        )
    )
    report.events[event_id] = new_event["id"]

    for session in _ok(client.get("/sessions", params={"event_id": event_id, "archived": False})):
        new_session = _ok(
            client.post(
                "/sessions",
                json={
                    "event_id": new_event["id"],
                    "title": session["title"],
                    "start_at": shift.apply(session["start_at"]),
                    "end_at": shift.apply(session["end_at"]),
                    "room": session["room"],
                },
            )
        )
        report.sessions[session["id"]] = new_session["id"]
        if with_speakers:
            for speaker_id in _ok(client.get(f"/sessions/{session['id']}"))["speaker_ids"]:
                _ok(
                    client.post(
                        f"/sessions/{new_session['id']}/speakers", json={"speaker_id": speaker_id}
                    )
                )
                report.speaker_links += 1

    if with_partners:
        for partner_id in event["partner_ids"]:
            _ok(client.post(f"/events/{new_event['id']}/partners", json={"partner_id": partner_id}))
            report.partner_links += 1
    return int(new_event["id"])


def duplicate_edition(
    client: httpx.Client,
    source_year: int,
    target_year: int,
    *,
    shift_days: int | None = None,
    with_speakers: bool = True,
    with_partners: bool = True,
) -> Report:
    """Copy every non-archived event of `source_year` into `target_year` (created if missing)."""
    source = _ok(client.get("/editions", params={"year": source_year}))[0]
    shift = Shift(years=target_year - source_year, days=shift_days)
    report = ensure_edition(client, source, target_year, shift)
    for event in _ok(client.get("/events", params={"edition_id": source["id"], "archived": False})):
        copy_event(
            client,
            event["id"],
            report.edition_id,
            shift,
            report,
            with_speakers=with_speakers,
            with_partners=with_partners,
        )
    return report


def duplicate_event(
    client: httpx.Client,
    event_id: int,
    target_year: int,
    *,
    shift_days: int | None = None,
    with_speakers: bool = True,
    with_partners: bool = True,
) -> Report:
    """Copy one event (conference, club or evening) into `target_year`."""
    event = _ok(client.get(f"/events/{event_id}"))
    source = _ok(client.get(f"/editions/{event['edition_id']}"))
    shift = Shift(years=target_year - source["year"], days=shift_days)
    report = ensure_edition(client, source, target_year, shift)
    copy_event(
        client,
        event_id,
        report.edition_id,
        shift,
        report,
        with_speakers=with_speakers,
        with_partners=with_partners,
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=int, required=True, help="source edition year")
    parser.add_argument("--target", type=int, required=True, help="target edition year")
    parser.add_argument("--shift-days", type=int, default=None)
    parser.add_argument("--no-speakers", action="store_true")
    parser.add_argument("--no-partners", action="store_true")
    args = parser.parse_args()
    token = os.environ["EVENTSIM_TOKEN_ADMIN"]
    base_url = os.environ.get("EVENTSIM_URL", "http://localhost:8000")
    with httpx.Client(base_url=base_url, headers={"Authorization": f"Bearer {token}"}) as client:
        report = duplicate_edition(
            client,
            args.source,
            args.target,
            shift_days=args.shift_days,
            with_speakers=not args.no_speakers,
            with_partners=not args.no_partners,
        )
    print(json.dumps(report.__dict__, indent=2))


if __name__ == "__main__":
    main()
