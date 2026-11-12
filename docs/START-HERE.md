---
title: EventGuard — Start here
author: written for Aya NASFI by the coding agent
date: 2026-11-10
---

# Start here

This page explains what exists in the repository today, in plain English. Everything below was checked in the repo on 2026-11-10. When something was not checked, or does not exist yet, the text says so. Tonight's results are at the end (section 12).

A few words used everywhere:

- **Agent**: an AI model (here Gemini) that reads a request, plans steps and calls *tools* to carry them out.
- **Tool**: a function the agent may call, such as `list_events` or `archive_record`. Each tool turns into one call to the event platform.
- **MCP (Model Context Protocol)**: a standard way for an agent to discover and call tools over HTTP.
- **Gateway**: our own service that sits between the agent and the platform. Every tool call passes through it, so it can check, block, log or ask a person first.
- **EventSim**: our simulated event platform. It holds editions, events, sessions, speakers, partners and attendees. All its data is invented.
- **Configuration C0–C4**: which protections the gateway switches on. C0 has none; C4 has all of them.
- **Attack**: a request or a piece of planted text that tries to make the agent do something it should not do.

## 1. EventGuard in 5 lines

1. **Problem:** an AI assistant that can write to an event platform can be tricked. Text hidden in a record can steer it to leak data or archive things, and nobody notices.
2. **Agent:** Gemini, run from an n8n chat, plans the duplication (2026 → 2027) or archiving of editions and calls tools.
3. **Gateway:** every tool call goes through EventGuard's gateway. It enforces role rights, archive-never-delete, write quotas, output filtering, "untrusted text is data", a signed single-use human approval for writes, and a hash-chained audit log.
4. **Attacks:** a bench of 80–100 attacks in 8 families, for example instructions hidden in event descriptions.
5. **Measurement:** run the bench against C0…C4 and compare attack success, task success, false refusals and approvals per task, each with confidence intervals.

## 2. The big picture

```mermaid
flowchart LR
  user([Event staff]) -->|chat| n8n["n8n chat + AI Agent node<br/>(not built)"]
  n8n -->|prompt, history| gemini[(Gemini API<br/>external)]
  n8n -->|MCP tool calls<br/>bearer per role| gw["Gateway<br/>gateway/ (branch only)"]
  gw -->|HTTP, user's token| es["EventSim<br/>eventsim/"]
  gw -.->|search_procedures| vs[("Vector store<br/>procedure sheets (not built)")]
  bench["Attack bench + harness<br/>(not built)"] -->|runs tasks/attacks| n8n
  bench -->|/_test/* with test token| es
  web["Web UI<br/>web/ (mock data)"] -.->|dev proxy, read/archive| es

  subgraph B3["Untrusted: what the model asks for"]
    n8n
  end
  subgraph B5["Untrusted: text inside records"]
    es
  end
```

Trust boundaries, from `docs/threat-model-v0.md`:

- **B1**: human → n8n.
- **B2**: n8n → Gemini.
- **B3**: agent → gateway (untrusted; the model can be steered).
- **B4**: gateway → EventSim (trusted; the gateway holds the EventSim tokens).
- **B5**: EventSim → agent (untrusted content; any text field may carry an injection).
- **B6**: harness → `/_test/*` (harness only, separate token).

| Component | Folder | Status | What works today | Requirement IDs (as cited in the repo) |
|---|---|---|---|---|
| EventSim (simulated platform) | `eventsim/` | **built** | 6 business tables, roles reader/editor/admin, archive-only, seeded data (seed 42), canaries, outbox, `/_test/*` harness routes. 96 tests at last record. | FR-SIM-01 … FR-SIM-10 |
| Configuration C0–C4 | `config/` | **partly built** | C0 complete. C1–C4 are stubs with every layer off. Strict loader and config hash. 11 tests. | FR-AGT-02, FR-AGT-07, FR-GW-15, NFR-02 |
| Gateway + MCP server | `gateway/` on branch `s1/S1-02-gateway-mcp` | **partly built (not merged)** | MCP over HTTP; 27 C0 tools; bearer token per role; hard deny of `/_test/*`; empty layer pipeline (C0). 77 tests on that branch. **Not on `main`.** | FR-AGT-03, FR-GW-01, FR-GW-04, SR-01, SR-10 (hash prepared), SR-14 |
| Agent in n8n | none | **not started** | Only `scripts/first_tool_call.py`: one Gemini call to one tool (Sprint 0 proof). | FR-AGT-* (see the spec) |
| Procedure sheets + vector store | none | **not started** | `search_procedures` exists in the gateway but answers "not available yet". | not checked (spec not in repo) |
| Protection layers (C1–C4) | none | **not started** | Flags exist in config; no layer is implemented. | SR-*, FR-GW-* (see the spec) |
| Attack bench, harness, results | none | **not started** | EventSim's `/_test/*` (reset, snapshot, state diff, canaries) is ready for it. | not checked (spec not in repo) |
| Web UI | `web/` | **partly built** | Assistant, Approvals, Audit log, Events and the shell, running on bundled fictional data. Live mode reads/archives on a real EventSim (section 6). | — (not in the spec as far as checked) |

