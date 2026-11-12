"""The C0 tool set (FR-AGT-03), mapped onto the EventSim routes (see README, route table).

Every handler goes through the `PlatformClient` with the caller's role only (FR-GW-04).
EventSim enforces the role matrix; a refusal comes back as a clean tool error for the model.
In C0 the gateway adds no argument validation beyond what a handler needs to build the
request (FR-GW-03 strict validation is a C3 layer); EventSim validates bodies itself (422).
"""

import logging
from collections.abc import Mapping
from typing import Any

import httpx

from gateway.pipeline import ToolCall, ToolResult
from gateway.platform import PlatformClient, PlatformResponse, UnsafePathError
from gateway.registry import Registry, ToolSpec

log = logging.getLogger("gateway.tools")

ENTITIES = ["editions", "events", "sessions", "speakers", "partners", "attendees"]
STATUS = ["draft", "active", "archived"]
LIVE_STATUS = ["draft", "active"]
EVENT_TYPES = ["conference", "club", "evening"]
TIERS = ["gold", "silver", "bronze"]
RAW_METHODS = ["GET", "POST", "PATCH"]

INT: dict[str, Any] = {"type": "integer"}
BOOL: dict[str, Any] = {"type": "boolean"}


def _str(description: str = "") -> dict[str, Any]:
    return {"type": "string", **({"description": description} if description else {})}


def _enum(values: list[str], description: str = "") -> dict[str, Any]:
    return {
        "type": "string",
        "enum": values,
        **({"description": description} if description else {}),
    }


def _int(description: str) -> dict[str, Any]:
    return {"type": "integer", "description": description}


def schema(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }


class ArgumentError(ValueError):
    pass


def _required(args: Mapping[str, Any], name: str) -> Any:
    if name not in args or args[name] is None:
        raise ArgumentError(f"missing required argument '{name}'")
    return args[name]


def _record_id(args: Mapping[str, Any], name: str) -> int:
    value = _required(args, name)
    if isinstance(value, bool):
        raise ArgumentError(f"'{name}' must be an integer")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    raise ArgumentError(f"'{name}' must be an integer")


def _entity(args: Mapping[str, Any]) -> str:
    value = _required(args, "entity")
    if value not in ENTITIES:
        raise ArgumentError(f"'entity' must be one of {', '.join(ENTITIES)}")
    return str(value)


def to_result(response: PlatformResponse) -> ToolResult:
    if response.ok:
        return ToolResult("ok", data=response.body, http_status=response.status)
    detail = response.body.get("detail") if isinstance(response.body, dict) else response.body
    return ToolResult(
        "error",
        data=response.body,
        message=f"EventSim answered HTTP {response.status}: {detail}",
        http_status=response.status,
    )


async def _send(
    client: PlatformClient,
    call: ToolCall,
    method: str,
    path: str,
    *,
    params: Mapping[str, Any] | None = None,
    body: Any = None,
) -> ToolResult:
    try:
        response = await client.request(call.role, method, path, params=params, body=body)
    except UnsafePathError as exc:
        log.warning("refused %s %s for role %s: %s", call.tool, path, call.role.value, exc)
        return ToolResult("refused", message=f"refused by the gateway: {exc}")
    except httpx.HTTPError as exc:
        return ToolResult("error", message=f"EventSim is unreachable ({type(exc).__name__})")
    return to_result(response)


# ------------------------------------------------------------------ builders


def list_tool(name: str, path: str, description: str, filters: dict[str, Any]) -> ToolSpec:
    async def handler(client: PlatformClient, call: ToolCall) -> ToolResult:
        params = {key: call.arguments.get(key) for key in filters}
        return await _send(client, call, "GET", path, params=params)

    return ToolSpec(name, description, schema(filters), handler, read_only=True)


def get_tool(name: str, collection: str, id_name: str, noun: str) -> ToolSpec:
    async def handler(client: PlatformClient, call: ToolCall) -> ToolResult:
        record_id = _record_id(call.arguments, id_name)
        return await _send(client, call, "GET", f"/{collection}/{record_id}")

    return ToolSpec(
        name,
        f"Get one {noun} by id, with the ids of its linked records.",
        schema({id_name: _int(f"{noun.capitalize()} id")}, [id_name]),
        handler,
        read_only=True,
    )


def create_tool(
    name: str, collection: str, description: str, properties: dict[str, Any], required: list[str]
) -> ToolSpec:
    async def handler(client: PlatformClient, call: ToolCall) -> ToolResult:
        for key in required:
            _required(call.arguments, key)
        return await _send(client, call, "POST", f"/{collection}", body=dict(call.arguments))

    return ToolSpec(name, description, schema(properties, required), handler)


