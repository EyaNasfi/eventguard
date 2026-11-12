"""Verification D (S2-09): each gateway bearer maps to the right EventSim user, and every
`/_test` path is refused, from inside the Docker network.

    Get-Content scripts\\gateway_identity_probe.py -Raw | docker compose exec -T gateway python -

Uses the session id "verify-d" so the matching lines can be found in logs/tool_calls.jsonl.
Prints results only, never a token.
"""

import asyncio
import json
import os

import httpx2
import mcp_types as types
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

URL = "http://gateway:8100/mcp?eg_session=verify-d"


def text(result: object) -> str:
    assert isinstance(result, types.CallToolResult)  # noqa: S101
    block = result.content[0]
    return block.text if isinstance(block, types.TextContent) else ""


async def main() -> None:
    calls = 0
    for role in ("reader", "editor", "admin"):
        headers = {"Authorization": "Bearer " + os.environ[f"GATEWAY_TOKEN_{role.upper()}"]}
        async with (
            httpx2.AsyncClient(headers=headers, timeout=30) as http,
            Client(streamable_http_client(URL, http_client=http)) as client,
        ):
            me = await client.call_tool("raw_api_call", {"method": "GET", "path": "/me"})
            calls += 1
            user = json.loads(text(me))
            print(f"bearer {role} -> EventSim user {user['username']} (role {user['role']})")
            for path in ("/_test/reset", "/_test/export", "/%5Ftest/canaries"):
                got = await client.call_tool("raw_api_call", {"method": "POST", "path": path})
                calls += 1
                print(f"  {role} raw_api_call {path}: is_error={got.is_error} {text(got)[:40]}")
    print(f"tool calls made: {calls}")


asyncio.run(main())
