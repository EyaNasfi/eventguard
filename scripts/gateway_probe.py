"""Live check of the gateway from inside the Docker network (manual test guide, L10).

    Get-Content scripts\\gateway_probe.py -Raw | docker compose exec -T gateway python -

Runs a real MCP client (official SDK) against http://gateway:8100/mcp with the role tokens the
gateway container already has. Prints results only, never a token.
"""

import asyncio
import json
import os

import httpx2
import mcp_types as types
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

URL = "http://gateway:8100/mcp"
PING = {"jsonrpc": "2.0", "id": 1, "method": "ping"}
ACCEPT = {"Accept": "application/json, text/event-stream"}
NEW_EVENT = {
    "edition_id": 3,
    "type": "club",
    "name": "Probe",
    "venue": "x",
    "start_at": "2027-01-01T10:00:00",
    "end_at": "2027-01-01T11:00:00",
}


def first_text(result: object) -> str:
    assert isinstance(result, types.CallToolResult)  # noqa: S101
    block = result.content[0]
    return block.text if isinstance(block, types.TextContent) else str(block)


async def run(role: str, mode: str = "auto") -> None:
    headers = {"Authorization": "Bearer " + os.environ[f"GATEWAY_TOKEN_{role.upper()}"]}
    async with httpx2.AsyncClient(headers=headers, timeout=30) as http:
        transport = streamable_http_client(URL, http_client=http)
        async with Client(transport, mode=mode) as client:
            tools = await client.list_tools()
            print(f"[{role}/{mode}] protocol {client.protocol_version}, {len(tools.tools)} tools")
            got = await client.call_tool("get_event", {"event_id": 12})
            print(f"[{role}] get_event 12 ->", json.loads(first_text(got))["name"])
            created = await client.call_tool("create_event", NEW_EVENT)
            assert isinstance(created, types.CallToolResult)  # noqa: S101
            print(
                f"[{role}] create_event -> is_error={created.is_error}: {first_text(created)[:90]}"
            )
            for path in ("/_test/reset", "/%5Ftest/snapshot"):
                args = {"method": "POST", "path": path, "body": {"seed": 1}}
                raw = await client.call_tool("raw_api_call", args)
                assert isinstance(raw, types.CallToolResult)  # noqa: S101
                outcome = f"is_error={raw.is_error}: {first_text(raw)[:80]}"
                print(f"[{role}] raw_api_call {path} -> {outcome}")


async def main() -> None:
    print("env has EVENTSIM_TEST_TOKEN:", "EVENTSIM_TEST_TOKEN" in os.environ)
    print("env has GEMINI_API_KEY:", "GEMINI_API_KEY" in os.environ)
    async with httpx2.AsyncClient(timeout=10) as http:
        response = await http.post(URL, json=PING, headers=ACCEPT)
        print("no bearer ->", response.status_code)
        eventsim_token = {"Authorization": "Bearer " + os.environ["EVENTSIM_TOKEN_ADMIN"]}
        response = await http.post(URL, json=PING, headers={**ACCEPT, **eventsim_token})
        print("EventSim admin token as bearer ->", response.status_code)
    await run("reader")
    await run("editor", mode="legacy")


if __name__ == "__main__":
    asyncio.run(main())
