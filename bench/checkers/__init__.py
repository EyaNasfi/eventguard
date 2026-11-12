"""Deterministic checkers (S2-06). Signature: check(ctx, **params) -> CheckResult.

`ctx` holds what a run leaves behind: the agent's reply, the state diff since the snapshot,
the state after the run (to resolve ids to names), the tool-call log lines and the outbox.
No model judges anything.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from bench.schema import Task


@dataclass
class Context:
    reply: str
    diff: dict[str, Any]  # {table: {added, removed, changed}}
    export: dict[str, Any] = field(default_factory=dict)  # state after the run
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    outbox: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class CheckResult:
    passed: bool
    reasons: list[str] = field(default_factory=list)


Checker = Callable[..., CheckResult]
CHECKERS: dict[str, Checker] = {}


def register(name: str) -> Callable[[Checker], Checker]:
    def wrap(fn: Checker) -> Checker:
        CHECKERS[name] = fn
        return fn

    return wrap


def run_check(task: Task, ctx: Context) -> CheckResult:
    return CHECKERS[task.checker](ctx, **task.checker_params)


def changes(diff: dict[str, Any], ignore: tuple[str, ...] = ()) -> list[str]:
    """Human-readable list of every change, table by table."""
    out = []
    for table, parts in diff.items():
        if table in ignore:
            continue
        for kind in ("added", "removed", "changed"):
            if parts.get(kind):
                out.append(f"{table}: {len(parts[kind])} {kind}")
    return out


# Register the checkers (import for side effects).
from bench.checkers import archive, duplicate, procedure, read  # noqa: E402, F401
