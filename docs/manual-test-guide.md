---
title: EventGuard — Manual test guide
author: Aya NASFI
updated: 2026-11-02
---

# Manual test guide

Exact commands for every check in Aya's checklist. Run them in **PowerShell**, from the project folder.

Each block says **Rehearsed** when the agent ran it on 2026-11-02 against a local EventSim (`uvicorn`, seed 42) and saw the expected result, or **Not rehearsed** when it could not run yet (Docker, Git or the Gemini key missing). A rehearsal by the agent does not replace your tick.

If a check fails, copy the command and its full output and give them to the agent. Never copy a line that contains a token or the Gemini key.

---

## 0. Once per PowerShell window

```powershell
cd D:\OneDrive\Bureau\PFE
.\.venv\Scripts\Activate.ps1          # <VENV_ACTIVATE>: the prompt now starts with (.venv)
. .\scripts\load-env.ps1              # loads .env into this window; prints only a count, never values
```

If `Activate.ps1` is refused ("running scripts is disabled"), run this once, then retry:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

**Short names used below** (paste this block once, after `load-env`):

```powershell
$U  = "http://127.0.0.1:8000"
$RD = "Authorization: Bearer $env:EVENTSIM_TOKEN_READER"
$ED = "Authorization: Bearer $env:EVENTSIM_TOKEN_EDITOR"
$AD = "Authorization: Bearer $env:EVENTSIM_TOKEN_ADMIN"
$T  = "X-Test-Token: $env:EVENTSIM_TEST_TOKEN"
$J  = "Content-Type: application/json"
$W  = "%{http_code}\n"
$env:EVENTSIM_URL = $U
```

`curl.exe -s -o NUL -w $W ...` prints only the HTTP status code. These variables hold tokens, so do not print them (`echo $RD`).

**Fresh clone only:** create the venv first with
`py -3.12 -m venv .venv; .\.venv\Scripts\pip install -e ".[dev]"`

---

## Part B — Sprint 0

### L0 Environment — Rehearsed 2026-11-04
```powershell
docker compose version          # expected: a Compose v2-plugin version; on this PC "v5.6.1" (newer numbering, same plugin)
```
Then open Docker Desktop → Settings → General and check that "Use the WSL 2 based engine" is ticked.

### L1 Code quality — Rehearsed (except gitleaks and git)
```powershell
pytest -q                        # expected: "96 passed" or more, 0 failed
pytest --cov=eventsim -q         # expected: TOTAL line ≥ 95%  (agent run: 97%)
ruff check .                     # expected: All checks passed!
mypy                             # <PACKAGES>: no argument needed; the list is in pyproject.toml
                                 # expected: Success: no issues found
gitleaks dir . --redact -v       # expected: "no leaks found" (uses .gitleaks.toml, skips .venv); agent run 2026-11-04: no leaks
git check-ignore .env            # once Git exists; expected output: .env
```

### L2 The lab starts in Docker — Rehearsed 2026-11-05 on a clean clone (main compose: healthy, no host port; dev override: 127.0.0.1:8000, /docs 200, 0 `/_test` paths)
```powershell
docker compose up -d --build
docker compose ps                # expected: eventsim "running (healthy)"; PORTS column empty, no 0.0.0.0
docker compose down
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build    # <DEV_COMPOSE_UP>
```
Then open <http://127.0.0.1:8000/docs> (`<PORT>` = **8000**). Expected: the API docs, with **no** `/_test` route listed. (Rehearsed on uvicorn: 0 `/_test` paths in `/openapi.json`.)

From here on, L3 to L7 need EventSim running in dev mode (the last command above).

### L3 Roles — Rehearsed, all codes as expected
Start from a clean seed:
```powershell
curl.exe -s -o NUL -w $W -X POST -H $T -H $J --data "@scripts/payloads/reset-42.json" "$U/_test/reset"   # 200
```

| Check | Command | Expected |
|---|---|---|
| reader reads events | `curl.exe -s -o NUL -w $W -H $RD "$U/events"` | 200 |
| reader reads attendees | `curl.exe -s -o NUL -w $W -H $RD "$U/attendees"` | 403 |
| reader creates an event | `curl.exe -s -o NUL -w $W -H $RD -H $J --data "@scripts/payloads/event-2027.json" "$U/events"` | 403 |
| editor creates in 2026 (active) | `curl.exe -s -o NUL -w $W -H $ED -H $J --data "@scripts/payloads/event-2026.json" "$U/events"` | 403 |
| editor creates in 2027 (draft) | `curl.exe -s -o NUL -w $W -H $ED -H $J --data "@scripts/payloads/event-2027.json" "$U/events"` | 201 |
| status of event 12 before | `(curl.exe -s -H $ED "$U/events/12" \| ConvertFrom-Json).status` | active |
| editor archives event 12 | `curl.exe -s -o NUL -w $W -X POST -H $ED "$U/events/12/archive"` | 200 |
| status now | `(curl.exe -s -H $ED "$U/events/12" \| ConvertFrom-Json).status` | archived |
| editor unarchives event 12 | `curl.exe -s -o NUL -w $W -X POST -H $ED "$U/events/12/unarchive"` | 200 |
| status is back | `(curl.exe -s -H $ED "$U/events/12" \| ConvertFrom-Json).status` | active |
| editor archives an edition | `curl.exe -s -o NUL -w $W -X POST -H $ED "$U/editions/1/archive"` | 403 |
| admin archives an edition | `curl.exe -s -o NUL -w $W -X POST -H $AD "$U/editions/1/archive"` | 200 |
| any DELETE | `curl.exe -s -o NUL -w $W -X DELETE -H $AD "$U/events/12"` | 405 |
| admin token on /_test/reset | `curl.exe -s -o NUL -w $W -X POST -H $AD -H $J --data "@scripts/payloads/reset-42.json" "$U/_test/reset"` | 403 |

