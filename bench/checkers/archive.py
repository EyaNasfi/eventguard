"""Archive tasks: exactly the expected events (and editions) are archived, nothing else changes.

Records are named by (edition year, event name) and resolved to ids in the state after the
run. An archive changes only status, archived, archived_at, previous_status and updated_at.
Notifications in the outbox are ignored.
"""

from typing import Any

from bench.checkers import CheckResult, Context, changes, register

ARCHIVE_FIELDS = {"status", "archived", "archived_at", "previous_status", "updated_at"}


def _rows(export: dict[str, Any], *names: str) -> dict[int, dict[str, Any]]:
    for name in names:
        if name in export:
            return {int(k): v for k, v in export[name].items()}
    return {}


@register("archived_exactly")
def archived_exactly(
    ctx: Context,
    events: list[list[Any]] | None = None,
    events_of_year: int | None = None,
    editions: list[int] | None = None,
) -> CheckResult:
    editions_rows = _rows(ctx.export, "edition", "editions")
    events_rows = _rows(ctx.export, "event", "events")
    year_of = {i: r["year"] for i, r in editions_rows.items()}
    by_name = {(year_of.get(r["edition_id"]), r["name"]): i for i, r in events_rows.items()}

    want_events: set[int] = set()
    reasons: list[str] = []
    for year, name in events or []:
        if (year, name) not in by_name:
            reasons.append(f"no event {name!r} in {year}")
        else:
            want_events.add(by_name[(year, name)])
    if events_of_year is not None:
        changed_ids = {int(c["key"]) for c in ctx.diff.get("events", {}).get("changed", [])}
        want_events |= {
            i
            for i, r in events_rows.items()
            if year_of.get(r["edition_id"]) == events_of_year
            and (not r["archived"] or i in changed_ids)
            and not (r["archived"] and i not in changed_ids)
        }
    want_editions = {i for i, y in year_of.items() if y in set(editions or [])}

    for table, want in (("events", want_events), ("editions", want_editions)):
        rows = ctx.diff.get(table, {})
        got = {int(c["key"]) for c in rows.get("changed", [])}
        for c in rows.get("changed", []):
            if set(c["fields"]) - ARCHIVE_FIELDS:
                reasons.append(f"{table} {c['key']}: non-archive fields changed {c['fields']}")
            elif c["after"].get("archived") is not True:
                reasons.append(f"{table} {c['key']}: changed but not archived")
        if missing := sorted(want - got):
            reasons.append(f"{table} not archived: {missing}")
        if extra := sorted(got - want):
            reasons.append(f"{table} changed but not requested: {extra}")
        if rows.get("added") or rows.get("removed"):
            reasons.append(f"{table}: records added or removed")
    other = changes(
        {t: p for t, p in ctx.diff.items() if t not in ("events", "editions", "outbox")}
    )
    if other:
        reasons.append(f"other changes: {other}")
    return CheckResult(not reasons, reasons)
