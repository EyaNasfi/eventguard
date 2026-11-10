---
title: EventGuard web UI — status
date: 2026-11-10
branch: s1/web-frontend-p1-3 (local, not pushed)
---

# Web UI status

Front-end Phases 1–3 are built. Phases 4–7 are paused by PL decision #3:

- the Gateway page resumes in Sprint 5;
- the Attack lab and Results resume after the first real attack results;
- motion, polish and the demo page resume in Sprint 8.

How to run it: `web/README.md`. Screenshots were taken at 1440×900 in mock mode on 2026-11-10.

## Pages built

| Page | What it does | Data | Screenshot |
|---|---|---|---|
| **Assistant** | Chat on the left. On the right, the agent's run as a numbered list of steps: each tool call, the gateway checkpoints it passed, and the decision (allowed / needs approval / blocked, with the rule). Writes show a preview: what will be created or linked, what is not touched, an expiry, Approve and sign or Reject. Untrusted record text sits in a labelled frame. A **Demo guide** replays the jury script. | Sample data (scripted agent) | `screenshots/assistant-c3-attack-blocked.png`, `screenshots/assistant-approved.png` |
| **Approvals** | Queue of writes that need approval: change summary, requester role, configuration, expiry countdown. The selected item shows the full preview with Approve and Reject; the Decided tab keeps history. | Sample data | `screenshots/approvals.png` |
| **Audit log** | Hash-chained entries: time, role, tool, arguments, decision, rule, previous hash → hash. Filters live in the URL (`?q=TC-0016` jumps to a call). **Verify chain** recomputes every hash. **Simulate tampering** edits a copy of entry #10 and shows exactly where the chain breaks and which fields were changed. | Sample data | `screenshots/audit-verified.png`, `screenshots/audit-tampered.png` |
| **Events** | EventSim browser: editions by year (2025, 2026, 2027), filter by kind and status, sessions with speakers, partners, internal notes (hidden for reader), registrations (admin only). Archive and unarchive are the only writes, reversible and labelled as direct EventSim edits. | **Live** with `VITE_USE_MOCKS=false`; otherwise a fictional seed-42 copy | `screenshots/events.png` |
| Gateway, Attack lab, Results | Paused: each says what it will do, when it resumes, and what it waits for. No sample numbers are shown. | — | `screenshots/gateway-coming-later.png` |
| Component gallery `/dev/components` | Every base component and state on the product tokens. | — | `screenshots/component-gallery.png` |

Checks on the final tree: `npm run typecheck`, `npm run lint` and `npm run build` are clean. The live-mode bundle has no `_test`, no test-token name and no token value. Every text/background pair has a contrast of at least 4.5:1 (computed); control borders are at least 3:1.

## Live-mode check table (2026-11-10)

**Docker Desktop was not running**, so EventSim could not be started with the dev compose file, and the browser checks against a dockerised EventSim were **not run**.

The API side was checked **in-process** instead, against the real EventSim app: FastAPI TestClient, a throwaway SQLite database and fictional tokens. No server was started and no backend code changed.

| Check | Result | How |
|---|---|---|
| Events: editions 2025, 2026, 2027; events, sessions, partners, speakers | PASS | in-process API |
| Attendees visible to admin only (admin 200, editor 403, reader 403) | PASS | in-process API |
| Editor archives a 2026 event → status `archived`; unarchive restores the old status | PASS | in-process API |
| Archive twice → 409 with a reason (shown as "Nothing to do: already in that state") | PASS | in-process API + UI mapping |
| Reader cannot archive (403 "role 'reader' cannot archive events") | PASS | in-process API |
| Editor cannot archive an edition (403 "role 'editor' cannot archive editions") | PASS | in-process API |
| EventSim down → clear error state ("EventSim is not reachable…") | PASS | live dev server with nothing on :8000 |
| Demo controls hidden in live mode; sample-data labels shown | PASS | live dev server |
| All of the above in the browser against Docker EventSim | **NOT RUN** | Docker down |

Contract mismatch found and fixed (front-end types only): `GET /me` returns `{id, role, username}`, so `Me.display_name` is now optional.

