"""Tool-call log (S2-05, FR-AGT-08, NFR-02): one JSON line per tool call.

Written by the gateway to `GATEWAY_TOOL_LOG` (in the lab: `logs/tool_calls.jsonl` on the host,
bind-mounted at /logs). Every line carries what is needed to reproduce the run: config name and
hash, model and temperature (from the config), and the git commit of the lab.

The session id comes from the MCP URL (`/mcp?eg_session=...`, ADR-005). It only labels the line;
the identity is the bearer token, logged as `user` and `role`.
"""

import json
import re
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from gateway.pipeline import ToolCall, ToolResult

SESSION_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,100}$")


def clean_session(value: str | None) -> str | None:
    """Keep a session id only if it is short and plain; anything else is dropped (not logged)."""
    return value if value and SESSION_RE.match(value) else None


class ToolCallLog:
    def __init__(self, path: Path | None, model: str, temperature: float, git_commit: str) -> None:
        self.path = path
        self.model = model
        self.temperature = temperature
        self.git_commit = git_commit
        self._lock = threading.Lock()
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self, call: ToolCall, result: ToolResult, session: str | None, latency_ms: int
    ) -> dict[str, Any]:
        line: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "session_id": session,
            "user": f"gateway-token:{call.role.value}",
            "role": call.role.value,
            "config_name": call.config_name,
            "config_hash": call.config_hash,
            "model": self.model,
            "temperature": self.temperature,
            "git_commit": self.git_commit,
            "tool": call.tool,
            "arguments": call.arguments,
            "outcome": result.outcome,
            "http_status": result.http_status,
            "message": (result.message or "")[:300] or None,
            "latency_ms": latency_ms,
        }
        if self.path is not None:
            text = json.dumps(line, ensure_ascii=False, default=str)
            with self._lock, self.path.open("a", encoding="utf-8") as f:
                f.write(text + "\n")
        return line
