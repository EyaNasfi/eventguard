---
title: EventGuard — Sprint 2 log
author: Aya NASFI
---

# Sprint 2 log (13 → 22 November 2026)

Each entry: what was done, files, why, how to verify (PowerShell), unsure points, **next**.
Resume point: the last entry's **Next** line.

## PL decision #4 — Sprint 2 brief (received 2026-11-12)

**Sprint goal.** The naive agent (C0) works end to end: n8n chat → Gemini → MCP gateway → EventSim. It answers procedure questions and cites the sheet it used. The 40 legitimate tasks with their checkers are written, tested and frozen.

**Why.** Sprint 1 finished only S1-00 to S1-02. Sprint 2 = the unfinished Sprint 1 work. The 50-run pilot and the C0 utility measurement move to Sprint 3 (23 Nov – 6 Dec). The web front end stays paused.

**Rules.**
1. No push, no pull request, no remote change unless Aya asks in so many words.
2. Merge finished task branches into the **local** `main` only when pytest, ruff, mypy, web checks and gitleaks pass; `--no-ff`, message names the task.
3. One branch per task (`s2/<task-id>-short-name`); commits name task and requirement IDs.
4. Subagents: `sonnet` (or `haiku`), one at a time.
5. After each task: a log entry here and matching L-checks in `docs/manual-test-guide.md`.
6. Security: no secret in Git, prompts, workflow exports or logs; the agent never holds EventSim tokens (SR-01); `/_test/*` never reachable by the agent (FR-SIM-06); no delete; fictional data only; gitleaks before every commit.
7. Gemini: free tier, `GEMINI_MODEL`, fixed temperature, retry with backoff on 429; report calls and tokens.
8. Blocked > ~2 h: log it, take the fallback, continue. Never drop scope silently or invent a result.
9. No EventSim API contract change without an ADR; prefer adding over modifying.

**Backlog.** Step 0 (month-2 facts), then S2-01 gateway merge (FR-GW-01, FR-AGT-07) · S2-02 n8n + identity spike (FR-AGT-01, FR-GW-04, SR-14) · S2-03 18 procedure sheets + retrieval (FR-AGT-04) · S2-04 n8n naive agent C0 (FR-AGT-01/02/05/06, SR-12) · S2-05 run logging (FR-AGT-08, NFR-02) · S2-06 40 tasks + checkers, frozen (FR-EVAL-01, D4) · S2-07 agent client + smoke run · S2-08 docs (NFR-11) · S2-09 verification campaign, then stop.
**Cut order if short:** token export first (keep tool-call logging), then smoke run down to 3 tasks. Never cut S2-04 or S2-06.

## PL decision #5 — go for an unattended overnight run (received 2026-11-12)

- Both pushes of `s1/web-frontend-p1-3` accepted (see the push report below). The no-push rule is unchanged.
- Everything is pre-approved; blocked items are logged with their fallback, then the next task starts.
- gitleaks: install at user scope (winget), else the official release in `.tools/`, else the substitute scan.
- PL decision #2 text given; record it, check EventSim against it, fix on `s2/S2-00-role-matrix` if needed.
- Docker, the local n8n owner account, the n8n API key (fictional values in `.env` only) and typing the demo prompts are pre-approved.
- New task right after Step 0: rewrite `README.md` as a 5-minute read for Aya; update it again at the end.
- Hard limits: no push, no tag push, no PR, no remote change, no `web/` change, no secret printed, stop every process I start.

## 2026-11-12 — Push report (rule 1, first action)

`git reflog` and the remote-tracking ref show two pushes of `s1/web-frontend-p1-3`, both on 2026-11-12:

