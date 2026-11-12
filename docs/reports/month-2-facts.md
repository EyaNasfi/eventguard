---
title: EventGuard — Facts for monthly report 2
author: Aya NASFI
date: 2026-11-12
---

# Facts for monthly report 2 (due 14 November 2026)

This is a **facts-only digest**. Aya writes the report from it. Each fact names its source. "To confirm by Aya" means the repo holds no source for it.

## 1. Sprint 0 (P0: the simulated platform)

| Fact | Value | Source |
|---|---|---|
| Audit found no Sprint 0 code | 2026-11-02, empty workspace | `docs/sprints/sprint-0-status.md` §1–2 |
| Decision to rebuild P0 inside Sprint 1 | 2026-11-02 | ADR-001, `docs/decisions.md` |
| P0 built (EventSim, CI, threat model v0) | 2026-11-02 | `sprint-0-status.md` §4b |
| Baseline commit and tag | `c5cea87` "S0: EventSim baseline", tag `sprint-0`, 2026-11-05 | `sprint-0-status.md` §4d; `git tag` |
| Exit criterion met, Sprint 0 closed | 2026-11-05 | `sprint-0-status.md` §4d (verdict) |
| Exit evidence | private remote, CI green (read by Aya), clean-clone `docker compose up` healthy, reference script inside the network, dev override, first Gemini tool call | `sprint-0-status.md` §4d table |
| Tests | 96 passed | `pytest` (re-run 2026-11-12 on local `main`: 96 passed) |
| Coverage on `eventsim/` | 97% (2026-11-02); 97% re-measured 2026-11-12 | `docs/sprints/sprint-1-log.md` (2026-11-02 entry); `pytest --cov=eventsim` |
| Reference script result | 2026 → 2027: **10 draft events**, speakers still 30 | `sprint-0-status.md` §4c–4d; `tests/test_eventsim_reference.py` |
| Reference script duration | **2.0–2.3 s** per run (3 runs, seed 42, EventSim in Docker, measured over HTTP from the host) | measured 2026-11-12 for this digest; no earlier record in the repo |
| First Gemini tool call | model requested `gemini-3.5-flash`, served `gemini-3.6-flash`; one `get_event(12)` call; 5/5 checks; **761 tokens**, 4.2 s; passed | `sprint-0-status.md` §4d |
| Earlier failed tries | `gemini-3.8-flash`: 503 "high demand", twice | `sprint-0-status.md` §4d |
| Repeat run (second PC) | same script, `gemini-3.5-flash` served as `gemini-3.6-flash`; passed; 663 tokens; 37 s | `logs/first_tool_call.jsonl` on this PC (gitignored), 2026-11-12 |

## 2. Sprint 1 (2 → 8 November)

| Task | Status | Evidence |
|---|---|---|
| S1-00 Repository audit | Done | `sprint-0-status.md` |
| S1-01 Configurations C0–C4 | Partial: C0 complete, C1–C4 stubs with every layer off | `config/configurations.yaml`; `tests/test_config.py` (11 tests) |
| S1-02 Gateway + MCP server | Partial: done on branch `s1/S1-02-gateway-mcp`, **not merged** | `sprint-1-log.md` on that branch; ADR-003 |
| S1-03 n8n | Not started | `docs/START-HERE.md` §8 |
| S1-04 Procedure sheets + retrieval | Not started | `START-HERE.md` §8 |
| S1-05 Agent in n8n | Not started | `START-HERE.md` §8 |
| S1-06 Run logging | Not started | `START-HERE.md` §8 |
| S1-07, S1-08 Tasks, smoke run | Not started | `START-HERE.md` §8 |
| S1-09 | Moved to Sprint 2 | PL decision #1 (`sprint-1-log.md`) |
| S1-10 | Not started; task name not recorded | `START-HERE.md` §8 |

**Gateway facts** (branch `s1/S1-02-gateway-mcp`, source: ADR-003 and its `sprint-1-log.md` entry of 2026-11-05):

- **Tools:** 27 C0 tools, the same list as `config/configurations.yaml`.
- **Tests:** 77 gateway tests (174 in total on that branch); 95% coverage on `gateway/`.
- **Transport:** MCP over Streamable HTTP at `http://gateway:8100/mcp`, stateless. SDK `mcp==2.3.0`, low-level `Server`.
- **Authentication:** one bearer token per role (`GATEWAY_TOKEN_*`), constant-time compare. Each token maps to one EventSim user; the gateway sends only that user's EventSim token.
- **Hard deny rule:** `raw_api_call` refuses every `/_test/*` path, including encoded forms, and `DELETE`. Refusals are logged.
- **Network:** internal Docker network only, no host port, not even in dev.
- **Docker probe:** no or wrong bearer → 401; reader `create_event` → refused by EventSim (403); editor `create_event` in 2027 → ok.

