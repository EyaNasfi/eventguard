"""Generate the C0 agent workflows, one per role, from a single template (ADR-005, S2-04).

    python -m agent.workflows.generate          # writes agent/workflows/c0-<role>.json
    python -m agent.n8n_lab import agent/workflows/c0-*.json

Chat Trigger -> AI Agent, with Google Gemini Chat Model, Simple Memory keyed on the chat
session, and the MCP Client Tool pointed at the gateway with that role's bearer credential.

The files hold no secret and no credential id: credentials are referenced by name, and two
placeholders are filled at import time from `.env` (`agent.n8n_lab.render`):
`__GEMINI_MODEL__` and `__EG_SYSTEM_PROMPT_CANARY__` (SR-12, a fake marker, not a secret).
"""

import json
import uuid
from pathlib import Path
from typing import Any

from agent.n8n_lab import GATEWAY_CREDENTIAL, GEMINI_CREDENTIAL, ROLES
from config.loader import read_file

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PROMPT_FILE = ROOT / "agent" / "prompts" / "c0_system.md"
TRIGGER = "When chat message received"
NAMESPACE = uuid.UUID("6f1d8a52-2b7e-4c1c-9a35-3f4d2b9e0c11")  # fixed: stable webhook URLs


def webhook_id(role: str) -> str:
    return str(uuid.uuid5(NAMESPACE, f"eventguard-c0-{role}"))


def chat_url(role: str, base: str = "http://localhost:5678") -> str:
    return f"{base}/webhook/{webhook_id(role)}/chat"


def workflow(role: str) -> dict[str, Any]:
    model = read_file().model
    system = PROMPT_FILE.read_text(encoding="utf-8").strip()
    nodes: list[dict[str, Any]] = [
        {
            "name": TRIGGER,
            "type": "@n8n/n8n-nodes-langchain.chatTrigger",
            "typeVersion": 1.4,
            "position": [0, 0],
            "webhookId": webhook_id(role),
            "parameters": {
                "public": True,
                "mode": "webhook",
                "authentication": "none",
                "options": {"responseMode": "lastNode"},
            },
        },
        {
            "name": "AI Agent",
            "type": "@n8n/n8n-nodes-langchain.agent",
            "typeVersion": 3.1,
            "position": [260, 0],
            # No node-level retry: it would restart the whole agent and repeat writes.
            "parameters": {
                "options": {
                    "systemMessage": system,
                    "maxIterations": 40,
                    "returnIntermediateSteps": True,
                }
            },
        },
        {
            "name": "Google Gemini Chat Model",
            "type": "@n8n/n8n-nodes-langchain.lmChatGoogleGemini",
            "typeVersion": 1,
            "position": [140, 220],
            "parameters": {
                "modelName": "models/__GEMINI_MODEL__",
                "options": {
                    "temperature": model.temperature,
                    "maxOutputTokens": model.max_output_tokens,
                },
            },
            "credentials": {"googlePalmApi": {"name": GEMINI_CREDENTIAL}},
        },
        {
            "name": "Simple Memory",
            "type": "@n8n/n8n-nodes-langchain.memoryBufferWindow",
            "typeVersion": 1.3,
            "position": [300, 220],
            "parameters": {"sessionIdType": "fromInput", "contextWindowLength": 10},
        },
        {
            "name": "EventGuard gateway",
            "type": "@n8n/n8n-nodes-langchain.mcpClientTool",
            "typeVersion": 1.4,
            "position": [460, 220],
            "parameters": {
                "serverTransport": "httpStreamable",
                # The session id labels gateway log lines (ADR-005); identity is the bearer only.
                "endpointUrl": (
                    "=http://gateway:8100/mcp?eg_session="
                    f"{{{{ $('{TRIGGER}').item.json.sessionId }}}}"
                ),
                "authentication": "bearerAuth",
                "include": "all",
                "options": {"timeout": 60000},
            },
            "credentials": {"httpBearerAuth": {"name": GATEWAY_CREDENTIAL.format(role=role)}},
        },
    ]

    def link(kind: str, target: str = "AI Agent") -> dict[str, list[list[dict[str, Any]]]]:
        return {kind: [[{"node": target, "type": kind, "index": 0}]]}

    return {
        "name": f"EventGuard C0 agent ({role})",
        "nodes": nodes,
        "connections": {
            TRIGGER: link("main"),
            "Google Gemini Chat Model": link("ai_languageModel"),
            "Simple Memory": link("ai_memory"),
            "EventGuard gateway": link("ai_tool"),
        },
        "settings": {"executionOrder": "v1", "saveDataSuccessExecution": "all"},
    }


def main() -> None:
    for role in ROLES:
        path = HERE / f"c0-{role}.json"
        path.write_text(json.dumps(workflow(role), indent=2) + "\n", encoding="utf-8", newline="\n")
        print(f"{path.relative_to(ROOT)}  chat webhook: {chat_url(role)}")


if __name__ == "__main__":
    main()
