"""Gateway end to end: MCP client (official SDK) -> gateway HTTP app -> seeded EventSim.

HTTP runs in memory (ASGI transports), not over a socket. Reason: on the development PC the
antivirus intercepts loopback HTTP whose path ends in `/mcp` and breaks the responses (see
docs/environment.md). The in-memory transport exercises the same Starlette app, auth middleware
and Streamable HTTP handler, and behaves the same on Windows and in CI.
"""

import json
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
import httpx2
import mcp_types as types
import pytest
from fastapi.testclient import TestClient
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from pydantic import SecretStr
from starlette.applications import Starlette

from config.loader import resolve
from eventsim.main import create_app as create_eventsim
from eventsim.models import Role
from gateway.platform import EventSimClient
from gateway.server import Gateway, build_app
from gateway.settings import GatewaySettings
from tests.conftest import HARNESS, TOKENS, make_settings

GATEWAY_TOKENS = {"reader": "g-reader", "editor": "g-editor", "admin": "g-admin"}
C0_TOOL_COUNT = 27

pytestmark = pytest.mark.anyio


@pytest.fixture(scope="module")
def anyio_backend() -> str:
    return "asyncio"


BASE = "http://gateway:8100"


class Lab:
    def __init__(self, app: Starlette, eventsim: TestClient, gateway: Gateway) -> None:
        self.app = app
        self.eventsim = eventsim
        self.gateway = gateway

    def http(self, headers: dict[str, str] | None = None) -> httpx2.AsyncClient:
        return httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=self.app),
            base_url=BASE,
            headers=headers or {},
            timeout=30,
        )

    def reset(self) -> None:
        self.eventsim.post("/_test/reset", json={"seed": 42}, headers=HARNESS).raise_for_status()


@pytest.fixture(scope="module")
def eventsim() -> Iterator[TestClient]:
    with TestClient(create_eventsim(make_settings())) as client:  # runs the lifespan: seed 42
        yield client


@pytest.fixture(scope="module")
async def lab(eventsim: TestClient) -> AsyncIterator[Lab]:
    settings = GatewaySettings.model_validate(
        {
            "EVENTSIM_URL": "http://eventsim",
            "EVENTSIM_TOKEN_READER": TOKENS["reader"],
            "EVENTSIM_TOKEN_EDITOR": TOKENS["editor"],
            "EVENTSIM_TOKEN_ADMIN": TOKENS["admin"],
            "GATEWAY_TOKEN_READER": GATEWAY_TOKENS["reader"],
            "GATEWAY_TOKEN_EDITOR": GATEWAY_TOKENS["editor"],
            "GATEWAY_TOKEN_ADMIN": GATEWAY_TOKENS["admin"],
            "EVENTGUARD_CONFIG": "C0",
        }
    )
    platform = EventSimClient(
        "http://eventsim",
        {Role(k): SecretStr(v) for k, v in TOKENS.items()},
        transport=httpx.ASGITransport(app=eventsim.app),
    )
    gateway = Gateway(resolve("C0", env={"GEMINI_MODEL": "test-model"}), platform)
    app = build_app(settings, gateway)
    async with app.router.lifespan_context(app):  # starts the MCP session manager
        yield Lab(app, eventsim, gateway)
    await platform.aclose()


@pytest.fixture
def fresh(lab: Lab) -> Lab:
    lab.reset()
    return lab


@asynccontextmanager
async def connect(lab: Lab, role: str, mode: str = "auto") -> AsyncIterator[Client]:
    headers = {"Authorization": f"Bearer {GATEWAY_TOKENS[role]}"}
    async with lab.http(headers) as http:
        transport = streamable_http_client(f"{BASE}/mcp", http_client=http)
        async with Client(transport, mode=mode) as client:
            yield client


async def call(lab: Lab, role: str, tool: str, args: dict[str, Any]) -> types.CallToolResult:
    async with connect(lab, role) as client:
        result = await client.call_tool(tool, args)
    assert isinstance(result, types.CallToolResult)
    return result


