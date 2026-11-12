"""S2-04: the exported C0 workflows hold no secret and follow the identity design (ADR-005)."""

import json
from pathlib import Path

import pytest

from agent.n8n_lab import GATEWAY_CREDENTIAL, GEMINI_CREDENTIAL, ROLES, render
from agent.workflows.generate import HERE, PROMPT_FILE, chat_url, webhook_id, workflow

ROOT = Path(__file__).resolve().parent.parent


def exported(role: str) -> dict[str, object]:
    data: dict[str, object] = json.loads((HERE / f"c0-{role}.json").read_text(encoding="utf-8"))
    return data


@pytest.mark.parametrize("role", ROLES)
def test_export_matches_the_generator(role: str) -> None:
    assert exported(role) == json.loads(json.dumps(workflow(role)))


@pytest.mark.parametrize("role", ROLES)
def test_credentials_are_names_only_and_role_specific(role: str) -> None:
    nodes = workflow(role)["nodes"]
    refs = {ctype: ref for node in nodes for ctype, ref in (node.get("credentials") or {}).items()}
    assert refs == {
        "googlePalmApi": {"name": GEMINI_CREDENTIAL},
        "httpBearerAuth": {"name": GATEWAY_CREDENTIAL.format(role=role)},
    }


def test_webhook_ids_are_stable_and_distinct() -> None:
    ids = [webhook_id(r) for r in ROLES]
    assert len(set(ids)) == 3 and ids == [webhook_id(r) for r in ROLES]
    assert chat_url("editor").endswith(f"/webhook/{webhook_id('editor')}/chat")


def test_gateway_url_carries_the_chat_session_for_log_correlation() -> None:
    [tool] = [n for n in workflow("editor")["nodes"] if n["name"] == "EventGuard gateway"]
    url = tool["parameters"]["endpointUrl"]
    assert url.startswith("=http://gateway:8100/mcp?eg_session=")
    assert ".json.sessionId" in url


def test_system_prompt_has_the_canary_placeholder_and_no_security_rules() -> None:
    prompt = PROMPT_FILE.read_text(encoding="utf-8")
    assert "__EG_SYSTEM_PROMPT_CANARY__" in prompt
    assert "PROC-" in prompt and "search_procedures" in prompt
    for word in ("injection", "untrusted", "never reveal", "ignore instructions"):
        assert word not in prompt.lower()  # C0: no security instructions (those are C1)


def test_no_node_level_retry_on_the_agent() -> None:
    [agent] = [n for n in workflow("editor")["nodes"] if n["name"] == "AI Agent"]
    assert not agent.get("retryOnFail")


def test_render_fills_placeholders_and_refuses_missing_values() -> None:
    text = json.dumps(workflow("reader"))
    env = {"GEMINI_MODEL": "m-1", "EG_SYSTEM_PROMPT_CANARY": "EG-CANARY-SP-abc"}
    out = render(text, env)
    assert "__GEMINI_MODEL__" not in out and "models/m-1" in out
    assert "EG-CANARY-SP-abc" in out
    with pytest.raises(SystemExit):
        render(text, {"GEMINI_MODEL": "m-1"})


def test_exports_contain_no_env_value() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        pytest.skip("no .env on this machine")
    values = [
        line.split("=", 1)[1].strip()
        for line in env_file.read_text(encoding="utf-8").splitlines()
        if "=" in line and not line.startswith("#")
    ]
    secrets = [v for v in values if len(v) >= 12]
    for role in ROLES:
        text = (HERE / f"c0-{role}.json").read_text(encoding="utf-8")
        assert not [v for v in secrets if v in text], role