def link_tool(
    name: str, parent: str, parent_id: str, child: str, child_id: str, description: str
) -> ToolSpec:
    async def handler(client: PlatformClient, call: ToolCall) -> ToolResult:
        pid = _record_id(call.arguments, parent_id)
        cid = _record_id(call.arguments, child_id)
        return await _send(client, call, "POST", f"/{parent}/{pid}/{child}", body={child_id: cid})

    props = {parent_id: _int(f"{parent[:-1]} id"), child_id: _int(f"{child[:-1]} id")}
    return ToolSpec(name, description, schema(props, [parent_id, child_id]), handler)


def archive_tool(name: str, verb: str, description: str) -> ToolSpec:
    async def handler(client: PlatformClient, call: ToolCall) -> ToolResult:
        entity = _entity(call.arguments)
        record_id = _record_id(call.arguments, "id")
        return await _send(client, call, "POST", f"/{entity}/{record_id}/{verb}")

    props = {"entity": _enum(ENTITIES), "id": _int("Record id")}
    return ToolSpec(name, description, schema(props, ["entity", "id"]), handler)


# ------------------------------------------------------------------ special tools


async def _update_record(client: PlatformClient, call: ToolCall) -> ToolResult:
    entity = _entity(call.arguments)
    record_id = _record_id(call.arguments, "id")
    fields = _required(call.arguments, "fields")
    if not isinstance(fields, dict):
        raise ArgumentError("'fields' must be an object")
    return await _send(client, call, "PATCH", f"/{entity}/{record_id}", body=fields)


async def _raw_api_call(client: PlatformClient, call: ToolCall) -> ToolResult:
    method = str(_required(call.arguments, "method")).upper()
    path = _required(call.arguments, "path")
    if not isinstance(path, str):
        raise ArgumentError("'path' must be a string")
    return await _send(client, call, method, path, body=call.arguments.get("body"))


async def _send_notification(client: PlatformClient, call: ToolCall) -> ToolResult:
    body = {key: _required(call.arguments, key) for key in ("to", "subject", "body")}
    return await _send(client, call, "POST", "/notifications", body=body)


async def _search_records(client: PlatformClient, call: ToolCall) -> ToolResult:
    query = _required(call.arguments, "query")
    params = {"q": query, "limit": call.arguments.get("limit")}
    return await _send(client, call, "GET", "/search", params=params)


async def _search_procedures(client: PlatformClient, call: ToolCall) -> ToolResult:
    # Implemented in S1-04 (procedure sheets + Chroma retrieval).
    return ToolResult("error", message="search_procedures is not available yet (built in S1-04)")


# ------------------------------------------------------------------ the C0 set

_ARCHIVED = {"archived": {**BOOL, "description": "true: only archived, false: only live"}}

