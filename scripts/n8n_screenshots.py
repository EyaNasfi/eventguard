"""Screenshots of n8n executions for the S2-04 demo checks (headless Microsoft Edge).

    python scripts/n8n_screenshots.py OUT_DIR "<workflow name>:<execution id>:<file name>" ...

Logs in through n8n's REST API with the local owner account from `.env` (never printed), hands
the session cookie to a headless Edge (Playwright, channel "msedge", no browser download), opens
each execution and saves a PNG. The browser is always closed, even on error.
"""

import sys
from pathlib import Path

import httpx
from dotenv import dotenv_values
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
BASE = "http://localhost:5678"


def session_cookie() -> list[dict[str, str]]:
    env = dotenv_values(ROOT / ".env")
    r = httpx.post(
        f"{BASE}/rest/login",
        json={"emailOrLdapLoginId": env["N8N_OWNER_EMAIL"], "password": env["N8N_OWNER_PASSWORD"]},
        timeout=30,
    )
    r.raise_for_status()
    return [{"name": c.name, "value": c.value or "", "url": BASE} for c in r.cookies.jar]


def workflow_ids() -> dict[str, str]:
    env = dotenv_values(ROOT / ".env")
    r = httpx.get(
        f"{BASE}/api/v1/workflows", headers={"X-N8N-API-KEY": env["N8N_API_KEY"] or ""}, timeout=30
    )
    return {w["name"]: str(w["id"]) for w in r.raise_for_status().json()["data"]}


def main(argv: list[str]) -> int:
    out = Path(argv[0])
    out.mkdir(parents=True, exist_ok=True)
    ids = workflow_ids()
    cookies = session_cookie()
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        try:
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            context.add_cookies(cookies)  # type: ignore[arg-type]
            page = context.new_page()
            for spec in argv[1:]:
                workflow, execution, name = spec.split(":")
                page.goto(f"{BASE}/workflow/{ids[workflow]}/executions/{execution}")
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(2000)
                page.keyboard.press("Escape")  # closes the "Production Checklist" popup
                page.mouse.click(1300, 700)
                logs = page.get_by_text("Logs", exact=True)
                if logs.count():
                    logs.first.click(timeout=5000)  # opens the chat + logs panel
                page.wait_for_timeout(2500)
                path = out / name
                page.screenshot(path=str(path))
                print(f"saved {path}")
        finally:
            browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
