"""MCP authentication (SR-14): each bearer token maps to exactly one EventSim role (FR-GW-04).

The verifier plugs into the MCP SDK's `BearerAuthBackend`; a missing or unknown token never
reaches a tool (the SDK answers 401).
"""

import hmac
from collections.abc import Mapping

from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken
from pydantic import SecretStr

from eventsim.models import Role

CLIENT_PREFIX = "eventguard-"


class StaticTokenVerifier:
    """Fixed bearer tokens from `.env`, compared in constant time."""

    def __init__(self, tokens: Mapping[Role, SecretStr]) -> None:
        values = [secret.get_secret_value() for secret in tokens.values()]
        if any(not value for value in values):
            raise ValueError("every role needs a non-empty gateway token")
        if len(set(values)) != len(values):
            raise ValueError("gateway tokens must be distinct, one per role")
        self._tokens = {role: secret.get_secret_value().encode() for role, secret in tokens.items()}

    async def verify_token(self, token: str) -> AccessToken | None:
        presented = token.encode()
        match: Role | None = None
        for role, expected in self._tokens.items():
            # No early exit: every comparison runs, whichever role matches.
            if hmac.compare_digest(presented, expected):
                match = role
        if match is None:
            return None
        return AccessToken(
            token="redacted",  # noqa: S106 (placeholder: the raw token is not kept)
            client_id=CLIENT_PREFIX + match.value,
            scopes=[match.value],
            subject=match.value,
        )


def role_of(user: object) -> Role | None:
    """Role carried by the authenticated MCP request, or None."""
    if not isinstance(user, AuthenticatedUser):
        return None
    subject = user.access_token.subject
    try:
        return Role(subject) if subject else None
    except ValueError:
        return None