**Configuration facts** (source: `config/loader.py`, `tests/test_config.py`, `sprint-1-log.md` S1-01 entry):

- Selected with `EVENTGUARD_CONFIG`; no silent default.
- Temperature 0.0 and max output 2048 tokens are fixed in the file.
- The config hash is SHA-256 of the resolved config. It includes the model name and the system-prompt hash.
- Nine layer flags per configuration; all are off in C0–C4 today.

## 3. Decisions (one line each)

| Decision | Content | Source |
|---|---|---|
| ADR-001 | Rebuild Sprint 0 inside Sprint 1 | `docs/decisions.md` |
| ADR-002 (+ rev. 1) | EventSim data model, role matrix, canaries, `draft/active/archived`, no delete, no cascade | `docs/decisions.md` |
| ADR-003 | MCP SDK 2.3.0, Streamable HTTP, one bearer per role | `docs/decisions.md` on branch `s1/S1-02-gateway-mcp` |
| ADR-004 | Never push without Aya's explicit request | `docs/decisions.md` |
| PL decision #1 | Environment first, close Sprint 0 for real, align EventSim with the spec; S1-09 to Sprint 2 | `sprint-1-log.md` |
| PL decision #2 | Corrected role matrix and canary rules (given in chat, recorded on 2026-11-12) | `docs/decisions.md` |
| PL decision #3 | Overnight web front-end run (Phases 1–3), no push | `docs/overnight-log.md` |

## 4. Problems met and how they were solved

| Problem | Solution | Source |
|---|---|---|
| **WSL / Docker:** `wsl --install` failed; Windows component store corrupted (DISM error 14098) | DISM RestoreHealth + sfc, then an in-place Windows repair install (26H2); WSL 2.7.14 and Docker 29.9.2 installed on 2026-11-04 | `docs/environment.md` |
| **Git:** not installed at the audit | Git 2.56.0, gitleaks 8.30.1 and gh 2.103.3 installed with winget, hashes verified | `environment.md` |
| **gitleaks pre-commit hook** downloaded Go from `go.dev`, which DNS could not resolve | Hook switched to the installed gitleaks binary | `sprint-1-log.md` (2026-11-05) |
| **Avast HTTPS scanning:** `CERTIFICATE_VERIFY_FAILED` on Gemini, corrupted `pip install` | Avast exceptions for Gemini, GitHub, PyPI and Docker Hub | `environment.md`; `sprint-1-log.md` |
| **Avast breaks loopback `/mcp`** requests on the host | Host tests use in-memory ASGI transports; Docker traffic unaffected | ADR-003 |
| **VPN/proxy DNS** (fake-IP mode): `api.github.com`, `go.dev` fail at times | Aya reads CI on github.com; turn off the VPN when needed | `environment.md` |
| **CI gitleaks job** got 403 on pull requests | Job permission `pull-requests: read` added | `sprint-1-log.md` (2026-11-05) |
| **Gemini usage limits:** `gemini-3.8-flash` gave 503 "high demand" | Use `gemini-3.5-flash`; log the served version on every run | `sprint-0-status.md` §4d |
| **Edge processes:** 28 headless Edge processes (plus 82 children) left by screenshot captures | Stopped; capture script now always closes its browser | `docs/overnight-log.md` (05:40) |
| **Leftover dev servers** on ports 5173–5175 | Not stopped by the agent (permission denied); Aya to close them | `overnight-log.md` (07:50) |
| Other usage limits (for example, coding-agent limits) | — | to confirm by Aya |

## 5. The web console (a testing tool, not a result)

- **What it is:** a React web app in `web/`, merged into the local `main` on 2026-11-12. Pages: Assistant, Approvals, Audit log, Events. Source: `docs/frontend/status.md`.
- **What is real:** the Events page in live mode reads and archives real EventSim data through a dev proxy. Source: `web/README.md`, `docs/START-HERE.md` §6.
- **What is sample data:** Assistant, Approvals and Audit log show fictional sample data, labelled "Sample data · not measured". Gateway, Attack lab and Results are paused. Source: `START-HERE.md` §6.
- **Do not quote it as a result:** the console shows how results will look. It measures nothing.

## 6. Numbers NOT available yet

| Number | Why not | Planned |
|---|---|---|
| Tokens per agent run | No agent loop runs yet (only the one-tool test script) | Sprint 2 smoke run (S2-07) |
| C0 utility (task success rate) | The 40 tasks and checkers do not exist yet | Sprint 3 pilot |
| ASR (attack success rate) | The attack bench is not built | after Sprint 3 |
| False refusals, approvals per task | Need protection layers (C1–C4) | later sprints |