def text(result: types.CallToolResult) -> str:
    block = result.content[0]
    assert isinstance(block, types.TextContent)
    return block.text


def data(result: types.CallToolResult) -> Any:
    assert not result.is_error, text(result)
    return json.loads(text(result))


# ------------------------------------------------------------------ transport + auth


async def test_health_is_public_and_reports_config(lab: Lab) -> None:
    async with lab.http() as http:
        body = (await http.get("/health")).json()
    assert body["status"] == "ok"
    assert body["config"] == "C0"
    assert body["config_hash"] == lab.gateway.config.hash


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer wrong"}, {"Authorization": f"Bearer {TOKENS['admin']}"}],
    ids=["missing", "wrong", "eventsim-token-is-not-a-gateway-token"],
)
async def test_mcp_endpoint_requires_a_gateway_bearer(lab: Lab, headers: dict[str, str]) -> None:
    init = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "probe", "version": "0"},
        },
    }
    async with lab.http() as http:
        response = await http.post(
            "/mcp", json=init, headers={"Accept": "application/json, text/event-stream", **headers}
        )
    assert response.status_code == 401
    assert response.headers["www-authenticate"].startswith("Bearer")


async def test_unknown_host_header_is_rejected(lab: Lab) -> None:
    """DNS-rebinding protection: only the lab host names are accepted."""
    headers = {"Authorization": f"Bearer {GATEWAY_TOKENS['reader']}", "Host": "evil.example:8100"}
    async with lab.http(headers) as http:
        response = await http.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "ping"})
    assert response.status_code == 421


async def test_lists_exactly_the_c0_tools(lab: Lab) -> None:
    async with connect(lab, "reader") as client:
        listed = await client.list_tools()
    names = [tool.name for tool in listed.tools]
    assert names == lab.gateway.config.tools
    assert len(names) == C0_TOOL_COUNT
    for tool in listed.tools:
        assert tool.input_schema["type"] == "object"
        assert tool.input_schema["additionalProperties"] is False
        assert tool.description


async def test_legacy_handshake_clients_work(lab: Lab) -> None:
    """n8n's MCP Client Tool may use the pre-2026 initialize handshake."""
    async with connect(lab, "reader", mode="legacy") as client:
        result = await client.call_tool("get_event", {"event_id": 12})
    assert isinstance(result, types.CallToolResult)
    assert json.loads(text(result))["id"] == 12


# ------------------------------------------------------------------ read tools


@pytest.mark.parametrize(
    ("tool", "args", "check"),
    [
        ("list_editions", {}, lambda d: [e["year"] for e in d] == [2025, 2026, 2027]),
        (
            "get_edition",
            {"edition_id": 2},
            lambda d: d["year"] == 2026 and len(d["event_ids"]) == 11,
        ),
        ("list_events", {"year": 2026, "type": "club"}, lambda d: len(d) == 4),
        ("list_events", {"year": 2026, "archived": True}, lambda d: [e["id"] for e in d] == [22]),
        ("get_event", {"event_id": 12}, lambda d: d["name"] == "People Forum"),
        ("list_sessions", {"event_id": 12}, lambda d: all(s["event_id"] == 12 for s in d) and d),
        ("get_session", {"session_id": 1}, lambda d: "speaker_ids" in d),
        ("list_speakers", {}, lambda d: len(d) == 30),
        ("get_speaker", {"speaker_id": 1}, lambda d: "session_ids" in d),
        ("list_partners", {}, lambda d: len(d) == 12),
        ("get_partner", {"partner_id": 3}, lambda d: "event_ids" in d),
        ("search_records", {"query": "Forum"}, lambda d: d and all("entity" in h for h in d)),
    ],
)
async def test_read_tools_return_eventsim_data(
    fresh: Lab, tool: str, args: dict[str, Any], check: Any
) -> None:
    assert check(data(await call(fresh, "reader", tool, args)))


