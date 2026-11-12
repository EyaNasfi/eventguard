"""Positive and negative controls for every task (S2-06).

A positive control does the task correctly by hand (or with the reference script), with the
task's own role, in an in-process EventSim at the task's seed: the checker must pass. Negative
controls break it on purpose (empty diff, wrong sheet, missing value, wrong edition, one extra
record archived, a write during a read): the checker must fail.
"""

from typing import Any

from bench.checkers import Context
from bench.lab import InProcessLab
from bench.schema import Task
from eventsim.reference import duplicate_edition, duplicate_event


def _ctx(lab: InProcessLab, reply: str) -> Context:
    return Context(reply=reply, diff=lab.diff(), export=lab.export(), outbox=lab.outbox())


def _event_id(lab: InProcessLab, year: int, name: str) -> int:
    rows = lab.as_role("admin").get("/events", params={"year": year}).json()
    return int(next(r["id"] for r in rows if r["name"] == name))


def _stray_write(lab: InProcessLab) -> None:
    lab.as_role("admin").post("/partners", json={"name": "Stray Partner"}).raise_for_status()


def _good_reply(task: Task) -> str:
    if task.category == "procedure":
        return f"Follow the procedure sheet (see {task.expected.cited_sheet[0]})."
    if task.category == "read":
        return "Answer: " + "; ".join(group[0] for group in task.expected.reply_must_contain)
    return "Done."


def _duplicate(lab: InProcessLab, task: Task, target_year: int) -> None:
    p = task.checker_params
    client = lab.as_role(task.role if target_year == p["target_year"] else "admin")
    if p.get("events") is None:
        duplicate_edition(client, p["source_year"], target_year)
    else:
        for name in p["events"]:
            duplicate_event(client, _event_id(lab, p["source_year"], name), target_year)


def _archive_targets(lab: InProcessLab, task: Task) -> tuple[list[int], list[int]]:
    p = task.checker_params
    admin = lab.as_role("admin")
    events = [_event_id(lab, y, n) for y, n in p.get("events") or []]
    if (year := p.get("events_of_year")) is not None:
        events += [
            r["id"] for r in admin.get("/events", params={"year": year, "archived": False}).json()
        ]
    editions = [
        admin.get("/editions", params={"year": y}).json()[0]["id"] for y in p.get("editions") or []
    ]
    return events, editions


def _archive(lab: InProcessLab, role: str, events: list[int], editions: list[int]) -> None:
    client = lab.as_role(role)
    for i in events:
        client.post(f"/events/{i}/archive").raise_for_status()
    for i in editions:
        client.post(f"/editions/{i}/archive").raise_for_status()


def positive(lab: InProcessLab, task: Task) -> Context:
    lab.start(task.seed)
    if task.category == "duplicate":
        _duplicate(lab, task, task.checker_params["target_year"])
    elif task.category == "archive":
        _archive(lab, task.role, *_archive_targets(lab, task))
    return _ctx(lab, _good_reply(task))


def negatives(lab: InProcessLab, task: Task) -> dict[str, Context]:
    out: dict[str, Context] = {}
    lab.start(task.seed)
    out["empty diff, no answer"] = _ctx(lab, "I could not do that.")
    if task.category == "procedure":
        wrong = "PROC-01" if "PROC-18" in task.expected.cited_sheet else "PROC-18"
        out["wrong sheet"] = _ctx(lab, f"See {wrong}.")
        lab.start(task.seed)
        _stray_write(lab)
        out["right sheet but a write"] = _ctx(lab, _good_reply(task))
    elif task.category == "read":
        lab.start(task.seed)
        _stray_write(lab)
        out["right values but a write"] = _ctx(lab, _good_reply(task))
        groups = task.expected.reply_must_contain
        if len(groups) > 1:
            partial = "Answer: " + "; ".join(g[0] for g in groups[:-1])
            lab.start(task.seed)
            out["one value missing"] = _ctx(lab, partial)
    elif task.category == "duplicate":
        lab.start(task.seed)
        _duplicate(lab, task, 2028)  # wrong edition (created by admin)
        out["wrong edition (2028)"] = _ctx(lab, "Done.")
        lab.start(task.seed)
        _duplicate(lab, task, task.checker_params["target_year"])
        _stray_write(lab)
        out["right copy plus a stray record"] = _ctx(lab, "Done.")
    elif task.category == "archive":
        events, editions = _archive_targets(lab, task)
        admin = lab.as_role("admin")
        live = [r["id"] for r in admin.get("/events", params={"archived": False}).json()]
        extra = next(i for i in live if i not in events)
        lab.start(task.seed)
        _archive(lab, "admin", [*events, extra], editions)
        out["one extra event archived"] = _ctx(lab, "Done.")
        if task.checker_params.get("events"):
            other: list[Any] = []
            for _year, name in task.checker_params["events"]:
                rows = admin.get("/events", params={"archived": False}).json()
                other += [r["id"] for r in rows if r["name"] == name and r["id"] not in events]
            if other:
                lab.start(task.seed)
                _archive(lab, "admin", other[:1], [])
                out["same name, wrong edition"] = _ctx(lab, "Done.")
    return out
