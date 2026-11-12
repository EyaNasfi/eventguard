"""S2-02 identity spike: what can n8n's MCP nodes send to the gateway?

Needs the lab running (eventsim, gateway, n8n), N8N_API_KEY in .env, and for the header probe a
throwaway echo server reachable as http://echo:9000 on the internal network (see the sprint log).

1. Real call: webhook -> MCP Client node (bearer = editor gateway token) -> gateway
   -> get_event(12) on EventSim. Proves n8n -> gateway -> EventSim with a real n8n node.
2. Header probe: the same node aimed at the echo server, with
   - a session value in the endpoint URL query (node parameters accept expressions),
   - a Multiple Headers credential whose value is an expression ({{ $execution.id }}).
   The echo server's log shows what n8n really sends (Authorization redacted there).

Prints no secret. Spike workflows are named "EG spike: ..." and are not exported.
"""

import sys
import uuid
from typing import Any

import httpx

from agent.n8n_lab import GATEWAY_CREDENTIAL, client_from_env, create_lab_credentials, load_env

SPIKE_HEADERS_CREDENTIAL = "EG spike: headers probe"


def mcp_node(name: str, url: str, auth: str, cred_type: str, cred_name: str) -> dict[str, Any]:
    return {
        "name": name,
        "type": "@n8n/n8n-nodes-langchain.mcpClient",
        "typeVersion": 1.1,
        "position": [400, 0],
        "parameters": {
            "endpointUrl": url,
            "authentication": auth,
            "tool": {"__rl": True, "mode": "id", "value": "get_event"},
            "inputMode": "json",
            "jsonInput": '{"event_id": 12}',
            "options": {},
        },
        "credentials": {cred_type: {"name": cred_name}},
    }


def webhook_workflow(name: str, path: str, node: dict[str, Any]) -> dict[str, Any]:
    hook = {
        "name": "Webhook",
        "type": "n8n-nodes-base.webhook",
        "typeVersion": 2,
        "position": [0, 0],
        "webhookId": str(uuid.uuid5(uuid.NAMESPACE_URL, path)),
        "parameters": {"httpMethod": "POST", "path": path, "responseMode": "lastNode"},
    }
    return {
        "name": name,
        "nodes": [hook, node],
        "connections": {
            "Webhook": {"main": [[{"node": node["name"], "type": "main", "index": 0}]]}
        },
        "settings": {"executionOrder": "v1"},
    }


def main() -> int:
    env = load_env()
    n8n = client_from_env(env)
    create_lab_credentials(n8n, env)
    n8n.put_credential(
        SPIKE_HEADERS_CREDENTIAL,
        "httpMultipleHeadersAuth",
        {
            "headers": {
                "values": [
                    {"name": "X-EG-Session", "value": "={{ $execution.id }}"},
                    {"name": "X-EG-Static", "value": "static-marker"},
                ]
            }
        },
    )
    real = webhook_workflow(
        "EG spike: gateway call",
        "eg-spike-gateway",
        mcp_node(
            "MCP Client",
            "http://gateway:8100/mcp",
            "bearerAuth",
            "httpBearerAuth",
            GATEWAY_CREDENTIAL.format(role="editor"),
        ),
    )
    probe = webhook_workflow(
        "EG spike: header probe",
        "eg-spike-probe",
        mcp_node(
            "MCP Client",
            "=http://echo:9000/mcp?eg_session={{ $json.body.session }}",
            "multipleHeadersAuth",
            "httpMultipleHeadersAuth",
            SPIKE_HEADERS_CREDENTIAL,
        ),
    )
    for wf in (real, probe):
        print(f"imported '{wf['name']}' -> id {n8n.import_workflow(wf)}")

    base = env.get("N8N_URL", "http://127.0.0.1:5678")
    with httpx.Client(timeout=60) as http:
        r = http.post(f"{base}/webhook/eg-spike-gateway", json={})
        print("real call:", r.status_code, r.text[:400])
        r = http.post(f"{base}/webhook/eg-spike-probe", json={"session": "chat-session-123"})
        print("header probe (expected to fail, echo is not MCP):", r.status_code, r.text[:200])
    return 0


if __name__ == "__main__":
    sys.exit(main())
