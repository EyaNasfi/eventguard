"""Gateway MCP server: official MCP Python SDK (mcp 2.x, low-level `Server`), Streamable HTTP.

The low-level server is used rather than `MCPServer` (the v2 name of FastMCP) because tools are
declared as data in the registry (name, description, JSON schema), not derived from Python
signatures (SR-10). Bearer authentication uses the SDK's `BearerAuthBackend` (SR-14).
"""

import json
import logging
import os
from typing import Any

import mcp_types as types
from mcp.server import Server, ServerRequestContext
from mcp.server.auth.settings import AuthSettings
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from config.loader import ResolvedConfig, resolve
from gateway.identity import StaticTokenVerifier, role_of
from gateway.pipeline import Pipeline, ToolCall, ToolResult, build_pipeline
from gateway.platform import EventSimClient, PlatformClient
from gateway.registry import Registry
from gateway.settings import GatewaySettings
from gateway.tools import ArgumentError, full_registry

log = logging.getLogger("gateway")


def _content(result: ToolResult) -> str:
    if result.outcome == "ok":
        return json.dumps(result.data, ensure_ascii=False, default=str)
    return result.message or result.outcome


class Gateway:
    """Holds the per-configuration state: tool selection, pipeline, platform client."""

    def __init__(self, config: ResolvedConfig, platform: PlatformClient) -> None:
        self.config = config
        self.platform = platform
        self.registry: Registry = full_registry().select(config.tools)
        self.pipeline: Pipeline = build_pipeline(config.layers)

    def list_tools(self) -> list[types.Tool]:
        tools = []
        for name in self.registry.names():
            spec = self.registry.get(name)
            assert spec is not None  # noqa: S101 (names() comes from the registry)
            tools.append(
                types.Tool(
                    name=spec.name,
                    description=spec.description,
                    input_schema=spec.input_schema,
                    annotations=types.ToolAnnotations(read_only_hint=spec.read_only),
                )
            )
        return tools

    async def call(self, role: Any, name: str, arguments: dict[str, Any]) -> ToolResult:
        spec = self.registry.get(name)
        if spec is None:
            return ToolResult("refused", message=f"unknown tool '{name}' in configuration")
        call = ToolCall(
            tool=name,
            arguments=arguments,
            role=role,
            config_name=self.config.name,
            config_hash=self.config.hash,
        )

        async def handler(c: ToolCall) -> ToolResult:
            try:
                return await spec.handler(self.platform, c)
            except ArgumentError as exc:
                return ToolResult("error", message=str(exc))

        return await self.pipeline.run(call, handler)


def build_server(gateway: Gateway) -> Server[Any]:
    async def on_list_tools(
        ctx: ServerRequestContext[Any], params: types.PaginatedRequestParams | None
    ) -> types.ListToolsResult:
        return types.ListToolsResult(tools=gateway.list_tools())

    async def on_call_tool(
        ctx: ServerRequestContext[Any], params: types.CallToolRequestParams
    ) -> types.CallToolResult:
        role = role_of(getattr(ctx.request, "user", None))
        if role is None:  # unreachable behind RequireAuthMiddleware; kept as a guard
            result = ToolResult("refused", message="no authenticated user on this request")
        else:
            result = await gateway.call(role, params.name, dict(params.arguments or {}))
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=_content(result))],
            is_error=result.outcome != "ok",
        )

    return Server(
        "eventguard-gateway",
        version="0.1.0",
        instructions="Tools for the EventSim event platform (EventGuard lab).",
        on_list_tools=on_list_tools,
        on_call_tool=on_call_tool,
    )


def build_app(settings: GatewaySettings, gateway: Gateway) -> Starlette:
    server = build_server(gateway)

    async def health(_: Request) -> JSONResponse:
        return JSONResponse(
            {"status": "ok", "config": gateway.config.name, "config_hash": gateway.config.hash}
        )

    base = f"http://{settings.allowed_hosts[0].split(':')[0]}:{settings.port}"
    return server.streamable_http_app(
        streamable_http_path=settings.mcp_path,
        stateless_http=True,
        host=settings.host,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=settings.allowed_hosts,
            allowed_origins=[f"http://{h}" for h in settings.allowed_hosts],
        ),
        # Resource-server-only setup: static bearer tokens, no OAuth endpoints, no metadata route.
        auth=AuthSettings.model_validate({"issuer_url": base, "resource_server_url": None}),
        token_verifier=StaticTokenVerifier(settings.gateway_tokens()),
        custom_starlette_routes=[Route("/health", health)],
    )


def create_app() -> Starlette:
    """uvicorn --factory gateway.server:create_app"""
    settings = GatewaySettings()
    config = resolve(settings.config_name, env=dict(os.environ))
    platform = EventSimClient(settings.eventsim_url, settings.eventsim_tokens())
    gateway = Gateway(config, platform)
    log.info(
        "gateway up: config %s (%s), %d tools, tool descriptions sha256 %s",
        config.name,
        config.hash[:12],
        len(gateway.registry.names()),
        gateway.registry.descriptions_hash()[:12],
    )
    return build_app(settings, gateway)
