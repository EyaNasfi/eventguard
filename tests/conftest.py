from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from eventsim.main import create_app
from eventsim.settings import Settings

# Test-only values, never used outside pytest.
TOKENS = {"reader": "t-reader", "editor": "t-editor", "admin": "t-admin"}
TEST_TOKEN = "t-harness"
SEED = 42


def make_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "database_url": "sqlite://",
        "default_seed": SEED,
        "token_reader": SecretStr(TOKENS["reader"]),
        "token_editor": SecretStr(TOKENS["editor"]),
        "token_admin": SecretStr(TOKENS["admin"]),
        "test_token": SecretStr(TEST_TOKEN),
        "test_endpoints": True,
    }
    values.update(overrides)
    return Settings.model_validate(values)


def auth(role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKENS[role]}"}


HARNESS = {"X-Test-Token": TEST_TOKEN}


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app(make_settings())) as c:
        yield c


def as_role(client: TestClient, role: str) -> TestClient:
    """Same app, with the given role's bearer token on every request."""
    client.headers.update(auth(role))
    return client