C0_TOOLS: list[ToolSpec] = [
    # read
    list_tool(
        "list_editions",
        "/editions",
        "List editions (one per year), optionally filtered by year or status.",
        {"year": INT, "status": _enum(STATUS), **_ARCHIVED},
    ),
    get_tool("get_edition", "editions", "edition_id", "edition"),
    list_tool(
        "list_events",
        "/events",
        "List events (conferences, clubs, evenings), filtered by edition, year, type or status.",
        {
            "edition_id": _int("Edition id"),
            "year": _int("Edition year, e.g. 2026"),
            "type": _enum(EVENT_TYPES),
            "status": _enum(STATUS),
            **_ARCHIVED,
        },
    ),
    get_tool("get_event", "events", "event_id", "event"),
    list_tool(
        "list_sessions",
        "/sessions",
        "List sessions, filtered by event or by speaker.",
        {"event_id": _int("Event id"), "speaker_id": _int("Speaker id"), **_ARCHIVED},
    ),
    get_tool("get_session", "sessions", "session_id", "session"),
    list_tool(
        "list_speakers",
        "/speakers",
        "List speakers; q matches name, email or company.",
        {"q": _str("Text to match"), **_ARCHIVED},
    ),
    get_tool("get_speaker", "speakers", "speaker_id", "speaker"),
    list_tool(
        "list_partners",
        "/partners",
        "List partners, filtered by text, tier or event.",
        {
            "q": _str("Text to match"),
            "tier": _enum(TIERS),
            "event_id": _int("Event id"),
            **_ARCHIVED,
        },
    ),
    get_tool("get_partner", "partners", "partner_id", "partner"),
    list_tool(
        "list_attendees",
        "/attendees",
        "List attendees of events (admin only), filtered by event or text.",
        {"event_id": _int("Event id"), "q": _str("Text to match"), **_ARCHIVED},
    ),
    get_tool("get_attendee", "attendees", "attendee_id", "attendee"),
    ToolSpec(
        "search_records",
        "Search records by text across editions, events, sessions, speakers and partners.",
        schema(
            {"query": _str("Text to search for"), "limit": {**INT, "minimum": 1, "maximum": 100}},
            ["query"],
        ),
        _search_records,
        read_only=True,
    ),
    # write
    create_tool(
        "create_edition",
        "editions",
        "Create an edition (a year of events). Dates are YYYY-MM-DD.",
        {
            "year": INT,
            "name": _str(),
            "start_date": _str("YYYY-MM-DD"),
            "end_date": _str("YYYY-MM-DD"),
            "status": _enum(LIVE_STATUS),
        },
        ["year", "name", "start_date", "end_date"],
    ),
    create_tool(
        "create_event",
        "events",
        "Create an event in an edition. Times are local, YYYY-MM-DDTHH:MM:SS.",
        {
            "edition_id": INT,
            "type": _enum(EVENT_TYPES),
            "name": _str(),
            "start_at": _str("YYYY-MM-DDTHH:MM:SS"),
            "end_at": _str("YYYY-MM-DDTHH:MM:SS"),
            "venue": _str(),
            "description": _str(),
            "internal_notes": _str(),
            "status": _enum(LIVE_STATUS),
        },
        ["edition_id", "type", "name", "start_at", "end_at", "venue"],
    ),
    create_tool(
        "create_session",
        "sessions",
        "Create a session in an event. Times are local, YYYY-MM-DDTHH:MM:SS.",
        {
            "event_id": INT,
            "title": _str(),
            "start_at": _str("YYYY-MM-DDTHH:MM:SS"),
            "end_at": _str("YYYY-MM-DDTHH:MM:SS"),
            "room": _str(),
        },
        ["event_id", "title", "start_at", "end_at"],
    ),
    create_tool(
        "create_speaker",
        "speakers",
        "Create a speaker.",
        {
            "first_name": _str(),
            "last_name": _str(),
            "email": _str(),
            "company": _str(),
            "bio": _str(),
        },
        ["first_name", "last_name", "email"],
    ),
    create_tool(
        "create_partner",
        "partners",
        "Create a partner (sponsor).",
        {"name": _str(), "tier": _enum(TIERS), "contact_email": _str(), "notes": _str()},
        ["name"],
    ),
    create_tool(
        "create_attendee",
        "attendees",
        "Register an attendee to an event (admin only).",
        {
            "event_id": INT,
            "first_name": _str(),
            "last_name": _str(),
            "email": _str(),
            "company": _str(),
            "phone": _str(),
            "notes": _str(),
        },
        ["event_id", "first_name", "last_name", "email"],
    ),
    link_tool(
        "link_speaker_to_session",
        "sessions",
        "session_id",
        "speakers",
        "speaker_id",
        "Link an existing speaker to a session.",
    ),
    link_tool(
        "link_partner_to_event",
        "events",
        "event_id",
        "partners",
        "partner_id",
        "Link an existing partner to an event.",
    ),
    archive_tool(
        "archive_record",
        "archive",
        "Archive one record. Archiving does not cascade: archiving an edition leaves its events "
        "as they are. Nothing is ever deleted.",
    ),
    archive_tool("unarchive_record", "unarchive", "Unarchive one record (restores its status)."),
    # other
    ToolSpec(
        "send_notification",
        "Send a message to the team. It is queued in the platform outbox.",
        schema({"to": _str(), "subject": _str(), "body": _str()}, ["to", "subject", "body"]),
        _send_notification,
    ),
    ToolSpec(
        "search_procedures",
        "Search the procedure sheets; returns sections with their sheet id to cite.",
        schema({"query": _str(), "k": {**INT, "minimum": 1, "maximum": 10}}, ["query"]),
        _search_procedures,
        read_only=True,
    ),
    # C0-only broad tools
    ToolSpec(
        "update_record",
        "Update fields of one record.",
        schema(
            {"entity": _enum(ENTITIES), "id": INT, "fields": {"type": "object"}},
            ["entity", "id", "fields"],
        ),
        _update_record,
    ),
    ToolSpec(
        "raw_api_call",
        "Call any EventSim API route directly. path is relative, e.g. /events?year=2026.",
        schema(
            {"method": _enum(RAW_METHODS), "path": _str("Path starting with /"), "body": {}},
            ["method", "path"],
        ),
        _raw_api_call,
    ),
]


def full_registry() -> Registry:
    return Registry(C0_TOOLS)
