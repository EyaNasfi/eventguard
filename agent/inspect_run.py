"""Summarise the latest n8n executions of the C0 agent workflows (debugging aid, S2-04).

    python -m agent.inspect_run [--workflow "EventGuard C0 agent (editor)"] [--last 1]

Prints status, error node and message, token usage and the tool calls of each execution. It
reads n8n's execution data through the public API and never prints credentials.
"""

import argparse
import json
import sys
from typing import Any

from agent.n8n_lab import client_from_env


def run_data(execution: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    data = execution.get("data") or {}
    result: dict[str, list[dict[str, Any]]] = (data.get("resultData") or {}).get("runData") or {}
    return result


def summary(execution: dict[str, Any]) -> dict[str, Any]:
    runs = run_data(execution)
    tokens = {"prompt": 0, "completion": 0, "total": 0, "model_calls": 0}
    tools: list[str] = []
    for node, node_runs in runs.items():
        for run in node_runs:
            for out in (run.get("data") or {}).get("ai_languageModel", []) or []:
                for item in out or []:
                    usage = ((item.get("json") or {}).get("tokenUsage")) or {}
                    if usage:
                        tokens["model_calls"] += 1
                        tokens["prompt"] += int(usage.get("promptTokens", 0))
                        tokens["completion"] += int(usage.get("completionTokens", 0))
                        tokens["total"] += int(usage.get("totalTokens", 0))
            if "gateway" in node.lower():
                tools.append(node)
    error = (execution.get("data") or {}).get("resultData", {}).get("error") or {}
    return {
        "id": execution.get("id"),
        "status": execution.get("status"),
        "started": execution.get("startedAt"),
        "stopped": execution.get("stoppedAt"),
        "error_node": (error.get("node") or {}).get("name"),
        "error": (error.get("message") or "")[:400],
        "error_description": (error.get("description") or "")[:400],
        "tokens": tokens,
        "tool_node_runs": len(tools),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow", default="EventGuard C0 agent (editor)")
    parser.add_argument("--last", type=int, default=1)
    args = parser.parse_args(argv)
    n8n = client_from_env()
    wid = n8n.workflows()[args.workflow]
    for execution in n8n.executions(wid, limit=args.last):
        full = n8n.execution(str(execution["id"]))
        print(json.dumps(summary(full), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