The Requirements Specification v1.0 is **not in the repository**, so the IDs above are only the ones the code and docs cite.

## 3. Folder tour

| Folder | What it contains | Open first |
|---|---|---|
| `eventsim/` | The simulated platform (FastAPI + SQLModel). | `api.py`: every route, with the role matrix in its docstring. `models.py`: the tables. `seed.py`: how the fictional data and canaries are generated. |
| `config/` | The C0–C4 configurations. | `configurations.yaml`: tools and layer flags per configuration. `loader.py`: validation and the config hash. |
| `tests/` | pytest suite for EventSim and config. | `test_eventsim_api.py`: the role matrix test. `test_eventsim_canaries.py`: one test per canary. |
| `scripts/` | Helper scripts. | `first_tool_call.py`: the first Gemini tool call. `state_hash.py`: hash of the database state. |
| `docs/` | Decisions, threat model, sprint logs, guides. | `decisions.md` (ADRs), `threat-model-v0.md`, `sprints/sprint-1-log.md`. |
| `web/` | The React front end (built in this session). | `src/api/types.ts`: the data contract. `src/pages/Assistant.tsx`: the main screen. `README.md`: how to run it. |
| `.github/workflows/` | CI (continuous integration: checks run on every push). | `ci.yml`. |
| `.claude/`, `.agents/`, `.codex/`, `.github/agents`, `.github/skills` | Design and animation skills used by the coding agent (Impeccable, Emil Kowalski skills). Not product code. | — |
| `.impeccable/` | Design notes and review screenshots. | `surfaces/web-src-pages-assistant-tsx.md`: the chosen visual direction. |

## 4. One request, step by step: "duplicate 2026 into 2027"

**Target design** (what the project aims for):

1. The editor types the request in the n8n chat.
2. The agent (Gemini) plans: read edition 2026, create draft events and sessions in 2027, relink speakers and partners, never copy registrations.
3. Each tool call goes to the gateway over MCP with the editor's bearer token.
4. The gateway checks the role, the tool allowlist and the quotas, filters outputs, and marks record text as data (spotlighting).
5. Reads go through. Writes are held, and a preview (what will be created) is shown to the editor.
6. The editor signs the preview once. The gateway runs the writes on EventSim with the editor's own token and writes each decision to the hash-chained audit log.

**Today:**

| Step | Exists? |
|---|---|
| 1. Chat in n8n | **No** (S1-03/S1-05 not started). |
| 2. Agent planning | **No.** Only the one-tool Sprint 0 script exists. |
| 3. Gateway over MCP with a bearer token | **Yes, on an unmerged branch** (C0: nothing is checked except role tokens and the `/_test` deny rule). |
| 4. Checks, filters, spotlighting | **No** (C1–C4 layers not implemented). |
| 5. Preview and approval | **No in the backend.** The web UI shows how it will look, on fictional data. |
| 6. Writes on EventSim | **Yes.** `eventsim/reference.py` does the whole duplication through the public API and is the ground truth: 10 draft events in 2027. |
| Audit log | **No in the backend.** The web UI shows it on fictional data. |

## 5. How to run each piece (PowerShell, from the repo root)

```powershell
# One-time Python setup
py -3.12 -m venv .venv
.\.venv\Scripts\pip install -e ".[dev]"

# Tests and checks
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\ruff check . ; .\.venv\Scripts\ruff format --check . ; .\.venv\Scripts\mypy

# EventSim in Docker, reachable from this PC on 127.0.0.1:8000 (needs Docker Desktop running and a filled .env)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build --wait

# Reference duplication 2026 -> 2027 (needs EventSim running and EVENTSIM_TOKEN_ADMIN in the environment)
$env:EVENTSIM_URL = "http://localhost:8000"
.\.venv\Scripts\python -m eventsim.reference --source 2026 --target 2027

# Web UI, mock mode (fictional data, no backend needed)
cd web
npm install
npm run dev            # then open http://localhost:5173

# Web UI, live mode (needs EventSim on 127.0.0.1:8000): see web/README.md
#   copy web/.env.example to web/.env.local, set VITE_USE_MOCKS=false and the three local tokens
```

