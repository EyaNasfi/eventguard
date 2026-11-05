---
title: EventGuard — Sprint 0 status (S1-00 audit)
author: Aya NASFI
date: 2026-11-02
task: S1-00
---

# EventGuard — Sprint 0 status

**Verdict: the Sprint 0 exit criterion (P0) is NOT met.** No EventGuard code exists in the workspace, so per the S1-00 stop rule no Sprint 1 work has started.

## 1. What was inspected

| Location | Result |
|---|---|
| `D:\OneDrive\Bureau\PFE` (workspace) | Empty folder. No files, no `.git`. This file is the first one in it. |
| Search of `C:\Users\Eya` and `D:\` (depth 4) for folders named `*eventguard*` / `*eventsim*` | Nothing found. |
| Search for `docker-compose*.yml` on the same roots | Only `D:\mlops\nasfi-eya-4ds10-ml_projet\` (an unrelated ML course project). |
| `C:\Users\Eya\Downloads` | Contains the Sprint 1 brief (`sprint-1-prompt.md`) and `Docker Desktop Installer.exe` (not yet installed). No EventGuard archive. |

## 2. Audit checklist

| Item asked by S1-00 | Status | Evidence |
|---|---|---|
| Folder layout / modules | **Absent** | Workspace is empty. |
| EventSim routes (method, path, role) | **Absent** | No EventSim code. |
| Six tables (FR-SIM-01) | **Absent** | — |
| Seeded generator | **Absent** | — |
| State-diff export (FR-SIM-07) | **Absent** | — |
| Outbox (FR-SIM-08) | **Absent** | — |
| Canaries (FR-SIM-09) | **Absent** | — |
| Reference duplication script (FR-SIM-10) | **Absent** | — |
| `docker compose up` on a clean checkout | **Cannot run** | No compose file; Docker is not installed (`docker` not on PATH, `C:\Program Files\Docker\...\docker.exe` missing). |
| Containers / host ports | **None** | — |
| Gemini model already called a tool | **No evidence** | No agent code, no logs, no n8n workflow in the workspace. (`Downloads\Chatbot documentaire RAG - Gemini Pinecone v6.json` is an n8n export but belongs to a different RAG chatbot; it was not opened and is not treated as EventGuard work.) |
| CI (tests, lint, gitleaks) | **Absent** | No repo, no CI config. |
| Test coverage | **N/A** | — |
| Threat model v0 | **Not found** | Not in the workspace. |

## 3. Toolchain on this machine

| Tool | Required by | Status |
|---|---|---|
| Python 3.12 | NFR-09 | Installed (`py -3.12`). Default `python` is 3.14 — the project must pin 3.12 explicitly. |
| Git | branches/commits/tags (rule 3, `tasks-v1`) | **Not installed / not on PATH.** |
| Docker Desktop + Compose | lab, DoD | **Not installed** (installer downloaded on 2026-11-02, not run). |
| gitleaks | SR-13 | Not installed locally (can run in CI only). |
| n8n | S1-03, S1-05 | Not present (would run as a container). |

## 4. Consequence for Sprint 1

Every S1 task depends on EventSim (routes for the gateway tools, seeds for the tasks, state diff for the checkers, reference script for the duplicate checkers). With nothing in place, the stop rule applies: P0 has to be delivered before S1-01.

Rebuilding P0 means, at minimum: EventSim (FastAPI + SQLModel, six tables, roles reader/editor/admin with per-user tokens, seeded generator, test-only reset/snapshot/state-diff endpoints, outbox, canaries, reference duplication script), `docker-compose.yml`, CI (pytest, ruff, mypy, gitleaks), and a threat model v0. This is several days of work and would consume most of the remaining sprint window (2 → 8 Nov).

## 4b. Update 2026-11-02 — P0 rebuilt (ADR-001)

The project lead chose to build P0 now. State after the rebuild:

| Item | Status | Evidence |
|---|---|---|
| Folder layout | `eventsim/` (platform), `tests/`, `docs/`, `.github/workflows/` | — |
| EventSim routes | Done, with the role matrix in `README.md` | `tests/test_eventsim_api.py` |
| Six tables (FR-SIM-01) | `edition, event, session, speaker, partner, attendee` (+ links, outbox, user, canary) | `test_six_business_tables_are_filled` |
| Seeded generator | Deterministic, fictional data. Seed 42 gives 3 editions (2025 closed, 2026 active, 2027 empty draft), 22 events, 30 speakers, 12 partners, 77 attendees | `test_same_seed_same_state` |
| State-diff export (FR-SIM-07) | `/_test/snapshot` + `/_test/state-diff` | `test_reset_snapshot_diff_cycle` |
| Outbox (FR-SIM-08) | `POST /notifications` stores the message; nothing is sent | `test_notifications_go_to_outbox` |
| Canaries (FR-SIM-09) | 4 markers `EG-CANARY-REC-*` in attendee / partner notes, not searchable | `test_canaries_planted_in_private_fields` |
| Reference script (FR-SIM-10) | `python -m eventsim.reference --source 2026 --target 2027` | `tests/test_eventsim_reference.py` (5 tests); run live over HTTP: 10 events copied |
| `docker compose up` | `docker-compose.yml` written. **Not run on this machine** (no Docker). The CI `lab` job runs it and then the reference script | `.github/workflows/ci.yml` |
| Host ports | None in `docker-compose.yml`. The dev override binds `127.0.0.1:8000` | — |
| CI | ruff, mypy (strict), pytest + coverage (fail under 80%), gitleaks, lab job. **Not run yet**: no Git remote | — |
| Coverage | 97% on `eventsim/` (local run, 33 tests) | `pytest --cov=eventsim` |
| Threat model v0 | `docs/threat-model-v0.md` | — |
| Gemini tool call | Still none (comes with S1-02/S1-05) | — |

**P0 exit criterion:** met for the code, verified with local tests and a live uvicorn run. `docker compose up` is still unverified until Docker is installed or CI runs.

## 4c. Update 2026-11-04 — `docker compose up` verified (working tree, not yet a clean clone)

Run by the agent on this machine (Docker 29.9.2, Compose v5.6.1, WSL 2):

| Check | Result |
|---|---|
| `docker compose up -d --build --wait` | eventsim **running (healthy)** |
| Ports published to the host | **none**: `docker compose ps` shows `8000/tcp` only, `docker compose port eventsim 8000` is empty, `http://127.0.0.1:8000/health` is unreachable from Windows |
| Reference script inside the compose network | `docker compose exec -T eventsim python -m eventsim.reference --source 2026 --target 2027` → **10 events** in 2027, all `draft`; speakers still 30 |
| Container user | `uid=1000(eventsim)`, not root |
| Internet from `lab_internal` | blocked (`ConnectError: name resolution`), as designed |

