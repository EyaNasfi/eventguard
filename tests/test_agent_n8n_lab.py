"""agent/n8n_lab.py against a fake n8n API (no network)."""

import json
from typing import Any

import httpx
import pytest

from agent.n8n_lab import GATEWAY_CREDENTIAL, N8n, create_lab_credentials


class FakeN8n:
    def __init__(self) -> None:
        self.creds: dict[str, dict[str, Any]] = {}
        self.workflows: dict[str, dict[str, Any]] = {}
        self.active: set[str] = set()
        self.next_id = 1

    def handler(self, request: httpx.Request) -> httpx.Response:
        path, method = request.url.path.removeprefix("/api/v1"), request.method
        assert request.headers["X-N8N-API-KEY"] == "k"
        if path == "/credentials" and method == "GET":
            rows = [{"id": i, "name": c["name"]} for i, c in self.creds.items()]
            return httpx.Response(200, json={"data": rows})
        if path == "/credentials" and method == "POST":
            cid = str(self.next_id)
            self.next_id += 1
            self.creds[cid] = json.loads(request.content)
            return httpx.Response(200, json={"id": cid})
        if path.startswith("/credentials/") and method == "DELETE":
            self.creds.pop(path.split("/")[-1])
            return httpx.Response(200, json={})
        if path == "/workflows" and method == "GET":
            rows = [{"id": i, "name": w["name"]} for i, w in self.workflows.items()]
            return httpx.Response(200, json={"data": rows})
        if path == "/workflows" and method == "POST":
            wid = f"w{self.next_id}"
            self.next_id += 1
            self.workflows[wid] = json.loads(request.content)
            return httpx.Response(200, json={"id": wid})
        if path.startswith("/workflows/") and method == "PUT":
            self.workflows[path.split("/")[2]] = json.loads(request.content)
            return httpx.Response(200, json={})
        if path.endswith("/activate"):
            self.active.add(path.split("/")[2])
            return httpx.Response(200, json={})
        if path.endswith("/deactivate"):
            self.active.discard(path.split("/")[2])
            return httpx.Response(200, json={})
        return httpx.Response(404)


@pytest.fixture
def fake() -> tuple[FakeN8n, N8n]:
    server = FakeN8n()
    return server, N8n("http://n8n", "k", transport=httpx.MockTransport(server.handler))


ENV = {
    "GATEWAY_TOKEN_READER": "r",
    "GATEWAY_TOKEN_EDITOR": "e",
    "GATEWAY_TOKEN_ADMIN": "a",
    "GEMINI_API_KEY": "g",
}


def test_credentials_are_replaced_not_duplicated(fake: tuple[FakeN8n, N8n]) -> None:
    server, client = fake
    create_lab_credentials(client, ENV)
    create_lab_credentials(client, ENV)
    names = sorted(c["name"] for c in server.creds.values())
    assert len(names) == 4 and len(set(names)) == 4
    editor = next(c for c in server.creds.values() if "editor" in c["name"])
    assert editor["type"] == "httpBearerAuth" and editor["data"] == {"token": "e"}


def test_import_maps_credential_names_and_activates(fake: tuple[FakeN8n, N8n]) -> None:
    server, client = fake
    ids = create_lab_credentials(client, ENV)
    name = GATEWAY_CREDENTIAL.format(role="reader")
    workflow = {
        "name": "wf",
        "nodes": [{"name": "MCP", "credentials": {"httpBearerAuth": {"name": name}}}],
        "connections": {},
    }
    wid = client.import_workflow(workflow)
    stored = server.workflows[wid]["nodes"][0]["credentials"]["httpBearerAuth"]
    assert stored == {"id": ids[name], "name": name}
    assert wid in server.active
    assert client.import_workflow(workflow) == wid  # second import updates in place
    assert len(server.workflows) == 1


def test_missing_credential_stops_the_import(fake: tuple[FakeN8n, N8n]) -> None:
    _, client = fake
    workflow = {
        "name": "wf",
        "nodes": [{"name": "MCP", "credentials": {"httpBearerAuth": {"name": "nope"}}}],
        "connections": {},
    }
    with pytest.raises(SystemExit):
        client.import_workflow(workflow)


def test_missing_env_value_stops(fake: tuple[FakeN8n, N8n]) -> None:
    _, client = fake
    with pytest.raises(SystemExit):
        create_lab_credentials(client, {**ENV, "GEMINI_API_KEY": ""})
