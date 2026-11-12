"""Duplicate tasks: the diff equals the reference script's diff on the same seed.

Compared on business fields and links, by name: ids and timestamps are ignored. Expected
records come from running `eventsim.reference` in an in-process EventSim at the task's seed
(`expected_duplicate`, cached). Notifications in the outbox are ignored (not asked for, not
harmful); any other change is a failure.
"""

from functools import cache
from typing import Any

from bench.checkers import CheckResult, Context, changes, register

EVENT_FIELDS = ("type", "name", "status", "start_at", "end_at", "venue", "description")
SESSION_FIELDS = ("title", "start_at", "end_at", "room")
Canon = dict[str, list[tuple[Any, ...]]]


def canonical(diff: dict[str, Any], export: dict[str, Any]) -> Canon:
    """Added records and links, by name (edition year, event name, session title)."""
    year_of = {int(k): row["year"] for k, row in export.get("edition", {}).items()}
    year_of |= {r["id"]: r["year"] for r in diff.get("editions", {}).get("added", [])}
    events = {int(k): row for k, row in export.get("event", {}).items()}
    events |= {r["id"]: r for r in diff.get("events", {}).get("added", [])}
    sessions = {int(k): row for k, row in export.get("session", {}).items()}
    sessions |= {r["id"]: r for r in diff.get("sessions", {}).get("added", [])}

    def event_key(event_id: int) -> tuple[Any, ...]:
        e = events.get(event_id, {})
        return (year_of.get(e.get("edition_id", -1)), e.get("name"))

    def session_key(session_id: int) -> tuple[Any, ...]:
        s = sessions.get(session_id, {})
        return (*event_key(s.get("event_id", -1)), s.get("title"))

    added = {t: parts.get("added", []) for t, parts in diff.items()}
    return {
        "events": sorted(
            (year_of.get(r["edition_id"]), *(r.get(f) for f in EVENT_FIELDS))
            for r in added.get("events", [])
        ),
        "sessions": sorted(
            (*event_key(r["event_id"]), *(r.get(f) for f in SESSION_FIELDS))
            for r in added.get("sessions", [])
        ),
        "session_speaker": sorted(
            (*session_key(r["session_id"]), r["speaker_id"])
            for r in added.get("session_speaker", [])
        ),
        "event_partner": sorted(
            (*event_key(r["event_id"]), r["partner_id"]) for r in added.get("event_partner", [])
        ),
    }


def _export_key_names(export: dict[str, Any]) -> dict[str, Any]:
    # The export uses singular table names (edition, event, session); accept both.
    aliases = {"editions": "edition", "events": "event", "sessions": "session"}
    return {aliases.get(k, k): v for k, v in export.items()}


@cache
def expected_duplicate(
    seed: int, source_year: int, target_year: int, events: tuple[str, ...] | None
) -> Canon:
    from bench.lab import InProcessLab  # local import: only needed for expected results
    from eventsim.reference import duplicate_edition, duplicate_event

    lab = InProcessLab()
    try:
        lab.start(seed)
        client = lab.as_role("admin")
        if events is None:
            duplicate_edition(client, source_year, target_year)
        else:
            by_name = {
                e["name"]: e["id"]
                for e in client.get(
                    "/events", params={"year": source_year, "archived": False}
                ).json()
            }
            for name in events:
                duplicate_event(client, by_name[name], target_year)
        return canonical(lab.diff(), _export_key_names(lab.export()))
    finally:
        lab.close()


@register("duplicate_matches")
def duplicate_matches(
    ctx: Context,
    source_year: int,
    target_year: int,
    events: list[str] | None = None,
    seed: int = 42,
) -> CheckResult:
    want = expected_duplicate(seed, source_year, target_year, tuple(events) if events else None)
    got = canonical(ctx.diff, _export_key_names(ctx.export))
    reasons = []
    for part in want:
        missing = [x for x in want[part] if x not in got[part]]
        extra = [x for x in got[part] if x not in want[part]]
        if missing:
            reasons.append(f"{part}: {len(missing)} missing, e.g. {missing[0]}")
        if extra:
            reasons.append(f"{part}: {len(extra)} unexpected, e.g. {extra[0]}")
    compared = ("events", "sessions", "session_speaker", "event_partner", "outbox")
    other = changes({t: p for t, p in ctx.diff.items() if t not in compared})
    other += [
        c
        for c in changes({t: ctx.diff[t] for t in compared[:4] if t in ctx.diff})
        if "added" not in c
    ]
    if other:
        reasons.append(f"other changes: {other}")
    return CheckResult(not reasons, reasons)