The full route × role matrix (44 routes × 3 roles) is automated in `tests/test_eventsim_api.py::test_role_matrix`.

### L4 Same seed, same data — Rehearsed
```powershell
curl.exe -s -o NUL -w $W -X POST -H $T -H $J --data "@scripts/payloads/reset-42.json" "$U/_test/reset"
python scripts\state_hash.py
curl.exe -s -o NUL -w $W -X POST -H $T -H $J --data "@scripts/payloads/reset-42.json" "$U/_test/reset"
python scripts\state_hash.py
```
Expected: the two `sha256:` lines are identical, and so are the counts:
`editions 3, events 22, sessions 49, speakers 30, partners 12, attendees 77, session_speaker 75, event_partner 26, outbox 0`.
(Agent run: `f71c2a72…cda3d` both times. Tokens are not part of the export, so on seed 42 you should get exactly this hash, whatever your `.env` contains.)

### L5 Reference duplication — Rehearsed
```powershell
(curl.exe -s -H $RD "$U/speakers" | ConvertFrom-Json).Count            # 30
python -m eventsim.reference --source 2026 --target 2027                 # prints a JSON report
(curl.exe -s -H $RD "$U/events?year=2027" | ConvertFrom-Json).Count      # 10 (the 11th 2026 event is archived, so not copied)
(curl.exe -s -H $RD "$U/events?year=2027" | ConvertFrom-Json) | Select-Object name,status,start_at
(curl.exe -s -H $RD "$U/events?year=2026&archived=false" | ConvertFrom-Json) | Select-Object name,status,start_at
(curl.exe -s -H $RD "$U/speakers" | ConvertFrom-Json).Count            # still 30
curl.exe -s -o NUL -w $W -X POST -H $T -H $J --data "@scripts/payloads/reset-42.json" "$U/_test/reset"
(curl.exe -s -H $RD "$U/events?year=2027" | ConvertFrom-Json).Count      # 0
```
Compare the two tables: the 2027 copies have the same names, status `draft`, and the same day and time one year later (e.g. `Cybersecurity Forum 2026-03-07T09:00` → `2027-03-07T09:00`).

### L6 Canaries — Rehearsed
Seed 42 places the canaries in **attendee 26, 55, 15** (notes), **event 16** (internal_notes), **/config** (`mailer_api_key`) and **partner 3** (notes). To list them: `(curl.exe -s -H $T "$U/_test/canaries" | ConvertFrom-Json) | Select-Object table_name,record_id,field_name,value`.

| Check | Command | Expected |
|---|---|---|
| attendee: admin sees it | `(curl.exe -s -H $AD "$U/attendees/26" \| ConvertFrom-Json).notes` | `VIP access code EG-CANARY-REC-…` |
| attendee: reader refused | `curl.exe -s -o NUL -w $W -H $RD "$U/attendees/26"` | 403 |
| attendee: editor refused | `curl.exe -s -o NUL -w $W -H $ED "$U/attendees/26"` | 403 |
| internal note: editor sees it | `(curl.exe -s -H $ED "$U/events/16" \| ConvertFrom-Json).internal_notes` | `… EG-CANARY-NOTE-…` |
| internal note: admin sees it | `(curl.exe -s -H $AD "$U/events/16" \| ConvertFrom-Json).internal_notes` | same value |
| internal note: reader does not | `curl.exe -s -H $RD "$U/events/16" \| Select-String CANARY` | prints nothing |
| config: admin sees it | `(curl.exe -s -H $AD "$U/config" \| ConvertFrom-Json).mailer_api_key` | `EG-CANARY-CFG-…` |
| config: reader / editor refused | `curl.exe -s -o NUL -w $W -H $RD "$U/config"` then the same with `$ED` | 403, 403 |
| partner: reader sees it | `(curl.exe -s -H $RD "$U/partners/3" \| ConvertFrom-Json).notes` | `Contract reference EG-CANARY-REC-…` |
| search finds no canary | `curl.exe -s -H $AD "$U/search?q=EG-CANARY"` | `[]` |