async def test_attendee_tools_follow_the_role_matrix(fresh: Lab) -> None:
    assert len(data(await call(fresh, "admin", "list_attendees", {}))) == 77
    assert data(await call(fresh, "admin", "get_attendee", {"attendee_id": 1}))["id"] == 1
    refused = await call(fresh, "editor", "list_attendees", {})
    assert refused.is_error
    assert "HTTP 403" in text(refused)


async def test_reader_sees_no_internal_notes(fresh: Lab) -> None:
    assert "internal_notes" not in data(await call(fresh, "reader", "get_event", {"event_id": 16}))
    assert "internal_notes" in data(await call(fresh, "editor", "get_event", {"event_id": 16}))


# ------------------------------------------------------------------ write tools

NEW_EVENT = {
    "edition_id": 3,
    "type": "club",
    "name": "Gateway Test Club",
    "start_at": "2027-05-04T18:00:00",
    "end_at": "2027-05-04T20:00:00",
    "venue": "Salle Test",
}


async def test_reader_cannot_create_and_gets_a_clean_error(fresh: Lab) -> None:
    result = await call(fresh, "reader", "create_event", NEW_EVENT)
    assert result.is_error
    assert text(result).startswith("EventSim answered HTTP 403")
    assert "reader" in text(result)


async def test_editor_creates_in_draft_edition_and_links(fresh: Lab) -> None:
    event = data(await call(fresh, "editor", "create_event", NEW_EVENT))
    assert event["status"] == "draft"
    session = data(
        await call(
            fresh,
            "editor",
            "create_session",
            {
                "event_id": event["id"],
                "title": "Opening",
                "start_at": "2027-05-04T18:00:00",
                "end_at": "2027-05-04T18:30:00",
            },
        )
    )
    speaker = data(
        await call(
            fresh,
            "editor",
            "create_speaker",
            {"first_name": "Test", "last_name": "Speaker", "email": "t.speaker@example.com"},
        )
    )
    partner = data(await call(fresh, "editor", "create_partner", {"name": "Test Partner"}))
    data(
        await call(
            fresh,
            "editor",
            "link_speaker_to_session",
            {"session_id": session["id"], "speaker_id": speaker["id"]},
        )
    )
    data(
        await call(
            fresh,
            "editor",
            "link_partner_to_event",
            {"event_id": event["id"], "partner_id": partner["id"]},
        )
    )
    linked = data(await call(fresh, "reader", "get_event", {"event_id": event["id"]}))
    assert linked["session_ids"] == [session["id"]]
    assert linked["partner_ids"] == [partner["id"]]


async def test_editor_cannot_write_in_active_edition(fresh: Lab) -> None:
    result = await call(fresh, "editor", "create_event", {**NEW_EVENT, "edition_id": 2})
    assert result.is_error
    assert "draft edition" in text(result)


async def test_admin_creates_edition_and_attendee(fresh: Lab) -> None:
    edition = {
        "year": 2028,
        "name": "Edition 2028",
        "start_date": "2028-01-01",
        "end_date": "2028-12-31",
    }
    assert data(await call(fresh, "admin", "create_edition", edition))["status"] == "draft"
    attendee = {"event_id": 12, "first_name": "Ann", "last_name": "Test", "email": "a@example.org"}
    assert data(await call(fresh, "admin", "create_attendee", attendee))["event_id"] == 12


async def test_archive_then_unarchive_restores_status(fresh: Lab) -> None:
    archived = data(await call(fresh, "editor", "archive_record", {"entity": "events", "id": 12}))
    assert archived["status"] == "archived"
    restored = data(await call(fresh, "editor", "unarchive_record", {"entity": "events", "id": 12}))
    assert restored["status"] == "active"


async def test_editor_cannot_archive_an_edition(fresh: Lab) -> None:
    result = await call(fresh, "editor", "archive_record", {"entity": "editions", "id": 1})
    assert result.is_error
    assert "HTTP 403" in text(result)


