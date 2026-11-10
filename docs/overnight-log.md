# Overnight log — PL decision #3 (unattended run, 2026-11-10)

Each entry: time · what was done · files changed · how it was checked · next.
Resume point: the last entry's "Next" line.

## 05:07 — Start
- Read the overnight brief (PL decision #3). Repo on `main` (3e53595); web/ and design tooling untracked.
- Found: no `.claude/settings.json` (only `settings.local.json`, untouched), no `CLAUDE.md`.
- Next: Step 1, docs/START-HERE.md.

## 05:25 — Step 1: docs/START-HERE.md
- Wrote `docs/START-HERE.md` (11 sections + answers). Facts checked in repo: main log, sprint logs, ADRs, gateway branch `origin/s1/S1-02-gateway-mcp` (unmerged, 77 tests per its log), settings, manual guide.
- Not found in repo, marked as such: Requirements Spec v1.0, PL decision #2, S1-03…S1-10 task names.
- Docker Desktop is not running (`docker info` → pipe not found).
- Next: Step 2 housekeeping.

## 05:40 — Step 2: housekeeping
- `eventguard/.claude/settings.json` created with `env.CLAUDE_CODE_SUBAGENT_MODEL = "sonnet"` (no settings.json existed; `settings.local.json` with the Impeccable hooks left untouched).
- Headless Edge: 28 processes with `--headless` in the command line → stopped; 0 left (their 82 child processes exited with them; no non-headless msedge remained).
- Capture driver `cdp.mjs` (scratchpad, not in repo): now kills its browser in `finally`, on exit/SIGINT/SIGTERM/uncaught error, by PID tree **and** by its unique profile-dir tag (Edge's launcher hands off to a second process, so a PID kill alone left 2 behind — found and fixed). Smoke run → **0 headless left**.
- Standing no-push rule: `CLAUDE.md` (new) and ADR-004 in `docs/decisions.md`.
- Next: Step 3, Phase 3 review fixes.

## 06:20 — Step 3: Phase 3 review fixes
Sources: Assessment A (design review + normalize pass, 25/40) and Assessment B (detector + in-page checks) from 2026-11-09/10.

| Finding | File | Fix | Verified how |
|---|---|---|---|
| P1 Events archive is an untraced second write path; collides with pending AP-0041; raw 409 | `web/src/pages/Events.tsx` | Archive labelled "Direct EventSim edit: not through the gateway, not in the audit log" (pane + dialog); pending approvals for the same event listed with a Review link; 409/403/unreachable mapped to plain messages | Screenshot `p3fix-events.png` (AP-0041 shown above the button); tsc |
| P1 Tamper evidence below the fold | `pages/Audit.tsx`, new `components/ui/DetailPane.tsx` | BreakDetail now leads the pane; pane capped to viewport with its own scroll | Screenshot `p3fix-audit-broken.png` |
| P1 (B) Focus drops to `<body>` after Verify chain / Approve (button disabled while loading) | `components/ui/Button.tsx` | Loading buttons use `aria-disabled` + ignored clicks, stay focusable | Code review; build |
| P2 Focus lost after a decision on Approvals | `pages/Approvals.tsx` | Focus moves to the next row needing approval | Code review |
| N1 Lamp tones differ (cue sheet vs audit) | `components/ui/status.ts`, `CueSheet.tsx`, `Audit.tsx` | Shared `NUMERAL_TONE` / `auditNumeralState`; chain state carried by link glyph, not numeral | Screenshot |
| N2 `Q5` vs bare seq, time position | `CueSheet.tsx`, `Audit.tsx` | Bare numerals + time under numeral (sans, tabular) on both | Screenshot |
| N3 Record status green "Active" | `status.ts` (`RECORD`), `Events.tsx` | Active/Archived neutral, Draft info; green reserved for Allowed/Executed | Screenshot |
| N4 Pending/blocked named 4 ways | `status.ts`, `Assistant.tsx`, `Approvals.tsx`, `CueSheet.tsx` | "Needs approval" / "Blocked" everywhere; "Waiting for approval" only on the preview card | grep + screenshot |
| N5 Boxed 11px chips in rows | `Events.tsx`, `Approvals.tsx` | Plain chips in rows, boxed only in detail headers | Screenshot |
| N6 Three hand-rolled detail asides | `DetailPane.tsx` + Audit/Events/Approvals | One `DetailPane` + `LIST_DETAIL_GRID` (24–32rem) | tsc + screenshots |
| N7 Events filters local, no Clear, "11 shown" | `Events.tsx` | URL params (`year`, `kind`, `status`), `role="search"`, Clear filters, "N of M events", "All statuses" | Screenshot |
| N8 Empty states without actions | `Events.tsx`, `Audit.tsx` | 2027 empty → "Ask the assistant to duplicate 2026" link; filtered audit → Clear filters | Screenshot `p3fix-events-2027.png` |
| N9 ISO dates / mono dates / seconds | `Events.tsx`, `Approvals.tsx`, `Audit.tsx` | `fmtDate`/`fmtDayTime` in sans, no seconds | Screenshot |
| N10 Button-like links off the 7/9 scale | `Button.tsx` (`buttonClass`), CueSheet, ChatMessage, DemoGuide, role select, ConfigBadge | One scale (h-7 / h-9) | Screenshot |
| N11 "Simulate tampering" red | `Audit.tsx` | Secondary variant | Screenshot |
| N12 Mixed selection semantics, invalid `aria-selected` on rows | `Table.tsx`, `Audit.tsx`, `Events.tsx` | `aria-current` everywhere; `aria-selected` removed | grep |
| N13 Reader copy warn vs muted | `PreviewCard.tsx`, `Events.tsx` | Muted + Lock icon in both | Code |
| N14 Ad-hoc toast specs | `status.ts` (`RECORD_ACTION`), `Events.tsx` | Shared specs; errors use `RUN.error` | Code |
| N15 "Config" label, neutral tab count, no sample note on Assistant | `Approvals.tsx`, `Tabs.tsx`, `Assistant.tsx` | "Configuration"; amber count on "Needs approval" tab; sample-data note | Screenshot |
| Jury: same attack, two rule names | `api/mock/audit.ts` | Seeded #10 now `output_filter.external_recipient`, like the live C3 run | grep |
| B: Demo guide `aria-controls` to unmounted panel | `DemoGuide.tsx` | Only set when open | Code |
| B: line-length in untrusted quote | `UntrustedText.tsx` | 62ch | — |

Left for later (with reason):
- P2 Approvals queue as "held cues" (margin grammar) — visual polish, paused to Sprint 8 by PL decision #3.
- P3 Toasts can cover a detail footer; ShieldCheck used for 4 meanings; rule ids shown raw to staff — polish (Sprint 8).
- P3 11px uppercase field labels and stamps remain (deliberate label style; the detector's tiny-text rule no longer fires).

Checks: `tsc -b --noEmit` clean, `eslint .` 0 problems, `vite build` OK. Capture batch → 0 headless Edge left.
- Next: Step 4 (live mode). Docker is not running.

## 06:55 — Step 4: live mode (Docker down → partial, as the brief allows)
- **Docker Desktop not running** (`docker info`: engine pipe not found). Per the brief, EventSim was **not** started with the dev compose file and the browser-against-Docker checks were **skipped**. Not started: Docker itself (needs Aya / GUI).
- Done anyway because it needs no Docker (safest useful option, recorded here):
  - Dev proxy `/eventsim` → `VITE_EVENTSIM_URL` already in `web/vite.config.ts` (no backend change for CORS). Tokens are attached server-side by the proxy per `X-Demo-Role`; client code never reads them; `envPrefix` exposes only `VITE_USE_MOCKS`.
  - `web/.env.example`: fictional per-role placeholders + note; `web/.env.local` created (gitignored) with placeholders, `VITE_USE_MOCKS=true`. `web/README.md` written, including the "`VITE_*` can end up in the browser, local dev only" warning.
  - Demo controls hidden in live mode (DemoGuide returns null). Live build grep (`VITE_USE_MOCKS=false`, admin token set to a sentinel): `_test` 0, `TEST_TOKEN` 0, `X-Test-Token` 0, sentinel 0, `VITE_EVENTSIM_TOKEN` 0, "Demo guide" 0. To get `_test` to 0, mock attack payloads and one seeded audit entry now say "harness reset route" instead of the literal path (wording only).
  - **API contract checked in-process** against the real EventSim app (FastAPI TestClient, throwaway SQLite, fictional tokens, no server, no backend change; script in the session scratchpad `contract_check.py`):

| Check | Result |
|---|---|
| Events: editions 2025, 2026, 2027 | PASS |
| Events: 2026 has 11 events; sessions, speakers, partners readable | PASS |
| Attendees: admin 200, editor 403, reader 403 | PASS |
| Editor archives a 2026 event (status → archived) | PASS |
| Unarchive restores previous status (active → active) | PASS |
| Archive twice → 409 with reason | PASS |
| Refusal: reader cannot archive (403 "role 'reader' cannot archive events") | PASS |
| Refusal: editor cannot archive an edition (403 "role 'editor' cannot archive editions") | PASS |
| Unknown token → 401 | PASS |
| EventSim down: UI shows a clear error state (live dev server on :5174, nothing on :8000) | PASS after fix: the proxy's 502 first read "EventSim refused (502)"; live client now maps proxy 502/503/504 to "EventSim is not reachable…" (`web/src/api/live.ts`) |
| Same checks in the browser against Docker EventSim | **NOT RUN** (Docker down) |

  - Contract mismatch fixed (front-end types only): `GET /me` returns `{id, role, username}`; `Me.display_name` is now optional (`web/src/api/types.ts`).
  - "Sample data · not measured" label on Assistant, Approvals, Audit log and Events (mock mode); Gateway, Attack lab, Results marked "coming later" in the sidebar and replaced by paused pages (no sample numbers shown).
- Live dev server on :5174 stopped; 0 headless Edge left.
- Next: Step 5 (branch, gitignore, gitleaks, CI job, commit; no push).
