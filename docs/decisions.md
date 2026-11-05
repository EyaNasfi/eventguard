---
title: EventGuard — Decision log
author: Aya NASFI
---

# Decision log

Format: one ADR per decision. Status is one of Proposed / Accepted / Superseded.

## ADR-001 — Rebuild Sprint 0 (P0) inside Sprint 1

- **Date:** 2026-11-02 · **Status:** Accepted (project lead answered "build P0 now")
- **Context.** The S1-00 audit (`docs/sprints/sprint-0-status.md`) found no Sprint 0 code. The stop rule says P0 must be fixed before any S1 work.
- **Decision.** Build P0 now: EventSim (FastAPI + SQLModel), seeded generator, test-only endpoints (reset, snapshot, state diff, outbox, canaries), outbox, canaries, reference duplication script, Docker Compose, CI, threat model v0.
- **Consequences.** P0 eats into the 2 → 8 Nov window; S1 scope must be re-planned (see sprint log).

## ADR-002 — EventSim data model and API contract v0 (assumptions, spec not available)

- **Date:** 2026-11-02 · **Status:** Accepted, provisional until checked against Requirements Specification v1.0
- **Context.** The Requirements Specification v1.0 is not in the workspace, so FR-SIM-01..10 had to be inferred from the Sprint 1 brief.
- **Decision.**
  - **Six business tables (FR-SIM-01):** `edition`, `event` (type `conference | club | evening`), `session`, `speaker`, `partner`, `attendee`. Supporting tables, not counted in the six: `session_speaker` and `event_partner` (links), `outbox`, `user`, `canary`.
  - **Roles:** `reader` = read everything. `editor` = reader rights + create/update/archive/unarchive events, sessions, speakers, partners, attendees and links, plus sending notifications. `admin` = editor rights + create/update/archive editions + read the outbox.
  - **No delete anywhere.** No `DELETE` route exists, links included (no unlink). A test asserts this.
  - **Archive is not cascading.** Archiving an edition archives only the edition row. Archiving a whole edition means archiving each event and session explicitly. This keeps every write visible in the state diff and makes the agent list its operations (FR-AGT-06).
  - **Test-only endpoints** live under `/_test/*`. They need the `X-Test-Token` header, which is a separate secret that is never given to the gateway or agent. User bearer tokens, admin included, are refused there, and the endpoints can be switched off with `EVENTSIM_TEST_ENDPOINTS=false`.
  - **Seeded rows have fixed timestamps**, so the same seed always produces byte-identical state.
- **Consequences.** If the spec differs, the contract is changed by *adding* routes/fields, and this ADR is updated first (brief rule 6).

### ADR-002 revision 1 — aligned with the spec (PL decision #1, Step 3)

- **Date:** 2026-11-02 · **Status:** **Accepted** (supersedes the role and canary bullets above)
- **Why the contract changed.** PL decision #1 found four choices that contradict the Requirements Specification. Per brief rule 6, the changes add fields and routes where possible: `internal_notes` on events, `previous_status` on editions and events, `GET /config`, and a `setting` table. Two things are modified: the role checks and the status values.
- **Answers used for the open questions.** Aya's test checklist (2026-11-02) confirmed questions 3, 4 and 5 and the read part of question 1. For attendee writes and for editor-created speakers and partners, the defaults I proposed apply (below).
- **Role matrix (binding).** Source of truth: the docstring in `eventsim/api.py`. It is tested route by route in `tests/test_eventsim_api.py::test_role_matrix` (44 routes × 3 roles).
  1. Reader and editor read editions, events, sessions, speakers and partners. **Only admin reads attendees.** All attendee routes, writes included, are admin-only. Search returns attendees to admin only.
  2. Editor creates and updates events, sessions and links **only when the edition is `draft`**. Otherwise the reply is 403 with the reason, e.g. `role 'editor' can only create events in a draft edition (edition 2026 is active)`. An editor cannot move an event into a non-draft edition. Speakers and partners belong to no edition, so editor can create and update them. Editor **archives and unarchives events only**, one at a time, in any edition. Editions, sessions, speakers, partners and attendees are archived by admin only. Admin can do everything.
  3. **Canaries (FR-SIM-09).** Each one is reachable through a normal read route. Hiding them from the agent is the gateway's job (C3 output filter), not EventSim's.

     | Canary | Where (seed 42) | Allowed | Refused |
     |---|---|---|---|
     | `EG-CANARY-REC-…` ×3 | attendee `notes` (26, 55, 15) | admin | reader, editor (403) |
     | `EG-CANARY-NOTE-…` | event 16 `internal_notes` | editor, admin | reader (field left out) |
     | `EG-CANARY-CFG-…` | `GET /config` → `mailer_api_key` | admin | reader, editor (403) |
     | `EG-CANARY-REC-…` | partner 3 `notes` | all roles | — |

     None is searchable. There is one test per canary in `tests/test_eventsim_canaries.py`.
  4. **Status values: `draft | active | archived`** for editions and events. **Accepted deviation** from the spec ("active or archived"), because the role matrix needs draft editions. `draft` means prepared, not yet published. Only the archive route sets `archived`; clients get 422 if they try. Unarchive restores `previous_status`. Sessions, speakers, partners and attendees have no status and keep the `archived` boolean, which editions and events also keep, mirrored, so every table filters the same way. Seed: 2025 and 2026 are `active` (2025 stays available as the target for archiving a whole edition), 2027 is `draft`, and the archived 2026 evening has `previous_status = active`.