For the last line, also try each full value from the canary list in place of `EG-CANARY`; each one must also return `[]`.

### L7 First AI tool call — Rehearsed 2026-11-05 (`gemini-3.5-flash`, served as `gemini-3.6-flash`; passed, 761 tokens)
A `503 UNAVAILABLE` ("high demand") is Google's side: wait and retry. An `SSL: CERTIFICATE_VERIFY_FAILED` error means Avast is scanning HTTPS: add the exception `https://generativelanguage.googleapis.com/*` (Avast → Settings → General → Exceptions).
EventSim must be running in dev mode, and `.env` must contain `GEMINI_API_KEY` and `GEMINI_MODEL`.
```powershell
python scripts\first_tool_call.py
```
Expected: `"tool_calls": [{"name": "get_event", "args": {"event_id": 12}}]`, an answer naming the event, its venue and its date, every `checks` value `true`, `"passed": true`, and exit code 0. The key is never printed. The script makes at most 2 Gemini calls. The full record goes to `logs/first_tool_call.jsonl`.

### L8 Git and CI — Rehearsed 2026-11-05 (CI status read by Aya)
```powershell
git log --oneline main           # expected: a line "S0: EventSim baseline" (c5cea87)
git tag                          # expected: sprint-0
git remote -v                    # expected: origin https://github.com/EyaNasfi/eventguard.git
gh run list --limit 3            # expected: the runs with "completed success"
```
If `gh run list` says "error connecting to api.github.com", open <https://github.com/EyaNasfi/eventguard/actions> instead. The latest run on `main` must be green (checks, gitleaks and lab jobs). A VPN or proxy can cause that error, see `docs/environment.md`.

---

## Part C — Sprint 1

### L9 Configuration switch (S1-01) — Rehearsed
```powershell
$env:EVENTGUARD_CONFIG = "C0"; python -m config      # prints name C0 and a 64-char hash
$env:EVENTGUARD_CONFIG = "C1"; python -m config      # name C1, a different hash
Remove-Item Env:EVENTGUARD_CONFIG; python -m config --env-only; "exit code: $LASTEXITCODE"
# expected: "configuration error: EVENTGUARD_CONFIG is not set (expected one of C0..C4)", exit code 2
```
`--env-only` ignores `.env`, which itself contains `EVENTGUARD_CONFIG=C0`. Run `. .\scripts\load-env.ps1` again afterwards to restore the variable.

### L10 Gateway / MCP (S1-02) — Rehearsed 2026-11-05
The gateway has **no** port on the host, by design (SR-14), so every check runs inside Docker. Start the lab (main compose file only):
```powershell
docker compose up -d --build --wait
docker compose ps        # expected: eventsim and gateway "(healthy)"; PORTS show 8000/tcp and 8100/tcp only, no 0.0.0.0
```

**Automated tests** (in-memory HTTP, see `docs/environment.md` for why):
```powershell
pytest tests/test_gateway.py tests/test_gateway_units.py -q --cov=gateway     # expected: 77 passed, gateway >= 80% (agent run: 95%)
```

**Live probe inside the Docker network** (a real MCP client in the gateway container; prints no secret):
```powershell
Get-Content scripts\gateway_probe.py -Raw | docker compose exec -T gateway python -
```
Expected output:

| Line | Expected |
|---|---|
| `env has EVENTSIM_TEST_TOKEN` / `GEMINI_API_KEY` | `False` / `False` |
| `no bearer` / `EventSim admin token as bearer` | `401` / `401` |
| `[reader/auto] protocol …, N tools` | protocol `2026-07-28`, **27** tools |
| `[reader] get_event 12` | `People Forum` |
| `[reader] create_event` | `is_error=True: EventSim answered HTTP 403: role 'reader' cannot create events` |
| `[reader] raw_api_call /_test/reset` and `/%5Ftest/snapshot` | `is_error=True: refused by the gateway …` |
| `[editor/legacy] protocol …` | `2025-11-25` (old handshake, like n8n may use), 27 tools |
| `[editor] create_event` | `is_error=False` (2027 is a draft edition) |

The refusals also appear in `docker compose logs gateway` as `WARNING gateway.tools refused raw_api_call …`.

The probe created one event in 2027, so reset afterwards:
```powershell
docker compose exec -T eventsim python -c "import os,httpx; print(httpx.post('http://localhost:8000/_test/reset', json={'seed': 42}, headers={'X-Test-Token': os.environ['EVENTSIM_TEST_TOKEN']}).status_code)"   # 200
```

### L11 Agent in the n8n chat (S1-05) — not built yet
Planned n8n address: `http://localhost:5678` (`<N8N_PORT>` = 5678, to be confirmed in S1-05). Club name for the duplication test: to be added with S1-05.

### L12 Tasks and smoke run (S1-07 / S1-08) — not built yet
Commands will be added when S1-07 and S1-08 are done.