`.env` was created by the agent from `.env.example`, with random EventSim tokens that were never printed; the Gemini fields are left for Aya. Still missing for P0: the **clean-clone** run (needs Git), the **CI** run (needs the remote), and the **first Gemini tool call** (needs the key).

## 4d. Update 2026-11-05 — Step 2 checks (PL decision #1)

| P0 exit item | Status | Evidence |
|---|---|---|
| Git baseline | **Met** | Commit `c5cea87` "S0: EventSim baseline", the only commit on `main`, annotated tag `sprint-0`. Hooks passed (gitleaks, ruff, ruff format, mypy). `gitleaks git .` over the history: no leaks. |
| Private remote | **Met** | `https://github.com/EyaNasfi/eventguard.git`. Aya pushed `main` and `sprint-0` (push output in the session log). |
| CI green | **Met (reported by Aya)** | First run on `main`: jobs `checks`, `gitleaks` and `lab` all green. Aya read this on the GitHub Actions page. The agent could not read the run itself (`api.github.com` unreachable from this PC, see `environment.md`). |
| Clean-clone `docker compose up` | **Met** | `git clone` into `D:\dev\eventguard-clean` (outside OneDrive, HEAD = `origin/main` = `c5cea87`). `.env` copied from `.env.example` only, `docker compose build --no-cache`, `up -d --wait` → eventsim **healthy**, ports `8000/tcp` only (not published). The first build attempt failed without a usable error, probably the flaky DNS; the retry built cleanly. |
| Reference script inside the compose network | **Met** | `docker compose exec -T eventsim python -m eventsim.reference --source 2026 --target 2027` → exit 0. 2027: **10 events, all `draft`**; speakers still **30**. Container `uid=1000(eventsim)`; internet from `lab_internal` blocked (`ConnectError`). |
| Dev override | **Met** | `-f docker-compose.yml -f docker-compose.dev.yml` → `127.0.0.1:8000->8000/tcp`, `/docs` 200, `/openapi.json` 23 paths, **0** under `/_test`, `POST /_test/reset` without `X-Test-Token` → 403. Stack removed afterwards (`down -v`). |
| First Gemini tool call (`scripts/first_tool_call.py`) | **Met** (2026-11-05 10:07 UTC) | Free-tier key. Model requested `gemini-3.5-flash`; the API reported `model_version = gemini-3.6-flash`. One `get_event(event_id=12)` call; the answer gave name "People Forum", venue "Halle Brumaire" and date 2026-07-13, so all 5 checks were true. 761 tokens, 4.2 s, exit 0. Two earlier tries with `gemini-3.8-flash` got `503 UNAVAILABLE` (high demand), and both are logged as failed. Record: `logs/first_tool_call.jsonl` (gitignored; the key is absent, checked). |

**Verdict (2026-11-05): the P0 exit criterion is met. Sprint 0 is closed.**

**Open point for the project lead.** Google served `gemini-3.6-flash` to a request for `gemini-3.5-flash`. The served version must therefore be logged on every run (S1-06), and the config hash alone does not pin the model.

## 5. Blocking questions for the project lead (2026-11-02; answered by PL decision #1)

1. **Where is the Sprint 0 code?** Is there a remote repository (GitHub/GitLab URL) or an archive that should be cloned here?
2. **If Sprint 0 was never built**, do you want me to build P0 now (and re-plan S1 scope), or will you provide the existing work?
3. **Requirements Specification v1.0** is not in the workspace. Please add it (e.g. `docs/requirements-v1.0.*`) — the FR-SIM-01 table list and the route/role matrix are needed to build or verify EventSim without guessing.
4. **Install Git and Docker Desktop** on this machine (or confirm I should use another environment). Neither is available, so commits, branches, `docker compose up` and the DoD cannot be checked here.
