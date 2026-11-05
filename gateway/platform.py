"""The platform client: the only code in the gateway that talks HTTP to EventSim.

`PlatformClient` is the seam a future inwink connector would implement instead (NFR-10).
`EventSimClient` holds one EventSim token per role and sends only the caller's (FR-GW-04).
"""

import posixpath
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import unquote, urlsplit

import httpx
from pydantic import SecretStr

from eventsim.models import Role

ALLOWED_METHODS = frozenset({"GET", "POST", "PATCH"})  # no DELETE anywhere
TEST_PREFIX = "_test"


class UnsafePathError(ValueError):
    """The path is not a plain EventSim API path, or it targets the test harness."""


@dataclass(frozen=True)
class PlatformResponse:
    status: int
    body: Any

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


class PlatformClient(Protocol):
    async def request(
        self,
        role: Role,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        body: Any = None,
    ) -> PlatformResponse: ...


def normalise_path(raw: str) -> tuple[str, str]:
    """Return (path, query) after decoding and dot-segment removal.

    The caller checks and sends this normalised form, so what is checked is what is sent.
    Raises UnsafePathError for anything that is not a relative API path.
    """
    if not isinstance(raw, str) or not raw.startswith("/") or raw.startswith("//"):
        raise UnsafePathError("path must start with a single '/'")
    decoded = raw
    for _ in range(5):  # undo nested percent-encoding (%255F -> %5F -> _)
        step = unquote(decoded)
        if step == decoded:
            break
        decoded = step
    else:
        raise UnsafePathError("path is encoded too many times")
    if "\\" in decoded or any(ord(ch) < 0x20 for ch in decoded):
        raise UnsafePathError("path contains a backslash or a control character")
    parts = urlsplit(decoded)
    if parts.scheme or parts.netloc:
        raise UnsafePathError("absolute URLs are not allowed, give a path only")
    path = posixpath.normpath(parts.path)
    if path.startswith("//"):
        path = "/" + path.lstrip("/")
    return path, parts.query


def is_test_path(path: str) -> bool:
    """True for any path under the EventSim test harness (/_test...), however it is spelled."""
    first = path.lstrip("/").split("/", 1)[0].strip().casefold()
    return first.startswith(TEST_PREFIX)


class EventSimClient:
    def __init__(
        self,
        base_url: str,
        tokens: Mapping[Role, SecretStr],
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 15.0,
    ) -> None:
        self._tokens = dict(tokens)
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"), transport=transport, timeout=timeout
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def request(
        self,
        role: Role,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        body: Any = None,
    ) -> PlatformResponse:
        verb = method.upper()
        if verb not in ALLOWED_METHODS:
            raise UnsafePathError(f"method {verb} is not allowed")
        clean, query = normalise_path(path)
        if is_test_path(clean):  # hard rule, every configuration (FR-SIM-06)
            raise UnsafePathError("EventSim test endpoints are never reachable from the gateway")
        url = clean + (f"?{query}" if query else "")
        token = self._tokens[role].get_secret_value()
        response = await self._http.request(
            verb,
            url,
            params={k: v for k, v in (params or {}).items() if v is not None} or None,
            json=body if verb != "GET" else None,
            headers={"Authorization": f"Bearer {token}"},
        )
        try:
            payload: Any = response.json()
        except ValueError:
            payload = response.text
        return PlatformResponse(status=response.status_code, body=payload)