## Endpoints the paused and sample-data pages will need

These are proposals. The contract is in `web/src/api/types.ts` (types `Conversation`, `ToolCall`, `Approval`, `AuditEntry`, `ChainCheck`, `GatewayConfig`, `Attack`, `AttackRun`, `ResultsSet`). All of them are gateway-side, called with the user's gateway bearer token, never EventSim's.

| Page | Method | Path | Response shape |
|---|---|---|---|
| Assistant | POST | `/conversations` | `Conversation` `{id, title, role, config, startedAt, messages: [], toolCalls: []}` |
| Assistant | GET | `/conversations/{id}` | `Conversation` with `messages: Message[]`, `toolCalls: ToolCall[]` |
| Assistant | POST | `/conversations/{id}/messages` `{text}` | `202`; the agent turn streams on the events channel below |
| Assistant | GET | `/conversations/{id}/events` (SSE) | stream of `AgentEvent`: `message`, `tool_call`, `tool_update`, `approval`, `done` |
| Approvals | GET | `/approvals?status=pending\|approved\|rejected\|expired` | `Approval[]` `{id, conversationId, toolCallIds, requestedBy, requestedAt, expiresAt, config, status, summary, preview: {title, note?, groups[], excluded[]}, previewHash, decidedAt?, decidedBy?, signature?}` |
| Approvals | GET | `/approvals/{id}` | `Approval` |
| Approvals | POST | `/approvals/{id}/approve` | `Approval` (status `approved`, `signature`); `409` if not pending (single use / expired) |
| Approvals | POST | `/approvals/{id}/reject` `{reason?}` | `Approval` (status `rejected`) |
| Approvals | GET | `/approvals/events` (SSE) | a ping whenever any approval is created or changes state |
| Audit log | GET | `/audit?q=&decision=&role=&config=` | `AuditEntry[]` newest first `{seq, at, actorRole, config, conversationId, toolCallId, tool, args, decision, rule?, reason?, hash, prevHash}` |
| Audit log | POST | `/audit/verify` | `ChainCheck`: `{status:'intact', checked, head}` or `{status:'broken', checked, brokenAt, expectedHash, storedHash}` |
| Gateway | GET | `/gateway/configs` | `GatewayConfig[]` `{id, description, layers: Record<LayerId, boolean>, tools: string[], hash}` |
| Gateway | GET | `/gateway/config` | the active `GatewayConfig` |
| Gateway | PUT | `/gateway/config` `{id, layers?}` | the new active `GatewayConfig` (admin only) |
| Attack lab | GET | `/bench/families` | `AttackFamily[]` `{id, name, goal, threat}` |
| Attack lab | GET | `/bench/attacks` | `Attack[]` `{id, family, title, vector, payload, oracle}` |
| Attack lab | GET | `/bench/runs?config=` | `AttackRun[]` `{id, attackId, config, status, outcome?, oracle?: {kind, detail, blockedBy?}, auditSeqs, startedAt, durationMs?}` |
| Attack lab | POST | `/bench/runs` `{attackIds, config}` | `AttackRun[]` queued; updates on `/bench/runs/events` (SSE) |
| Results | GET | `/results/latest` | `ResultsSet` `{id, generatedAt, synthetic, method, confidence, repetitions, configs: [{config, metrics: Record<MetricId, {value, low, high}>, byFamily, nAttacks, nTasks}]}` |

Not needed from the backend: the tamper simulation. It belongs to the demo; a real verifier only reports the actual state of the chain.

## Known gaps (not done tonight)

- Browser checks against Docker EventSim (Docker down).
- P2/P3 polish from the Phase 3 review: the Approvals queue in the step-margin style; toasts that can cover a detail footer; one icon (ShieldCheck) used for several meanings; raw rule ids shown to staff.
- The Assistant, Approvals and Audit log run on the scripted demo until the gateway exposes the endpoints above.
- Chart palette chosen and validated for Results (violet `#9085e9` attack success, teal `#1f9e9a` task success: dark-mode CVD ΔE 11.6). The page itself is paused.
