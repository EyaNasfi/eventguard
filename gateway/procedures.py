"""`search_procedures` (S2-03, FR-AGT-04): the gateway asks the internal retriever service.

The gateway holds no Gemini key and has no internet access; the retriever embeds the query.
Every hit carries `source: "procedure_sheet"`, which marks the text as untrusted content for
spotlighting in a later configuration.
"""

from typing import Any, Protocol

import httpx

from gateway.pipeline import ToolCall, ToolResult
from gateway.platform import PlatformClient


class ProcedureSearch(Protocol):
    async def search(self, query: str, k: int) -> list[dict[str, Any]]: ...


class RetrieverClient:
    def __init__(self, base_url: str, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.http = httpx.AsyncClient(base_url=base_url, timeout=30, transport=transport)

    async def search(self, query: str, k: int) -> list[dict[str, Any]]:
        r = await self.http.post("/search", json={"query": query, "k": k})
        r.raise_for_status()
        hits: list[dict[str, Any]] = r.json()["hits"]
        return hits

    async def aclose(self) -> None:
        await self.http.aclose()


FIELDS = ("sheet_id", "title", "section", "text", "source")


def make_handler(procedures: ProcedureSearch, k_default: int) -> Any:
    async def handler(_: PlatformClient, call: ToolCall) -> ToolResult:
        query = call.arguments.get("query")
        if not isinstance(query, str) or not query.strip():
            return ToolResult("error", message="missing required argument 'query'")
        k = call.arguments.get("k", k_default)
        if not isinstance(k, int) or not 1 <= k <= 10:
            return ToolResult("error", message="argument 'k' must be an integer from 1 to 10")
        try:
            hits = await procedures.search(query.strip(), k)
        except httpx.HTTPError as exc:
            return ToolResult(
                "error", message=f"procedure search unavailable: {type(exc).__name__}"
            )
        data = [{f: hit.get(f) for f in FIELDS} | {"source": "procedure_sheet"} for hit in hits]
        return ToolResult("ok", data=data)

    return handler
