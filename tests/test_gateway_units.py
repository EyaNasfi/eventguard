"""Unit tests for the gateway guard rails that the end-to-end tests do not reach."""

from typing import Any

import httpx
import pytest
from pydantic import SecretStr
from starlette.applications import Starlette

from config.loader import Layers, resolve
from eventsim.models import Role
from gateway.identity import StaticTokenVerifier, role_of
from gateway.pipeline import ToolCall, ToolResult, build_pipeline
from gateway.platform import EventSimClient, UnsafePathError, is_test_path, normalise_path
from gateway.registry import Registry, ToolSpec
from gateway.server import create_app
from gateway.tools import C0_TOOLS, full_registry

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _layers(**on: bool) -> Layers:
    values = dict.fromkeys(Layers.model_fields, False)
    values.update(on)
    return Layers.model_validate(values)


def test_c0_pipeline_is_empty() -> None:
    assert build_pipeline(_layers()).layers == []


def test_a_layer_switched_on_without_implementation_stops_start_up() -> None:
    with pytest.raises(RuntimeError, match="output_filter"):
        build_pipeline(_layers(output_filter=True))


class _Refuser:
    name = "refuser"

    def __init__(self) -> None:
        self.after_calls = 0

    async def before_call(self, call: ToolCall) -> ToolResult | None:
        return ToolResult("refused", message="stopped") if call.tool == "blocked" else None

    async def after_call(self, call: ToolCall, result: ToolResult) -> ToolResult:
        self.after_calls += 1
        return result


async def test_pipeline_runs_layers_and_can_stop_a_call() -> None:
    from gateway.pipeline import Pipeline

    layer = _Refuser()
    pipeline = Pipeline([layer])

    async def handler(call: ToolCall) -> ToolResult:
        return ToolResult("ok", data=call.tool)

    def make(tool: str) -> ToolCall:
        return ToolCall(tool, {}, Role.reader, "C0", "h")

    assert (await pipeline.run(make("fine"), handler)).data == "fine"
    assert (await pipeline.run(make("blocked"), handler)).outcome == "refused"
    assert layer.after_calls == 2


def test_registry_rejects_duplicates_and_unknown_names() -> None:
    spec = C0_TOOLS[0]
    with pytest.raises(ValueError, match="duplicate"):
        Registry([spec, spec])
    with pytest.raises(ValueError, match="unknown tool"):
        full_registry().select(["get_event", "delete_everything"])


def test_registry_selection_keeps_config_order_and_hash_is_stable() -> None:
    registry = full_registry()
    selected = registry.select(["get_event", "list_events"])
    assert selected.names() == ["get_event", "list_events"]
    assert "get_event" in selected and "raw_api_call" not in selected
    assert registry.descriptions_hash() == full_registry().descriptions_hash()
    assert selected.descriptions_hash() != registry.descriptions_hash()


def test_changing_a_description_changes_the_hash() -> None:
    first = C0_TOOLS[0]
    changed = ToolSpec(first.name, first.description + " ", first.input_schema, first.handler)
    assert Registry([first]).descriptions_hash() != Registry([changed]).descriptions_hash()


def test_every_c0_config_tool_exists_in_the_registry() -> None:
    config = resolve("C0", env={"GEMINI_MODEL": "m"})
    assert full_registry().select(config.tools).names() == config.tools


@pytest.mark.parametrize(
    "tokens",
    [
        {Role.reader: "", Role.editor: "b", Role.admin: "c"},
        {Role.reader: "same", Role.editor: "same", Role.admin: "c"},
    ],
    ids=["empty", "duplicate"],
)
def test_verifier_needs_distinct_non_empty_tokens(tokens: dict[Role, str]) -> None:
    with pytest.raises(ValueError):
        StaticTokenVerifier({r: SecretStr(v) for r, v in tokens.items()})


async def test_verifier_maps_each_token_to_its_role() -> None:
    verifier = StaticTokenVerifier({r: SecretStr(f"tok-{r.value}") for r in Role})
    for role in Role:
        token = await verifier.verify_token(f"tok-{role.value}")
        assert token is not None and token.subject == role.value and token.token == "redacted"
    assert await verifier.verify_token("tok-") is None
    assert role_of(object()) is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("/events?year=2026", ("/events", "year=2026")),
        ("/events/../speakers", ("/speakers", "")),
        ("/a/./b/", ("/a/b", "")),
        # decodes to ///host/x: no netloc, collapsed to a plain path on EventSim (no SSRF)
        ("/%2F%2Fhost/x", ("/host/x", "")),
    ],
)
def test_normalise_path(raw: str, expected: tuple[str, str]) -> None:
    assert normalise_path(raw) == expected


@pytest.mark.parametrize(
    "raw", ["/%25252525255Ftest", "/a\x00b", "/a\\b", "x", "//host/x", "/%2Fhost/x"]
)
def test_normalise_path_rejects(raw: str) -> None:
    with pytest.raises(UnsafePathError):
        normalise_path(raw)


@pytest.mark.parametrize(
    ("path", "denied"),
    [
        ("/_test", True),
        ("/_Test/x", True),
        ("/_testing", True),
        ("/events", False),
        ("/x/_test", False),
    ],
)
def test_is_test_path(path: str, denied: bool) -> None:
    assert is_test_path(path) is denied


async def test_client_refuses_test_paths_and_delete_even_when_called_directly() -> None:
    sent: list[str] = []

    def record(request: httpx.Request) -> httpx.Response:
        sent.append(str(request.url))
        return httpx.Response(200, json={})

    client = EventSimClient(
        "http://eventsim", {r: SecretStr("t") for r in Role}, transport=httpx.MockTransport(record)
    )
    with pytest.raises(UnsafePathError):
        await client.request(Role.admin, "POST", "/%5Ftest/reset")
    with pytest.raises(UnsafePathError):
        await client.request(Role.admin, "DELETE", "/events/1")
    assert sent == []
    await client.aclose()


async def test_client_sends_only_the_callers_token_and_handles_text_bodies() -> None:
    seen: dict[str, Any] = {}

    def record(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["authorization"]
        return httpx.Response(500, text="boom")

    tokens = {r: SecretStr(f"es-{r.value}") for r in Role}
    client = EventSimClient("http://eventsim", tokens, transport=httpx.MockTransport(record))
    response = await client.request(Role.editor, "GET", "/events", params={"year": None})
    assert seen["auth"] == "Bearer es-editor"
    assert (response.status, response.body, response.ok) == (500, "boom", False)
    await client.aclose()


async def test_unreachable_eventsim_is_a_tool_error() -> None:
    from gateway.server import Gateway

    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    platform = EventSimClient(
        "http://eventsim", {r: SecretStr("t") for r in Role}, transport=httpx.MockTransport(down)
    )
    gateway = Gateway(resolve("C0", env={"GEMINI_MODEL": "m"}), platform)
    result = await gateway.call(Role.reader, "list_editions", {})
    assert result.outcome == "error"
    assert "unreachable" in (result.message or "")
    await platform.aclose()


def test_create_app_reads_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    env = {
        "EVENTSIM_TOKEN_READER": "a",
        "EVENTSIM_TOKEN_EDITOR": "b",
        "EVENTSIM_TOKEN_ADMIN": "c",
        "GATEWAY_TOKEN_READER": "g1",
        "GATEWAY_TOKEN_EDITOR": "g2",
        "GATEWAY_TOKEN_ADMIN": "g3",
        "EVENTGUARD_CONFIG": "C0",
        "GEMINI_MODEL": "m",
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    assert isinstance(create_app(), Starlette)
