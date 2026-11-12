"""Export agent runs from n8n to `logs/agent_runs.jsonl` (S2-05, FR-AGT-08, NFR-02).

    python -m agent.export_runs              # new executions of the C0 agent workflows
    python -m agent.export_runs --limit 50

One line per n8n execution: role, chat session, status, latency, number of model calls and
tokens (prompt, completion, total), requested model, temperature, config name and hash, git
commit. Re-running only appends executions that are not in the file yet.

n8n 2.47.5 stores token usage per model call but **not** the model version that Google served
(checked 2026-11-13: the Gemini node output has `tokenUsage` and `generationInfo` only). So
`model_version` is null here; the smoke run records it with one probe call per batch
(`agent.model_probe`).
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from agent.n8n_lab import ROLES, N8n, client_from_env, load_env
from config.loader import resolve

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "logs" / "agent_runs.jsonl"
WORKFLOW = "EventGuard C0 agent ({role})"


def git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],  # noqa: S607
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _when(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _ms(start: str | None, stop: str | None) -> int | None:
    if not start or not stop:
        return None
    return int((_when(stop) - _when(start)).total_seconds() * 1000)


def executed_model(execution: dict[str, Any]) -> str | None:
    """The model of the workflow version that ran (n8n saves it with the execution)."""
    for node in (execution.get("workflowData") or {}).get("nodes") or []:
        if node.get("type", "").endswith("lmChatGoogleGemini"):
            name = str((node.get("parameters") or {}).get("modelName") or "")
            return name.removeprefix("models/") or None
    return None


def run_record(execution: dict[str, Any], role: str) -> dict[str, Any]:
    runs = ((execution.get("data") or {}).get("resultData") or {}).get("runData") or {}
    usage = {"model_calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    session = None
    tool_calls = 0
    for node, node_runs in runs.items():
        for run in node_runs:
            data = run.get("data") or {}
            for out in data.get("ai_languageModel") or []:
                for item in out or []:
                    tokens = (item.get("json") or {}).get("tokenUsage") or {}
                    if tokens:
                        usage["model_calls"] += 1
                        usage["prompt_tokens"] += int(tokens.get("promptTokens", 0))
                        usage["completion_tokens"] += int(tokens.get("completionTokens", 0))
                        usage["total_tokens"] += int(tokens.get("totalTokens", 0))
            if node == "When chat message received":
                main = (data.get("main") or [[{}]])[0] or [{}]
                session = (main[0].get("json") or {}).get("sessionId")
            if "gateway" in node.lower():
                tool_calls += 1
    error = ((execution.get("data") or {}).get("resultData") or {}).get("error") or {}
    return {
        "execution_id": str(execution.get("id")),
        "workflow": WORKFLOW.format(role=role),
        "role": role,
        "session_id": session,
        "status": execution.get("status"),
        "started": execution.get("startedAt"),
        "stopped": execution.get("stoppedAt"),
        "latency_ms": _ms(execution.get("startedAt"), execution.get("stoppedAt")),
        **usage,
        "tool_node_runs": tool_calls,
        "error": (error.get("message") or None),
        "model": executed_model(execution),
    }


def export(n8n: N8n, env: dict[str, str], out: Path = OUT, limit: int = 100) -> int:
    config_name = env.get("EVENTGUARD_CONFIG", "C0")
    seen: set[str] = set()
    if out.exists():
        seen = {json.loads(line)["execution_id"] for line in out.read_text("utf-8").splitlines()}
    out.parent.mkdir(parents=True, exist_ok=True)
    workflows = n8n.workflows()
    commit = git_commit()
    added = 0
    with out.open("a", encoding="utf-8") as f:
        for role in ROLES:
            wid = workflows.get(WORKFLOW.format(role=role))
            if not wid:
                continue
            for row in reversed(n8n.executions(wid, limit=limit)):
                if str(row["id"]) in seen or row.get("status") in ("running", "new", "waiting"):
                    continue
                record = run_record(n8n.execution(str(row["id"])), role)
                # Config hash for the model that actually ran (the hash includes the model).
                model = record["model"] or env.get("GEMINI_MODEL", "")
                config = resolve(config_name, env={**env, "GEMINI_MODEL": model})
                record |= {
                    "model": config.model.name,
                    "model_version": None,
                    "temperature": config.model.temperature,
                    "config_name": config.name,
                    "config_hash": config.hash,
                    "git_commit": commit,
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                added += 1
    return added


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args(argv)
    env = load_env()
    added = export(client_from_env(env), env, limit=args.limit)
    print(f"appended {added} run(s) to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
