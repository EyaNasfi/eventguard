"""Run one task against the real agent and check it (S2-07).

For a task: reset EventSim to the task's seed and snapshot it (harness token, host side only,
never the agent's), call the role's chat webhook with a fresh session id, wait for the reply,
collect the state diff, the export, the outbox and this session's lines from the gateway's
tool-call log, run the checker, and return one result record.

Needs the lab with the dev override (EventSim on 127.0.0.1:8000 for the harness) and n8n.
"""

import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from agent.chat import send
from agent.export_runs import WORKFLOW, git_commit, run_record
from agent.n8n_lab import N8n, client_from_env, load_env
from bench.checkers import Context, run_check
from bench.schema import Task
from config.loader import resolve

ROOT = Path(__file__).resolve().parent.parent
TOOL_LOG = ROOT / "logs" / "tool_calls.jsonl"


@dataclass
class Harness:
    base: str
    token: str

    def _h(self) -> dict[str, str]:
        return {"X-Test-Token": self.token}

    def start(self, seed: int) -> None:
        httpx.post(
            f"{self.base}/_test/reset", json={"seed": seed}, headers=self._h(), timeout=60
        ).raise_for_status()
        httpx.post(f"{self.base}/_test/snapshot", headers=self._h(), timeout=60).raise_for_status()

    def get(self, path: str) -> Any:
        r = httpx.get(f"{self.base}{path}", headers=self._h(), timeout=60)
        return r.raise_for_status().json()


def tool_lines(session_id: str, path: Path = TOOL_LOG) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line)
    return [r for r in rows if r.get("session_id") == session_id]


def find_execution(n8n: N8n, role: str, session_id: str, tries: int = 10) -> dict[str, Any] | None:
    wid = n8n.workflows()[WORKFLOW.format(role=role)]
    for _ in range(tries):
        for row in n8n.executions(wid, limit=10):
            full = n8n.execution(str(row["id"]))
            if run_record(full, role)["session_id"] == session_id:
                return full
        time.sleep(2)
    return None


def classify(status: int, execution: dict[str, Any] | None, passed: bool) -> str | None:
    """First guess only; every failure is reviewed by hand in the sprint report."""
    if passed:
        return None
    if status != 200 or execution is None or execution.get("status") != "success":
        return "infrastructure"
    return "agent"


def run_task(task: Task, run_id: str, model_version: str | None = None) -> dict[str, Any]:
    env = load_env()
    harness = Harness(
        env.get("EVENTSIM_HARNESS_URL", "http://127.0.0.1:8000"), env["EVENTSIM_TEST_TOKEN"]
    )
    n8n = client_from_env(env)
    config = resolve(env.get("EVENTGUARD_CONFIG", "C0"), env=env)

    harness.start(task.seed)
    session_id = f"{run_id}.{task.id}.{uuid.uuid4().hex[:6]}"
    reply = send(task.role, task.prompt, session_id)
    diff = harness.get("/_test/state-diff")["tables"]
    ctx = Context(
        reply=reply.output,
        diff=diff,
        export=harness.get("/_test/export"),
        tool_calls=tool_lines(session_id),
        outbox=harness.get("/_test/outbox"),
    )
    result = run_check(task, ctx)
    execution = find_execution(n8n, task.role, session_id)
    usage = run_record(execution, task.role) if execution else {}
    return {
        "run_id": run_id,
        "task_id": task.id,
        "category": task.category,
        "role": task.role,
        "passed": result.passed,
        "reasons": result.reasons,
        "failure_class": classify(reply.status, execution, result.passed),
        "http_status": reply.status,
        "execution_id": usage.get("execution_id"),
        "execution_status": usage.get("status"),
        "error": usage.get("error"),
        "session_id": session_id,
        "config_name": config.name,
        "config_hash": config.hash,
        "model": config.model.name,
        "model_version": model_version,
        "temperature": config.model.temperature,
        "seed": task.seed,
        "tasks_version": f"tasks-v{task.version}",
        "git_commit": git_commit(),
        "latency_ms": reply.latency_ms,
        "model_calls": usage.get("model_calls"),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "gateway_tool_calls": len(ctx.tool_calls),
        "tools": [line["tool"] for line in ctx.tool_calls],
        "reply_excerpt": reply.output[:400],
    }