| Time (+01:00) | Commit | Who | How |
|---|---|---|---|
| 19:17:00 | `624f841` (2 commits) | **The coding agent**, at Aya's explicit request in chat | The 2 local commits were rewritten so the author and committer are Aya NASFI <eya.nasfi@esprit.tn> with no co-author lines (contents unchanged). The remote URL was set to `https://EyaNasfi@github.com/EyaNasfi/eventguard.git`, then `git push -u origin s1/web-frontend-p1-3` via Git Credential Manager. |
| 21:15:44 | `771eebe` "Web UI: console restyle after the reference page" | **Aya** (confirmed in PL decision #5) | Committed at 21:15:39, pushed 5 s later. |

No other push: `main`, tags and PRs untouched on the remote. **Accepted by PL decision #5.**

## 2026-11-12 22:55 — Setup for the run

- **gitleaks 8.30.1** installed with `winget install --id Gitleaks.Gitleaks -e --scope user` (first option of PL decision #5). Path: `%LOCALAPPDATA%\Microsoft\WinGet\Links\gitleaks.exe`.
- **Docker** already running (29.6.1); EventSim container healthy.
- Stopped the Vite dev server that the agent itself had started earlier in this session (port 5173). No other process was touched.
- **Merged `s1/web-frontend-p1-3` into local `main`** (`--no-ff`, merge `e4e7627`). Reason: START-HERE, CLAUDE.md, ADR-004 and the decisions that Sprint 2 updates live on that branch. Checks before the merge: pytest 96 passed; ruff and ruff format clean; mypy clean; web typecheck, lint and build clean; `gitleaks git` no leaks. `gitleaks dir` found 4 hits, all in gitignored, untracked files (`web/.env.local` tokens and two `.impeccable/questions` caches): not in Git.
- **Commit identity:** local `user.name = Aya NASFI`, `user.email = eya.nasfi@esprit.tn` (as asked on 2026-11-12); commits carry no co-author lines.

**How to verify.**
```powershell
gitleaks version                                  # 8.30.1
git log --oneline -1 main                         # e4e7627 Merge s1/web-frontend-p1-3 into main ...
git config --local user.email                     # eya.nasfi@esprit.tn
```

## 2026-11-12 23:10 — Step 0: facts for monthly report 2 + PL decision #2

Branch `s2/S2-00-facts-readme`.

- `docs/reports/month-2-facts.md`: facts-only digest with a source per fact. New fact measured for it: the reference script takes **2.0–2.3 s** per run (3 runs, seed 42, Docker, over HTTP); EventSim reset to seed 42 afterwards.
- **PL decision #2** recorded in `docs/decisions.md`, with the canary table.
- **Gap check, EventSim vs PL decision #2:** no gap. New `tests/test_pl_decision_2.py`: one test per rule (8 tests, all pass). So no `s2/S2-00-role-matrix` branch.

**How to verify.**
```powershell
.\.venv\Scripts\python -m pytest tests/test_pl_decision_2.py -v     # 8 passed
```

**Unsure.** "Usage limits" in the problem list: only the Gemini 503s are recorded in the repo; any other limit is marked "to confirm by Aya".

**Next:** README rewrite (PL decision #5 §4), then S2-01.

## 2026-11-12 23:25 — S2-01 Review and merge the gateway (FR-GW-01, FR-AGT-07)

Branch `s2/S2-01-gateway-merge` = `origin/s1/S1-02-gateway-mcp` rebased onto local `main`.

- **Rebase:** conflicts only in `README.md` (kept the new README, added a `gateway/` row) and `docs/decisions.md` (kept ADR-003 and PL decision #2 both). Code applied cleanly.
- **Dependencies:** `mcp==2.3.0`, `httpx2==2.16.0` installed in `.venv`.
- **Tests:** 182 passed after the rebase (the 77 gateway tests among them); 204 after the additions below.
- **27 C0 tools vs PL decision #2:** the gateway forwards with the caller's own EventSim token, so EventSim's matrix applies. New `test_pl_decision_2_through_the_gateway` (14 rows: archive scope, patch scope, links in active editions, attendee routes, speaker/partner creation).
- **`raw_api_call` vs `/_test/*`:** new test calls all 6 test routes × GET/POST × 3 roles: all refused, state unchanged. The 9 tricky spellings test (encoding, case, dot segments) was already there.
- **Allow-list alignment:** C0 allow-list and registry were already identical (27 = 27). New `test_c0_allow_list_equals_the_gateway_registry` fails if they ever differ in either direction; `test_every_configuration_names_only_registry_tools` covers C1–C4.
- **`.env`:** three random `GATEWAY_TOKEN_*` values added on this PC (never printed).
- **Docker probe:** eventsim and gateway healthy; gateway `8100/tcp` only; no bearer → 401; EventSim token as bearer → 401; 27 tools with both protocol versions; reader `create_event` → HTTP 403; `/_test/reset` and `/%5Ftest/snapshot` → refused. EventSim reset to seed 42 afterwards.
- **Coverage:** eventsim + gateway 97%.

**How to verify:** manual guide L14.

**Unsure.** The Avast `/mcp` loopback problem (ADR-003) was on Aya's PC; this PC was not tested for it because the gateway has no host port.

**Next:** S2-02 (n8n in compose + identity spike).
