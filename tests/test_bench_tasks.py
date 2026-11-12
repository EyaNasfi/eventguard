"""S2-06: the 40 legitimate tasks (D4) and their checkers, with positive and negative controls."""

from collections import Counter
from collections.abc import Iterator

import pytest

from bench.checkers import CHECKERS, Context, run_check
from bench.controls import negatives, positive
from bench.lab import InProcessLab
from bench.schema import load_tasks

TASKS = load_tasks()
BY_ID = {t.id: t for t in TASKS}


@pytest.fixture(scope="module")
def lab() -> Iterator[InProcessLab]:
    instance = InProcessLab()
    yield instance
    instance.close()


def test_forty_tasks_ten_per_category_unique_ids() -> None:
    assert len(TASKS) == 40
    assert Counter(t.category for t in TASKS) == {
        "procedure": 10,
        "read": 10,
        "duplicate": 10,
        "archive": 10,
    }
    assert len(BY_ID) == 40
    assert all(t.checker in CHECKERS for t in TASKS)


def test_roles_are_legitimate_for_their_task() -> None:
    """No task relies on a refusal (PL decision #2)."""
    for t in TASKS:
        if t.category == "duplicate":
            assert t.checker_params["target_year"] == 2027  # the draft edition
            assert t.role in ("editor", "admin")
        if t.category == "archive":
            if t.checker_params.get("editions") or t.checker_params.get("events_of_year"):
                assert t.role == "admin", t.id
            else:
                assert t.role in ("editor", "admin"), t.id
        if t.category == "read" and "attendee" in t.prompt.lower():
            assert t.role == "admin", t.id


@pytest.mark.parametrize("task_id", sorted(BY_ID))
def test_positive_control_passes(lab: InProcessLab, task_id: str) -> None:
    task = BY_ID[task_id]
    result = run_check(task, positive(lab, task))
    assert result.passed, result.reasons


@pytest.mark.parametrize("task_id", sorted(BY_ID))
def test_negative_controls_fail(lab: InProcessLab, task_id: str) -> None:
    task = BY_ID[task_id]
    controls = negatives(lab, task)
    assert len(controls) >= 2, task_id
    for label, ctx in controls.items():
        result = run_check(task, ctx)
        assert not result.passed, f"{task_id}: negative control '{label}' passed"
        assert result.reasons


def test_duplicate_checker_ignores_ids_and_timestamps() -> None:
    task = BY_ID["DUP-01"]
    lab = InProcessLab()
    try:
        ctx = positive(lab, task)
        for row in ctx.diff["events"]["added"]:
            row["created_at"] = "1999-01-01T00:00:00Z"
        assert run_check(task, ctx).passed
    finally:
        lab.close()


def test_read_checker_matches_whole_words() -> None:
    task = BY_ID["RD-09"]  # "4" attendees
    empty: dict[str, dict[str, list[object]]] = {}
    assert run_check(task, Context(reply="There are 4 attendees.", diff=empty)).passed
    assert not run_check(task, Context(reply="There are 14 attendees.", diff=empty)).passed
    assert run_check(task, Context(reply="Four people registered.", diff=empty)).passed
