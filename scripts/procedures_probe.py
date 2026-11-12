"""Live check of search_procedures through the gateway (manual test guide, L16).

    Get-Content scripts\\procedures_probe.py -Raw | docker compose exec -T gateway python -

Real MCP client -> gateway -> retriever (Gemini query embedding) -> vector store. One Gemini
embedding call per query. Prints sheet ids and sections only, never a token.
"""

import asyncio
import json
import os

import httpx2
import mcp_types as types
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

URL = "http://gateway:8100/mcp"
QUERIES = {
    "How do I duplicate a club?": "PROC-03",
    "archive a whole edition": "PROC-10",
    "who can read attendees?": "PROC-14",
}


async def main() -> None:
    headers = {"Authorization": "Bearer " + os.environ["GATEWAY_TOKEN_READER"]}
    passed = 0
    async with (
        httpx2.AsyncClient(headers=headers, timeout=60) as http,
        Client(streamable_http_client(URL, http_client=http)) as client,
    ):
        if True:  # keeps the loop body's indentation readable
            for query, expected in QUERIES.items():
                result = await client.call_tool("search_procedures", {"query": query})
                assert isinstance(result, types.CallToolResult)  # noqa: S101
                block = result.content[0]
                text = block.text if isinstance(block, types.TextContent) else ""
                if result.is_error:
                    print(f"{query!r} -> error: {text}")
                    continue
                hits = json.loads(text)
                ids = [h["sheet_id"] for h in hits]
                ok = expected in ids
                passed += ok
                sources = {h["source"] for h in hits}
                print(
                    f"{query!r} -> {[f'{h["sheet_id"]}/{h["section"]}' for h in hits]} "
                    f"source={sorted(sources)} expected {expected}: {'PASS' if ok else 'FAIL'}"
                )
    print(f"{passed}/{len(QUERIES)} queries found the expected sheet")


asyncio.run(main())
