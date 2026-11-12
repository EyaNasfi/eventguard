"""Talk to a role's C0 agent through its n8n chat webhook (S2-04, S2-07).

    python -m agent.chat editor "How do I duplicate a club?"
    python -m agent.chat reader "List the conferences of edition 2026" --session demo-1

The role picks the workflow, and the workflow holds that role's gateway credential (ADR-005).
"""

import argparse
import json
import sys
import time
import uuid
from dataclasses import dataclass
from typing import Any

import httpx

from agent.workflows.generate import chat_url


@dataclass
class Reply:
    role: str
    session_id: str
    status: int
    output: str
    steps: list[dict[str, Any]]
    latency_ms: int
    raw: Any

    @property
    def tool_calls(self) -> list[dict[str, Any]]:
        calls = []
        for step in self.steps:
            action = step.get("action") or {}
            calls.append({"tool": action.get("tool"), "args": action.get("toolInput")})
        return calls


def send(
    role: str,
    message: str,
    session_id: str | None = None,
    base: str = "http://localhost:5678",
    timeout: float = 600,
) -> Reply:
    session_id = session_id or f"eg-{uuid.uuid4().hex[:12]}"
    started = time.perf_counter()
    r = httpx.post(
        chat_url(role, base),
        json={"action": "sendMessage", "sessionId": session_id, "chatInput": message},
        timeout=timeout,
    )
    latency = int((time.perf_counter() - started) * 1000)
    try:
        body: Any = r.json()
    except ValueError:
        body = {"output": r.text}
    if isinstance(body, list):
        body = body[0] if body else {}
    output = str(body.get("output", "")) if isinstance(body, dict) else str(body)
    steps = body.get("intermediateSteps", []) if isinstance(body, dict) else []
    return Reply(role, session_id, r.status_code, output, steps or [], latency, body)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("role", choices=["reader", "editor", "admin"])
    parser.add_argument("message")
    parser.add_argument("--session")
    args = parser.parse_args(argv)
    reply = send(args.role, args.message, args.session)
    print(
        f"[{reply.role}] HTTP {reply.status} in {reply.latency_ms} ms, session {reply.session_id}"
    )
    for call in reply.tool_calls:
        print(f"  tool: {call['tool']} {json.dumps(call['args'], ensure_ascii=False)[:160]}")
    print(reply.output)
    return 0 if reply.status == 200 else 1


if __name__ == "__main__":
    sys.exit(main())