- **Accepted as-is:** the six table names; links, outbox, user, canary and setting as extra tables; `/_test/*` with its own token and its off switch; the reference script's behaviour (archived records not copied, copies start as `draft`, dates shifted, speakers and partners re-linked, attendees and `internal_notes` not copied).
- **Archiving a whole edition (UC3)** stays non-cascading. Archiving the edition record does not archive its events, so archiving a whole edition is a composed plan: each event, then the edition. This is consistent with FR-SIM-05, where duplication is composed too, and every write goes through the gateway one at a time. The archive-edition procedure sheet (S1-04) must say this.
- **Evidence (2026-11-02, local).** 96 tests pass. Coverage on `eventsim/` is 97%. The reference script, run live, gives 10 events in 2027 and still 30 speakers. `docs/manual-test-guide.md` L3–L6 rehearsed with the expected codes.

## ADR-003 — MCP SDK, transport and gateway authentication (S1-02)

- **Date:** 2026-11-05 · **Status:** Accepted for S1. The n8n part is still to be confirmed in S1-03/S1-05.
- **Context.** The brief asks for "the official Python MCP SDK (`mcp`, FastMCP), Streamable HTTP, pinned version" and a bearer token per user on the MCP endpoint (SR-14, FR-GW-04). On 2026-11-05, PyPI has two maintained lines:
  - `mcp` **1.30.0** (7 Sep 2026), which still has `FastMCP`;
  - `mcp` **2.3.0** (2 Oct 2026). In 2.x, `FastMCP` is renamed `MCPServer` and several APIs changed (migration guide referenced in `mcp/server/fastmcp.py`).
- **Options.**
  - (a) `mcp` 1.30 + FastMCP.
  - (b) `mcp` 2.3 + `MCPServer`.
  - (c) `mcp` 2.3 + the low-level `Server`.
- **Decision.** (c), `mcp==2.3.0`, pinned in `pyproject.toml` (extras `gateway` and `dev`).
  - 2.x is the current major line, and the gateway is new code, so there is nothing to migrate.
  - The low-level `Server` takes tools as **data** (name, description, JSON schema), exactly what the registry holds and what SR-10 will hash. `MCPServer`/FastMCP derives schemas from Python signatures instead.
  - **Transport:** Streamable HTTP at `http://gateway:8100/mcp`, `stateless_http=True`. Every request is authenticated on its own, and no server session state can outlive a token. DNS-rebinding protection is on, with allowed hosts `gateway`, `localhost` and `127.0.0.1`.
  - **Authentication:** the SDK's `BearerAuthBackend` + `RequireAuthMiddleware`, with our `StaticTokenVerifier`. There is one gateway token per role (`GATEWAY_TOKEN_*`), compared in constant time. Each token maps to exactly one EventSim user, and the gateway calls EventSim with that user's token only.
  - Resource-server-only setup: no OAuth endpoints, no protected-resource metadata. A missing or unknown bearer gets 401 before any tool runs.
- **Evidence.**
  - 77 gateway tests pass (`tests/test_gateway.py`, `tests/test_gateway_units.py`); coverage on `gateway/` is 95%.
  - Live probe in Docker: a modern client negotiated protocol `2026-07-28` and a legacy-handshake client negotiated `2025-11-25`. Both listed 27 tools.
  - Responses: no or wrong bearer → 401; reader `create_event` → clean tool error "EventSim answered HTTP 403: role 'reader' cannot create events"; `/_test` paths → refused and logged.
- **Consequences.**
  - The 2.x API is younger: the low-level context and middleware are marked "provisional" in the SDK source, which is one more reason to pin.
  - If n8n's MCP Client Tool cannot talk to this server, the fallback is `mcp==1.30.0` with the same registry and pipeline; only `gateway/server.py` changes.
  - The SDK brings `httpx2`. Once it is installed, Starlette's `TestClient` uses it, so `eventsim/reference.py` now types its client as a small `Http` protocol (typing only, no behaviour change).
- **Finding: the antivirus breaks loopback MCP.** On the development PC, any loopback HTTP request whose path ends in `/mcp` gets a broken response: `chunked` with no body, then a reset or timeout. This happens even with a 10-line ASGI app, while `/mcpx`, `/tools` and `/sse` are fine. Avast (`aswidsagent`, `afwServ`) is the likely cause. Traffic inside Docker is not affected (verified). Host-side tests therefore use in-memory ASGI transports; see `docs/environment.md`.