`npm` lives in `C:\Program Files\nodejs`. If PowerShell says `npm` is not found, run `$env:Path = "C:\Program Files\nodejs;$env:Path"` first.

## 6. Real vs mock in the web UI

| Page | Mock mode (default) | Live mode (`VITE_USE_MOCKS=false`) |
|---|---|---|
| Events | Fictional copy of seed 42 | **Real EventSim data** (editions, events, sessions, speakers, partners, attendees for admin, archive/unarchive) |
| Assistant | Scripted demo agent, fictional | Sample data: the agent and gateway are not connected yet |
| Approvals | Sample data | Sample data |
| Audit log | Sample data | Sample data |
| Gateway, Attack lab, Results | Paused ("coming later") | Paused |

Every page that shows sample data carries a visible "Sample data · not measured" label.

## 7. Decisions so far

- **ADR-001**: rebuild Sprint 0 inside Sprint 1, because the audit found no Sprint 0 code.
- **ADR-002 (+ revision 1)**: the EventSim data model and role matrix. Editors write only in draft editions, only admins read attendees, nothing is deleted, there are four canaries, and statuses are `draft | active | archived`.
- **ADR-003** (on the gateway branch): MCP SDK `mcp==2.3.0`, low-level `Server`, Streamable HTTP, one bearer token per role.
- **PL decision #1**: environment first, then close Sprint 0 for real, then align EventSim with the spec. S1-09 moves to Sprint 2. One branch per task.
- **PL decision #2**: **not checked.** No record of it in the repo; ask the project lead what it was.
- **PL decision #3** (2026-11-10, overnight brief): finish the web front end Phases 1–3, wire live mode to EventSim, commit on a local branch, never push without Aya's request, and pause Phases 4–7 (Gateway page until Sprint 5; Attack lab and Results after the first real results; polish and demo page in Sprint 8).

## 8. Sprint status, honestly

**Sprint 0 exit criterion: met** (2026-11-05). The evidence is in `docs/sprints/sprint-0-status.md` §4d:

- the Git baseline;
- the private remote;
- CI green (reported by Aya);
- a clean-clone `docker compose up`;
- the reference script inside the network;
- the dev override;
- the first Gemini tool call.

**Sprint 1:**

| Task | Status | Evidence / note |
|---|---|---|
| S1-00 Repository audit | **done** | `sprint-0-status.md` |
| S1-01 Configuration C0–C4 | **partial** | On `main`; C0 full, C1–C4 stubs; 11 tests. The tool list is not yet checked against the gateway registry. |
| S1-02 Gateway + MCP (C0 tools) | **partial** | Done on branch `s1/S1-02-gateway-mcp`, 77 tests + Docker probe. **Not merged.** n8n compatibility only simulated. |
| S1-03 (n8n) | **not started** | needs Docker + n8n |
| S1-04 (procedure sheets, embeddings) | **not started** | `search_procedures` answers "not available yet" |
| S1-05 (agent in the n8n chat) | **not started** | manual guide L11 says "not built yet" |
| S1-06 (run logging, model_version) | **not started** | |
| S1-07, S1-08 (tasks, smoke run) | **not started** | manual guide L12 says "not built yet" |
| S1-09 | **moved to Sprint 2** | PL decision #1 |
| S1-10 | **not started** | The task name is not recorded in the repo. |
| Web UI (not an S1 task) | **Phases 1–3 built**, 4–7 paused | `docs/frontend/status.md` |

**Tested:** the EventSim routes and role matrix, canaries, the harness, the reference script, config, and the gateway (on its branch). The web UI is checked by typecheck, lint, build and screenshots.

**Not tested:** anything involving n8n or a real agent loop, the protection layers, the bench, the web UI's live mode against Docker (see section 12).

## 9. Reading path (about 60 minutes)

1. **5 min:** this page, sections 1–2.
2. **10 min:** `docs/threat-model-v0.md`. Look for the boundaries B1–B6 and threats T1–T10. They are what the gateway and the bench are for.
3. **10 min:** `docs/decisions.md`, ADR-002 revision 1. Look at the role matrix and the canary table.
4. **10 min:** `eventsim/api.py`, the docstring and two routes (`create_event`, `archive_record`). Find where 403 and 409 are raised.
5. **5 min:** `config/configurations.yaml`. Look at the 27 tools and the nine layer flags.
6. **10 min:** `git show origin/s1/S1-02-gateway-mcp:gateway/tools.py`. Look at how a tool becomes one HTTP call, and at the `/_test` deny rule.
7. **10 min:** run the web UI (`cd web; npm run dev`) and click **Demo guide → step 1, 2, 3**. Compare step 2 (C0, data leaks) with step 3 (C3, blocked).

