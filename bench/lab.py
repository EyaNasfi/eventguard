"""An in-process EventSim for controls and expected results (no Docker, no network, no Gemini).

Same code and same seed as the lab container, so the reference script's diff here is the
expected diff of a correct agent run there.
"""

from typing import Any

from fastapi.testclient import TestClient
from pydantic import SecretStr

from eventsim.main import create_app
from eventsim.settings import Settings

TOKENS = {"reader": "bench-reader", "editor": "bench-editor", "admin": "bench-admin"}
TEST_TOKEN = "bench-harness"  # noqa: S105 (in-process only; never the lab token)


class RoleClient:
    """What `eventsim.reference` needs (get/post), with one role's bearer on every request."""

    def __init__(self, client: TestClient, role: str) -> None:
        self.client = client
        self.headers = {"Authorization": f"Bearer {TOKENS[role]}"}

    def get(self, url: str, *, params: Any = None) -> Any:
        return self.client.get(url, params=params, headers=self.headers)

    def post(self, url: str, *, json: Any = None) -> Any:
        return self.client.post(url, json=json, headers=self.headers)


class InProcessLab:
    def __init__(self) -> None:
        settings = Settings.model_validate(
            {
                "database_url": "sqlite://",
                "default_seed": 42,
                "token_reader": SecretStr(TOKENS["reader"]),
                "token_editor": SecretStr(TOKENS["editor"]),
                "token_admin": SecretStr(TOKENS["admin"]),
                "test_token": SecretStr(TEST_TOKEN),
                "test_endpoints": True,
            }
        )
        self._cm = TestClient(create_app(settings))
        self.client = self._cm.__enter__()
        self.harness = {"X-Test-Token": TEST_TOKEN}

    def close(self) -> None:
        self._cm.__exit__(None, None, None)

    def as_role(self, role: str) -> RoleClient:
        return RoleClient(self.client, role)

    def start(self, seed: int) -> None:
        """Reset to the seed and take the snapshot the diff is measured from."""
        self.client.post(
            "/_test/reset", json={"seed": seed}, headers=self.harness
        ).raise_for_status()
        self.client.post("/_test/snapshot", headers=self.harness).raise_for_status()

    def diff(self) -> dict[str, Any]:
        r = self.client.get("/_test/state-diff", headers=self.harness)
        tables: dict[str, Any] = r.raise_for_status().json()["tables"]
        return tables

    def export(self) -> dict[str, Any]:
        result: dict[str, Any] = self.client.get("/_test/export", headers=self.harness).json()
        return result

    def outbox(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = self.client.get("/_test/outbox", headers=self.harness).json()
        return result
