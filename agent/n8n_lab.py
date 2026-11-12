"""Small client for the local n8n public API (S2-02, S2-04).

Creates the lab credentials from `.env` and imports workflows. It never prints a secret:
credential values are sent to n8n (which stores them encrypted with N8N_ENCRYPTION_KEY) and
only names and ids are reported.

    python -m agent.n8n_lab setup                # first start: owner account + API key into .env
    python -m agent.n8n_lab credentials          # create or replace the lab credentials
    python -m agent.n8n_lab import FILE.json...  # import or update workflows, then activate them
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent
ROLES = ("reader", "editor", "admin")

# Credential names used by the exported workflows. Exports carry only these names, never ids
# or values; `import_workflow` swaps each name for the id of the credential in this n8n.
GATEWAY_CREDENTIAL = "EventGuard gateway ({role})"
GEMINI_CREDENTIAL = "EventGuard Gemini"


# Placeholders in exported workflows, filled from `.env` at import time only, so the files in
# Git never hold these values (S2-04).
PLACEHOLDERS = {
    "__GEMINI_MODEL__": "GEMINI_MODEL",
    "__EG_SYSTEM_PROMPT_CANARY__": "EG_SYSTEM_PROMPT_CANARY",
}


def render(text: str, env: dict[str, str]) -> str:
    for placeholder, key in PLACEHOLDERS.items():
        if placeholder in text:
            value = env.get(key, "")
            if not value:
                raise SystemExit(f"{key} is empty in .env (needed by {placeholder})")
            text = text.replace(placeholder, json.dumps(value)[1:-1])
    return text


def load_env() -> dict[str, str]:
    values = {k: v for k, v in dotenv_values(ROOT / ".env").items() if v is not None}
    return values


class N8n:
    def __init__(self, base_url: str, api_key: str, transport: httpx.BaseTransport | None = None):
        self.http = httpx.Client(
            base_url=f"{base_url.rstrip('/')}/api/v1",
            headers={"X-N8N-API-KEY": api_key},
            timeout=30,
            transport=transport,
        )

    def _all(self, path: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            params: dict[str, str | int] = {"limit": 100}
            if cursor:
                params["cursor"] = cursor
            page = self.http.get(path, params=params).raise_for_status().json()
            rows.extend(page["data"])
            cursor = page.get("nextCursor")
            if not cursor:
                return rows

    # ------------------------------------------------------------------ credentials
    def credentials(self) -> dict[str, str]:
        """name -> id of every credential."""
        return {c["name"]: str(c["id"]) for c in self._all("/credentials")}

    def put_credential(self, name: str, ctype: str, data: dict[str, Any]) -> str:
        """Create the credential, replacing any credential with the same name."""
        existing = self.credentials().get(name)
        if existing:
            self.http.delete(f"/credentials/{existing}").raise_for_status()
        created = self.http.post("/credentials", json={"name": name, "type": ctype, "data": data})
        created.raise_for_status()
        return str(created.json()["id"])

    # ------------------------------------------------------------------ workflows
    def workflows(self) -> dict[str, str]:
        return {w["name"]: str(w["id"]) for w in self._all("/workflows")}

    def import_workflow(self, workflow: dict[str, Any], activate: bool = True) -> str:
        """Create or update a workflow by name; credential names are mapped to local ids."""
        creds = self.credentials()
        nodes = json.loads(json.dumps(workflow["nodes"]))
        for node in nodes:
            for ctype, ref in (node.get("credentials") or {}).items():
                if ref["name"] not in creds:
                    raise SystemExit(f"credential '{ref['name']}' missing: run 'credentials' first")
                node["credentials"][ctype] = {"id": creds[ref["name"]], "name": ref["name"]}
        body = {
            "name": workflow["name"],
            "nodes": nodes,
            "connections": workflow["connections"],
            "settings": workflow.get("settings") or {"executionOrder": "v1"},
        }
        existing = self.workflows().get(workflow["name"])
        if existing:
            if activate:
                self.http.post(f"/workflows/{existing}/deactivate")
            self.http.put(f"/workflows/{existing}", json=body).raise_for_status()
            wid = existing
        else:
            wid = str(self.http.post("/workflows", json=body).raise_for_status().json()["id"])
        if activate:
            self.http.post(f"/workflows/{wid}/activate").raise_for_status()
        return wid

    def executions(self, workflow_id: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit, "includeData": "true"}
        if workflow_id:
            params["workflowId"] = workflow_id
        rows: list[dict[str, Any]] = self.http.get("/executions", params=params).json()["data"]
        return rows

    def execution(self, execution_id: str) -> dict[str, Any]:
        r = self.http.get(f"/executions/{execution_id}", params={"includeData": "true"})
        result: dict[str, Any] = r.raise_for_status().json()
        return result


def client_from_env(env: dict[str, str] | None = None) -> N8n:
    env = env or load_env()
    base = env.get("N8N_URL", "http://127.0.0.1:5678")
    key = env.get("N8N_API_KEY")
    if not key:
        raise SystemExit("N8N_API_KEY is empty in .env (create it in n8n: Settings > n8n API)")
    return N8n(base, key)


def create_lab_credentials(n8n: N8n, env: dict[str, str]) -> dict[str, str]:
    """One bearer credential per role for the gateway, plus the Gemini key. Returns name -> id."""
    made: dict[str, str] = {}
    for role in ROLES:
        token = env.get(f"GATEWAY_TOKEN_{role.upper()}")
        if not token:
            raise SystemExit(f"GATEWAY_TOKEN_{role.upper()} is empty in .env")
        name = GATEWAY_CREDENTIAL.format(role=role)
        made[name] = n8n.put_credential(name, "httpBearerAuth", {"token": token})
    key = env.get("GEMINI_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY is empty in .env")
    made[GEMINI_CREDENTIAL] = n8n.put_credential(
        GEMINI_CREDENTIAL,
        "googlePalmApi",
        {"host": "https://generativelanguage.googleapis.com", "apiKey": key},
    )
    return made


def set_env_value(name: str, value: str, path: Path = ROOT / ".env") -> None:
    """Write NAME=value into .env (replacing an existing line). The value is never printed."""
    lines = path.read_text(encoding="utf-8").splitlines()
    out = [f"{name}={value}" if line.startswith(f"{name}=") else line for line in lines]
    if not any(line.startswith(f"{name}=") for line in lines):
        out.append(f"{name}={value}")
    path.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")


def setup_owner_and_key(env: dict[str, str], transport: httpx.BaseTransport | None = None) -> str:
    """First start of a local n8n: create the owner account (fictional, from .env) and an API
    key, stored in .env as N8N_API_KEY. Safe to re-run: an existing owner or key is kept."""
    base = env.get("N8N_URL", "http://127.0.0.1:5678")
    http = httpx.Client(base_url=base, timeout=30, transport=transport)
    owner = {
        "email": env["N8N_OWNER_EMAIL"],
        "firstName": "Lab",
        "lastName": "Owner",
        "password": env["N8N_OWNER_PASSWORD"],
    }
    created = http.post("/rest/owner/setup", json=owner)
    login = http.post(
        "/rest/login",
        json={"emailOrLdapLoginId": owner["email"], "password": owner["password"]},
    )
    login.raise_for_status()
    if env.get("N8N_API_KEY"):
        return f"owner {'created' if created.is_success else 'already set'}; API key kept"
    scopes = http.get("/rest/api-keys/scopes")
    body: dict[str, Any] = {"label": "eventguard-lab", "expiresAt": None}
    if scopes.is_success:
        body["scopes"] = scopes.json()["data"]
    made = http.post("/rest/api-keys", json=body).raise_for_status().json()["data"]
    set_env_value("N8N_API_KEY", made.get("rawApiKey") or made["apiKey"])
    return f"owner {'created' if created.is_success else 'already set'}; API key stored in .env"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup", help="create the local owner account and an API key (first start)")
    sub.add_parser("credentials")
    imp = sub.add_parser("import")
    imp.add_argument("files", nargs="+", type=Path)
    imp.add_argument("--no-activate", action="store_true")
    args = parser.parse_args(argv)
    env = load_env()
    if args.cmd == "setup":
        print(setup_owner_and_key(env))
        return 0
    n8n = client_from_env(env)
    if args.cmd == "credentials":
        for name, cid in create_lab_credentials(n8n, env).items():
            print(f"credential '{name}' -> id {cid}")
    else:
        for path in args.files:
            workflow = json.loads(render(path.read_text(encoding="utf-8"), env))
            wid = n8n.import_workflow(workflow, activate=not args.no_activate)
            print(f"workflow '{workflow['name']}' -> id {wid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