## 10. Ten self-check questions

1. Why does EventSim archive and never delete?
2. What is a canary, and where are the four canaries?
3. What does the gateway check in C0 today, and what will C3 add?
4. Why does the gateway hold the EventSim tokens instead of the agent?
5. Why does `/_test/*` need its own token, and why is it never in the front end?
6. What is an indirect prompt injection? Give the example used in the demo.
7. Why is a write approval "single-use" and "bound to the preview"?
8. What makes the audit log tamper-evident?
9. What do the four metrics measure, and why report confidence intervals?
10. Why do editors write only in draft editions?

## 11. What Aya must decide or do next

- Decide when to **merge `s1/S1-02-gateway-mcp`** (the gateway is not on `main`).
- Review and, if happy, **push the local branch `s1/web-frontend-p1-3`** (nothing was pushed tonight).
- Add the **Requirements Specification v1.0** to the repo so requirement IDs can be checked.
- Tell the agent what **PL decision #2** was (it is not recorded).
- Start **Docker Desktop** before the next session if live checks against the dockerised EventSim are wanted.
- Stop three leftover dev servers from tonight if they are still running: `node … vite --port 5173`, `--port 5174` (live mode) and `--port 5175`. Stopping the agent task did not end them, and the agent was not allowed to kill them (see `docs/overnight-log.md`). Task Manager → Node.js processes, or restart the PC.
- Install gitleaks on this PC (`winget install Gitleaks.Gitleaks`) and run `gitleaks git --staged` / `gitleaks detect` before pushing.

## 12. Tonight's results (2026-11-10)

- **Built:** web UI Phases 1–3: the Assistant, Approvals, Audit log, Events, shell and component gallery. Gateway, Attack lab and Results are paused pages marked "coming later". Screenshots are in `docs/frontend/screenshots/`, page by page in `docs/frontend/status.md`.
- **Phase 3 review:** every P1 finding fixed, and the cross-page inconsistencies cleaned up. The table is in `docs/overnight-log.md` (Step 3).
- **Live mode:**
  - The Events page reads and archives on a real EventSim through the dev proxy.
  - **Docker was not running**, so the browser checks against the dockerised EventSim were **not run**.
  - The same API checks were run in-process against the real EventSim code, and all of them passed. "EventSim down" shows a clear error.
  - The built bundle has no test-endpoint strings and no tokens.
- **Committed** on the local branch `s1/web-frontend-p1-3`. **Not pushed, not merged.**
  - gitleaks is not installed on this PC. The staged files were scanned for `.env` values and secret patterns instead: 0 hits.
- **Rules recorded:** never push without your explicit request (ADR-004, `CLAUDE.md`). Subagents use Sonnet (`.claude/settings.json`).
- **Look at first:** the summary at the end of `docs/overnight-log.md`.

---

### Answers to section 10

1. Deletion destroys evidence and cannot be undone. Archive hides a record, unarchive restores it, and every change stays visible in the state diff. It also turns "mass delete" attacks into reversible mass archives, which quotas then cap.
2. A canary is an invented secret-looking value planted in a private field. If it ever appears where it should not (the outbox, an answer), data leaked. There are four: three attendee notes, an internal note on event 16, a fake mailer key in `/config`, and partner 3's notes.
3. In C0 the gateway checks only who you are (bearer → EventSim user) and refuses `/_test/*`. C3 adds least privilege, quotas, preview + approval (from C2), the output filter, spotlighting and the audit log.
4. So a manipulated agent can never use a stronger token than the person chatting. EventSim checks roles again, so the gateway cannot raise privileges.
5. `/_test/*` can reset and read the whole database. Only the evaluation harness may use it. Anything in the browser bundle is public, so the token must never be there.
6. Instructions hidden in data the agent reads, not in the user's message. The demo hides a note in the People Forum 2026 description telling the agent to email partner contract references outside.
7. So a person approves exactly what will run. A changed plan needs a new signature, and a stolen signature cannot be replayed.
8. Each entry stores the hash of the previous one. Editing any entry changes its hash and breaks every link after it, and "Verify chain" finds the first break.
9. Attack success (lower is better), task success (higher), false refusals (lower) and approvals per task (cost to people). Intervals show whether a difference between configurations is real or noise, given the number of runs.
10. Published editions are live. Draft editions are where new work is prepared safely, so a mistake or an attack cannot change what attendees already see.
