"""S2-05: the gateway writes one JSON line per tool call (FR-AGT-08, NFR-02)."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import mcp_types as types
import pytest
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from gateway.calllog import ToolCallLog, clean_session
from tests.test_gateway import (  # noqa: F401 (fixtures are used by name)
    BASE,
    GATEWAY_TOKENS,
    Lab,
    anyio_backend,
    eventsim,
    fresh,
    lab,
)

pytestmark = pytest.mark.anyio
FIELDS = {
    "ts",
    "session_id",
    "user",
    "role",
    "config_name",
    "config_hash",
    "model",
    "temperature",
    "git_commit",
    "tool",
    "arguments",
    "outcome",
    "http_status",
    "message",
    "latency_ms",
}


async def call_with_session(
    lab: Lab, role: str, tool: str, args: dict[str, Any], session: str
) -> types.CallToolResult:
    headers = {"Authorization": f"Bearer {GATEWAY_TOKENS[role]}"}
    async with lab.http(headers) as http:
        url = f"{BASE}/mcp?eg_session={session}"
        async with Client(streamable_http_client(url, http_client=http)) as client:
            result = await client.call_tool(tool, args)
    assert isinstance(result, types.CallToolResult)
    return result


@pytest.fixture
def logged(fresh: Lab, tmp_path: Path) -> Iterator[tuple[Lab, Path]]:
    path = tmp_path / "tool_calls.jsonl"
    original = fresh.gateway.calllog
    fresh.gateway.calllog = ToolCallLog(path, "test-model", 0.0, "abc1234")
    yield fresh, path
    fresh.gateway.calllog = original


def lines(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]


async def test_each_call_is_one_line_with_session_and_config_hash(
    logged: tuple[Lab, Path],
) -> None:
    lab, path = logged
    await call_with_session(lab, "editor", "get_event", {"event_id": 12}, "run-42.task-1")
    await call_with_session(lab, "reader", "create_partner", {"name": "Nope"}, "run-42.task-2")
    first, second = lines(path)
    assert set(first) == FIELDS
    assert first["session_id"] == "run-42.task-1" and first["role"] == "editor"
    assert first["outcome"] == "ok" and first["tool"] == "get_event"
    assert first["config_name"] == "C0" and first["config_hash"] == lab.gateway.config.hash
    assert first["model"] == "test-model" and first["git_commit"] == "abc1234"
    assert first["latency_ms"] >= 0
    assert second["outcome"] == "error" and "HTTP 403" in second["message"]


async def test_test_endpoint_refusals_are_logged(logged: tuple[Lab, Path]) -> None:
    lab, path = logged
    await call_with_session(
        lab, "admin", "raw_api_call", {"method": "POST", "path": "/_test/reset"}, "s1"
    )
    [line] = lines(path)
    assert line["outcome"] == "refused" and line["tool"] == "raw_api_call"
    assert line["arguments"]["path"] == "/_test/reset"


async def test_unknown_tool_is_logged_as_refused(logged: tuple[Lab, Path]) -> None:
    lab, path = logged
    await call_with_session(lab, "admin", "delete_everything", {}, "s2")
    [line] = lines(path)
    assert line["outcome"] == "refused" and line["tool"] == "delete_everything"


@pytest.mark.parametrize(
    ("raw", "kept"),
    [("chat-123", "chat-123"), (None, None), ("", None), ("a b", None), ("x" * 101, None)],
)
def test_session_values_are_cleaned(raw: str | None, kept: str | None) -> None:
    assert clean_session(raw) == kept


def test_no_path_means_no_file(tmp_path: Path) -> None:
    log = ToolCallLog(None, "m", 0.0, "c")
    assert log.path is None