async def test_update_record_goes_through_eventsim_rules(fresh: Lab) -> None:
    updated = data(
        await call(
            fresh,
            "admin",
            "update_record",
            {"entity": "events", "id": 12, "fields": {"venue": "New Hall"}},
        )
    )
    assert updated["venue"] == "New Hall"
    unknown = await call(
        fresh, "admin", "update_record", {"entity": "events", "id": 12, "fields": {"bogus": 1}}
    )
    assert unknown.is_error
    assert "HTTP 422" in text(unknown)


async def test_send_notification_lands_in_outbox(fresh: Lab) -> None:
    queued = data(
        await call(
            fresh,
            "editor",
            "send_notification",
            {"to": "team@example.org", "subject": "Hi", "body": "x"},
        )
    )
    assert queued["status"] == "queued"
    outbox = fresh.eventsim.get("/_test/outbox", headers=HARNESS).json()
    assert [m["subject"] for m in outbox] == ["Hi"]


async def test_search_procedures_is_declared_but_not_built_yet(fresh: Lab) -> None:
    result = await call(fresh, "reader", "search_procedures", {"query": "duplicate a club"})
    assert result.is_error
    assert "S1-04" in text(result)


async def test_missing_argument_is_a_tool_error_not_a_crash(fresh: Lab) -> None:
    result = await call(fresh, "reader", "get_event", {})
    assert result.is_error
    assert "event_id" in text(result)


async def test_unknown_tool_is_refused(fresh: Lab) -> None:
    result = await call(fresh, "admin", "delete_record", {"entity": "events", "id": 1})
    assert result.is_error


# ------------------------------------------------------------------ raw_api_call and test paths


async def test_raw_api_call_reaches_public_routes(fresh: Lab) -> None:
    events = data(
        await call(fresh, "reader", "raw_api_call", {"method": "GET", "path": "/events?year=2026"})
    )
    assert len(events) == 11


TEST_PATH_SPELLINGS = [
    "/_test/reset",
    "/_test/snapshot",
    "/_test/state-diff",
    "/_TEST/reset",
    "/%5Ftest/reset",
    "/%255Ftest/reset",
    "/%5f%74%65%73%74/reset",
    "/events/../_test/reset",
    "/./_test/export",
    "/_test",
    "/_test?seed=1",
]


@pytest.mark.parametrize("path", TEST_PATH_SPELLINGS)
async def test_raw_api_call_never_reaches_test_endpoints(
    fresh: Lab, path: str, caplog: pytest.LogCaptureFixture
) -> None:
    before = fresh.eventsim.get("/_test/export", headers=HARNESS).json()
    caplog.set_level("WARNING", logger="gateway.tools")
    for method in ("GET", "POST"):
        result = await call(
            fresh, "admin", "raw_api_call", {"method": method, "path": path, "body": {"seed": 1}}
        )
        assert result.is_error
        assert text(result).startswith("refused by the gateway")
    assert "refused raw_api_call" in caplog.text
    assert fresh.eventsim.get("/_test/export", headers=HARNESS).json() == before


@pytest.mark.parametrize(
    "path", ["http://eventsim/_test/reset", "//evil.example/x", "events", "\\_test\\reset"]
)
async def test_raw_api_call_refuses_non_relative_paths(fresh: Lab, path: str) -> None:
    result = await call(fresh, "admin", "raw_api_call", {"method": "GET", "path": path})
    assert result.is_error
    assert text(result).startswith("refused by the gateway")


async def test_no_tool_can_delete(fresh: Lab) -> None:
    result = await call(fresh, "admin", "raw_api_call", {"method": "DELETE", "path": "/events/12"})
    assert result.is_error
    assert "DELETE is not allowed" in text(result)
    assert not [n for n in fresh.gateway.registry.names() if "delete" in n]
    assert data(await call(fresh, "reader", "get_event", {"event_id": 12}))["archived"] is False
