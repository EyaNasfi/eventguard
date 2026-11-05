---
title: EventGuard — Sprint 1 log
author: Aya NASFI
---

# Sprint 1 log

## 2026-11-02 — S1-00 Repository audit and Sprint 0 check

**What I did.** Inspected the workspace `D:\OneDrive\Bureau\PFE`, searched `C:\Users\Eya` and `D:\` (depth 4) for any EventGuard/EventSim folder or compose file, and checked the local toolchain (Python, Git, Docker, gitleaks).

**Files touched.** `docs/sprints/sprint-0-status.md` (new), `docs/sprints/sprint-1-log.md` (new).

**Result.** The workspace was empty and no EventGuard code exists elsewhere on the machine. Git and Docker are not installed. Python 3.12 is available via `py -3.12`. The P0 exit criterion is not met, so per the stop rule no S1-01+ work was started.

**How to verify.**
```powershell
Get-ChildItem -Force D:\OneDrive\Bureau\PFE -Recurse
Get-Command git, docker -ErrorAction SilentlyContinue
py -0p
```

**Unsure about.** Whether the Sprint 0 code lives in a remote repository that was simply not cloned here. Blocking questions are listed in section 5 of `sprint-0-status.md`.

## 2026-11-02 — P0 rebuild (stop rule, ADR-001 / ADR-002)

**What I did.** The project lead chose option 2 (build P0). I built EventSim with FastAPI + SQLModel on SQLite. It has six business tables plus link and system tables, bearer-token roles, a deterministic seeded generator, test-only endpoints (reset, snapshot, state diff, export, outbox, canaries), an outbox, canaries and the reference duplication script. I also added Docker files, CI and threat model v0.

**Files touched.** `eventsim/` (settings, models, db, seed, schemas, auth, api, harness, snapshot, reference, main, Dockerfile), `tests/` (4 test files + conftest), `pyproject.toml`, `.gitignore`, `.env.example`, `docker-compose.yml`, `docker-compose.dev.yml`, `.github/workflows/ci.yml`, `README.md`, `docs/decisions.md`, `docs/threat-model-v0.md`, `docs/sprints/sprint-0-status.md`.

**Why this approach.**
- *SQLite in a volume.* One container, and resetting it is trivial. The snapshot lives in process memory, so the server runs with exactly one uvicorn worker (noted in the Dockerfile).
- *Separate `X-Test-Token` for `/_test/*`.* The gateway never holds it, so no gateway bug can open a path from the agent to the test endpoints (FR-SIM-06). The gateway deny rule planned in S1-02 is a second layer.
- *Archive does not cascade.* Every write shows up in the diff, and the agent has to plan its operations (ADR-002).
- *Event times are naive local times; audit timestamps are UTC.* SQLModel 0.0.48 refuses naive datetimes unless they are annotated `NaiveDatetime`.
- *Reference script uses the public API.* It goes through HTTP with a normal user token, so its diff is exactly what a correct agent run would produce.

**How to verify.**
```powershell
py -3.12 -m venv .venv; .\.venv\Scripts\pip install -e ".[dev]"
.\.venv\Scripts\ruff check .; .\.venv\Scripts\ruff format --check .; .\.venv\Scripts\mypy
.\.venv\Scripts\python -m pytest --cov=eventsim      # 33 passed, 97% coverage (2026-11-02)
```
Live check that I ran: uvicorn on port 8765 with a file database, then `python -m eventsim.reference --source 2026 --target 2027` → 10 events in 2027; an admin token on `/_test/snapshot` → 403; `/_test/reset` → 0 events in 2027.

**Not run / unsure.**
- `docker compose up` was **not run**: Docker is not installed here. There are no commits or branches either: Git is not installed. That breaks rule 3 for now; the work will go in as one P0 commit once Git exists.
- CI was **not run** (no remote).
- I had no access to the spec. Table names, the role matrix and the canary placement are my assumptions (ADR-002).
- A tooling incident, already fixed: a PowerShell bulk edit read UTF-8 as ANSI and mangled two invented names. I made all names ASCII and removed the BOMs; from now on I use the editor tools only.

**Re-plan proposal for S1 (2 → 8 Nov, needs the lead's OK).** P0 took about day 1. I propose cutting S1-09 now (the first planned cut). S1-03 and S1-05 need Docker (n8n) and a Gemini API key, so they are blocked until both exist. Meanwhile I can do S1-01, S1-02 (testable without Docker), S1-04 (except embedding calls, which need the Gemini key) and S1-07.

## 2026-11-02 — PL decision #1

Received from the project lead. The re-plan above was **not approved as proposed**. Binding content:

1. **Step 1 — environment first.** Install Git, Docker (+ Compose v2), gitleaks, pre-commit and optionally `gh`, from official sources only. Record the versions in `docs/environment.md`. Anything that needs admin rights, a password, a reboot or a GUI is done by Aya, following exact steps I give her. Git: `user.name = Aya NASFI`, correct `core.autocrlf`. Baseline: `git init` on `main`, gitleaks clean *before* the first commit, one commit `S0: EventSim baseline` tagged `sprint-0` (no fake history), pre-commit hooks, then the remote (private, created by Aya), push, CI. Aya-only actions: Gemini API key, Google Cloud budget alert + cap (€20 cap, alert at 50%), writing the key into `.env` herself (never pasted in chat, never printed/logged/committed by me), creating the remote.
2. **Step 2 — close Sprint 0 for real.** Clean-clone `docker compose up -d --build` → EventSim healthy, reference script run inside the compose network, no host port in the main compose file. CI green on the remote (compose job, pytest, ruff, mypy, gitleaks). `scripts/first_tool_call.py`: one Gemini model (from `GEMINI_MODEL`) with a single `get_event` tool, 1–3 calls in total, logging the model, tokens and result. Update `sprint-0-status.md` with met / not met for all three parts.
3. **Step 3 — align EventSim with the spec** (ADR-002 updated and Accepted, with tests for each point):
   - (a) Reader and editor do not read attendees; only admin does. Route-by-route matrix test.
   - (b) Editor creates only into a **draft** edition, and archives/unarchives single events. Editions stay admin-only. Admin can do everything.
   - (c) Canaries in three places (attendee record, internal note on an event or edition, fake config secret `EG-CANARY-CFG-…` readable by admin). Each one reachable through a normal read path for allowed roles, refused to the others, absent from search. One test per canary.
   - (d) Status values `draft | active | archived`, recorded as an accepted deviation (the role matrix needs draft editions).
   - Accepted as-is: table names, extra link and outbox tables, `/_test/*` with its own token and switch, reference script behaviour, and non-cascading edition archive (UC3 is a composed plan, consistent with FR-SIM-05; stated in the archive-edition procedure sheet).
   - Afterwards: re-run the reference script and all tests, coverage ≥ 95% on `eventsim/`, merge.
4. **S1-09 moves to Sprint 2 day 1** (postponed, not removed).
5. **Step 4:** S1-01 → S1-02 → S1-03 → S1-04 → S1-05 → S1-06 → S1-07 → S1-08 → S1-10, one branch per task, target Sunday 8 Nov. While waiting on Step 1 I may write S1-01, S1-02 (against a local EventSim without Docker), the S1-04 sheets and S1-07. Nothing goes to `main` before Steps 1–3 are done. S1-02 is built on the corrected role matrix.
6. **Step 5:** verification campaign A–H in `docs/sprints/sprint-1-verification.md` (checks actually run, PASS/FAIL with evidence), update the sprint report, then **stop**: no Sprint 2 work without an explicit go.

## 2026-11-02 — Step 1 started (environment)

**OS detected.** Windows 11 Pro 10.0.26200, i5-10500H with virtualisation enabled in firmware, but no hypervisor running and no WSL distribution. Target: Windows + WSL2 + Docker Desktop. Full details in `docs/environment.md`.

**Done without admin rights.** pre-commit 4.3.0 installed in `.venv`. Added `.pre-commit-config.yaml` (gitleaks, ruff, ruff-format, mypy) and `.gitattributes` (`eol=lf`). Added `*.sqlite3`, `vectorstore_data/` and `chroma/` to `.gitignore`. Checked the Authenticode signature of `Downloads\Docker Desktop Installer.exe`: Valid, signed by Docker Inc.

**Waiting on Aya.** Steps for WSL2 (admin + reboot), Docker Desktop (GUI), Git, gitleaks and gh (winget, may trigger UAC), the Gemini key, the budget cap and the remote were sent in chat.

**Step 3.** Questions sent to the project lead before any EventSim change.

## 2026-11-02 — S1-01 Configuration system C0–C4 (written while waiting; branch `s1/S1-01-config` once Git exists)

**What I did.** Wrote `config/configurations.yaml` with C0 filled in completely and C1–C4 as stubs that inherit C0, with all nine layer flags spelled out and `false`. `config/loader.py` holds strict Pydantic models (unknown keys rejected at every level, every layer flag required), single-parent inheritance with cycle detection, and selection with `EVENTGUARD_CONFIG` (no silent default). The model name is read from the env variable named in the file (`GEMINI_MODEL`, FR-AGT-02); temperature 0.0 and max_output_tokens 2048 are fixed in the file. The config hash is SHA-256 of the canonical JSON (sorted keys, no spaces) of the resolved config.

**Files touched.** `config/__init__.py`, `config/loader.py`, `config/configurations.yaml`, `tests/test_config.py`, `pyproject.toml`, `.env.example`.

**Why.**
- The resolved config also contains the **model name** and the **SHA-256 of the system prompt file**. Changing the model or editing the prompt then changes the hash, so two runs with the same hash really used the same setup (NFR-02).
- Every stub lists every flag through a YAML anchor. A sprint that turns a layer on replaces that stub's `layers` block, and the diff shows exactly which flags moved.

**How to verify.**
```powershell
.\.venv\Scripts\python -m pytest tests/test_config.py -v    # 11 passed (2026-11-02)
.\.venv\Scripts\python -c "from config import resolve; c = resolve('C0', env={'GEMINI_MODEL': 'x'}); print(c.name, c.hash)"
```

**Unsure about.**
- Tool names in the allow-list are not yet checked against the gateway registry. S1-02 will fail at startup when a config names an unknown tool.
- `system_prompt_sha256` is `null` until `agent/prompts/c0_system.md` exists (S1-05).
- I named the link tools `link_speaker_to_session` and `link_partner_to_event`, and added `create_attendee`, which the brief's list did not name explicitly ("one create_* per entity"). Whether editor may use `create_attendee` depends on Step 3 question 1.

## 2026-11-02 — Aya's test checklist received; Step 3 implemented; manual test guide

**Input.** Aya sent her personal checklist (Parts A–C). It answers most of my Step 3 questions:
- attendees: reader and editor get 403;
- editor: 403 in 2026 (active), 201 in 2027 (draft);
- editor archives single events, and unarchive restores the previous status;
- `internal_notes`: editor and admin see them, reader does not;
- `/config`: admin only;
- partner notes: reader can read them;
- Gemini: free tier, no billing account.

Two questions it does not cover, so my proposed defaults apply: attendee *writes* are admin-only, and editor may create speakers and partners. Both are recorded in ADR-002 rev. 1.

**What I did (Step 3, branch `s1/S0-step3-spec-alignment` once Git exists).**
- One `Status` enum `draft | active | archived` for editions and events. `previous_status` is restored on unarchive, and clients cannot set `archived` directly (422).
- Role checks: attendees admin-only, including in search. The draft-edition rule for editor creates and updates of events, sessions and links. Editor archives events only. Every refusal has a readable reason.
- Canaries: kept the 3 attendee canaries and the partner canary, and added `EG-CANARY-NOTE-…` in one event's `internal_notes` and `EG-CANARY-CFG-…` behind the new admin-only `GET /config`.
- Tests: rewrote `tests/test_eventsim_api.py` around a 44-route × 3-role matrix, added `tests/test_eventsim_canaries.py` (one test per canary plus a search test), and updated the seed and harness tests.

**Helpers for the checklist.**
- `python -m config` prints the active config and its hash; `--env-only` ignores `.env`.
- `scripts/load-env.ps1` loads `.env` without printing any value.
- `scripts/state_hash.py` prints the state hash and row counts.
- `scripts/first_tool_call.py` (L7): Gemini with a single `get_event` tool, at most 2 calls, no automatic function calling. It checks the answer against the real record and never prints the key; untested until a key exists.
- `scripts/payloads/*.json` hold request bodies, so the PowerShell commands need no inline JSON quoting.
- `.gitleaks.toml` keeps the default rules and skips local gitignored folders such as `.venv`.

**Dependencies.** `google-genai==2.34.0` (extras `agent` and `dev`) and `python-dotenv` added. pre-commit added to the dev extra. mypy now checks `eventsim`, `config`, `tests` and `scripts`.

**Docs.** `docs/manual-test-guide.md` (new), ADR-002 rev. 1 (Accepted), README route table.

**How to verify.**
```powershell
.\.venv\Scripts\python -m pytest -q --cov=eventsim     # 96 passed, eventsim 97% (2026-11-02)
.\.venv\Scripts\ruff check .; .\.venv\Scripts\mypy     # clean
```
I rehearsed manual guide checks L1 (except gitleaks and git), L3, L4, L5, L6 and L9 against a live uvicorn on port 8000. Every code and value matched the checklist. Seed 42 state hash `f71c2a72…cda3d`, identical over two resets.

**Not run.** L0, L2, L7, L8: Docker, Git and the Gemini key are still missing. gitleaks is not installed, so `.gitleaks.toml` is untested.

**Unsure.**
- Canary record ids (attendees 26/55/15, event 16, partner 3) are fixed for seed 42 but move if the generator changes. The guide gives the `/_test/canaries` command to list them again.
- PowerShell 5.1 does not unroll a JSON array piped straight from `ConvertFrom-Json` into `Select-Object`. The guide wraps those commands in parentheses. I hit this during the rehearsal and fixed it.

---

## 2026-11-04 — Step 1 progress (A1, A2, A3 done)

**Done.**
- A1: WSL 2.7.14.0, after a repair install of Windows (see `docs/environment.md`).
- A2: Docker 29.9.2 / Compose v5.6.1. `docker compose up` → eventsim healthy, no host port, reference script inside the network → 10 draft events (`sprint-0-status.md` §4c).
- A3: Git 2.56.0, gitleaks 8.30.1, gh 2.103.3 (winget, hashes verified).
- `gitleaks dir . --config .gitleaks.toml --redact` → "no leaks found", exit 0 (167 KB scanned; `.venv` and `.env` skipped as configured).
- `git init -b main`; local `user.name = Aya NASFI`, `core.autocrlf = input`; `git check-ignore` confirms `.env` and `.venv` are ignored; dry-run staging = 47 files, no secret, no data; `pre-commit install` done.
- `.env` created from `.env.example` with random EventSim tokens (never printed).

**Waiting for Aya.** A4 Git email, A5 Gemini key + model in `.env`, A6 private remote URL.

**Not run.** No commit, no tag, no push, no CI run, no first Gemini call.
---

## 2026-11-05 — Baseline commit and tag (Step 1, A4 done)

**Done.**
- Local `user.email` set (repository scope). Before the commit: `pytest` 96 passed, eventsim coverage 97%, ruff, ruff format and mypy clean.
- The first commit attempt failed. The upstream gitleaks pre-commit hook builds gitleaks from source and downloads Go from `go.dev`, which the agent shell cannot resolve (`getaddrinfo failed`; github.com and pypi.org are reachable). `.pre-commit-config.yaml` now runs the installed gitleaks 8.30.1 as a local hook (`gitleaks git --pre-commit --staged --redact`). CI keeps `gitleaks-action` (SR-13).
- Hook controls:
  - positive: a staged random fake `ghp_…` token gave "leaks found: 1", exit 1;
  - negative: after removing it, "no leaks found", exit 0.
- Commit `c5cea87` "S0: EventSim baseline" (47 files, the only commit; the hooks gitleaks, ruff, ruff format and mypy all passed). Annotated tag `sprint-0`.
- `gitleaks git .` over the history: 1 commit scanned, no leaks.

**Note.** The baseline includes the docs as they stood before this entry. Later Sprint 0 closing updates go on a branch, never directly to `main`.

**Waiting for Aya.** A5 Gemini key + model in `.env`; A6 private remote URL + `gh auth login`.
---

## 2026-11-05 — Push, CI and Step 2 checks

**Done.**
- Aya created the private repo `EyaNasfi/eventguard`, ran `gh auth login` and `gh auth setup-git`, then pushed `main` and the tag `sprint-0`.
- CI on `main`: `checks`, `gitleaks` and `lab` are all green. Aya read this on the Actions page; the agent could not reach `api.github.com` (VPN/proxy DNS, see `environment.md`).
- Clean clone in `D:\dev\eventguard-clean` (HEAD = `origin/main`), `.env` from `.env.example`, no-cache build:
  - healthy, no published port;
  - reference script in the network: 10 draft events, 30 speakers;
  - uid 1000, no internet.
- Dev override: `127.0.0.1:8000`, `/docs` 200, 0 `/_test` paths, reset without token 403.
- `sprint-0-status.md` §4d: every P0 item met except the first Gemini tool call.
- Docs updated on branch `s0/close-sprint-0` (not on `main`).

**Not run.** `scripts/first_tool_call.py` (A5: key not filled yet).

**Unsure.** The first clean-clone build attempt failed without a usable message; the retry passed. I suspect the flaky DNS, but this is not proven.
---

## 2026-11-05 — First Gemini tool call: Sprint 0 closed

**Done.**
- Gemini key in `.env` (filled by Aya, never shown).
- First API call: `SSL: CERTIFICATE_VERIFY_FAILED`. The cause was Avast HTTPS scanning (issuer "Avast Web/Mail Shield Root"). Aya added Avast exceptions for `generativelanguage.googleapis.com` and `api.github.com`; afterwards the issuer was Google Trust Services.
- Listed the Flash models for the key (22).
- Run log, all three tries in `logs/first_tool_call.jsonl`:
  - `gemini-3.8-flash`: 503 UNAVAILABLE, twice;
  - `gemini-3.5-flash` (served as `gemini-3.6-flash`): one `get_event(12)` call, correct answer, 5/5 checks, 761 tokens, 4.2 s, **passed**.
- `.env` now has `GEMINI_MODEL=gemini-3.5-flash`. The log does not contain the key (checked).
- `sprint-0-status.md` §4d: **P0 met, Sprint 0 closed.**

**Unsure / for the PL.** The requested and served model versions differ. S1-06 run logging must record `model_version` from every response.

**Next.** Step 4: S1-02 (gateway + MCP) on branch `s1/S1-02-gateway-mcp`.
---

## 2026-11-05 — CI fix on PR #1 (gitleaks job)

**Problem.** On the first `pull_request` run, `gitleaks/gitleaks-action@v2` failed with `403 Resource not accessible by integration` on `GET /repos/EyaNasfi/eventguard/pulls/1/commits`. The workflow token only had `contents: read`; the API asked for `pull_requests=read` (header `x-accepted-github-permissions`). The job never reached the scan. This was not a leak.

**Fix.** The `gitleaks` job now has job-level `permissions: contents: read, pull-requests: read`. Read-only; the other jobs are unchanged.

**Not yet verified.** The PR run after the push.