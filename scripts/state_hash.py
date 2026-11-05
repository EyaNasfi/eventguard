"""Print the SHA-256 of EventSim's full state (from /_test/export) and the row counts.

python scripts/state_hash.py      # uses EVENTSIM_URL and EVENTSIM_TEST_TOKEN (env or .env)
"""

import hashlib
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    env = {k: v for k, v in dotenv_values(ROOT / ".env").items() if v is not None}
    env.update(os.environ)
    if not env.get("EVENTSIM_TEST_TOKEN"):
        sys.exit("EVENTSIM_TEST_TOKEN missing in environment/.env")
    response = httpx.get(
        env.get("EVENTSIM_URL", "http://127.0.0.1:8000") + "/_test/export",
        headers={"X-Test-Token": env["EVENTSIM_TEST_TOKEN"]},
    )
    response.raise_for_status()
    state = response.json()
    canonical = json.dumps(state, sort_keys=True, separators=(",", ":")).encode()
    print("sha256:", hashlib.sha256(canonical).hexdigest())
    print("counts:", {table: len(rows) for table, rows in state.items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
