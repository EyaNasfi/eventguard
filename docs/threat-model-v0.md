---
title: EventGuard — Threat model v0
author: Aya NASFI
date: 2026-11-02
status: v0 (written during S1 because no Sprint 0 version existed; review in S2)
---

# Threat model v0

## 1. System and trust boundaries

```
 human ──chat──▶ n8n (AI Agent + Gemini) ──MCP / bearer──▶ gateway ──HTTP / user token──▶ EventSim
                     ▲                                       │                              │
                     └──────── tool results (untrusted) ─────┘                         /_test/* (harness only)
```

| Boundary | What crosses it | Trust |
|---|---|---|
| B1 human → n8n | chat text | The user is authenticated by role; their text is trusted *as a request*, not as policy. |
| B2 n8n → Gemini | prompt, history, tool results | Gemini is an external service; it sees only synthetic data. |
| B3 agent → gateway (MCP) | tool calls | **Untrusted.** The model can be steered by injected content. |
| B4 gateway → EventSim | HTTP with the mapped user's token | Gateway is trusted; it holds every EventSim token (SR-01). |
| B5 EventSim → agent | record content, procedure sheets | **Untrusted content**: any text field may carry an injection. |
| B6 harness → `/_test/*` | reset, snapshot, diff, canaries | Harness only, separate secret; never reachable from B3 (FR-SIM-06). |

## 2. Assets

- A1 EventSim data integrity (editions, events, sessions, links): no unwanted writes, no "deletes" by mass archive.
- A2 Confidential fields: attendee contact data and private notes, partner notes. Canaries live here (FR-SIM-09).
- A3 Credentials: EventSim user tokens, MCP bearer tokens, the harness test token, the Gemini API key.
- A4 System prompt (canary `EG-CANARY-SP-*`, SR-12).
- A5 Evaluation integrity: the frozen tasks, seeds, checkers and state diffs.

## 3. Threats (STRIDE-style, focused on the agent)

| ID | Threat | Entry | Asset | Planned layer |
|---|---|---|---|---|
| T1 | Indirect prompt injection in a record field (event description, speaker bio) makes the agent write or send data | B5 | A1, A2 | spotlighting, injection detector (C3/C4) |
| T2 | Injection hidden in a procedure sheet | B5 | A1 | spotlighting (C3), pinned sources |
| T3 | Exfiltration through `send_notification` to an outside address | B3 | A2 | output filter, preview/approval, quotas (C2–C3) |
| T4 | Privilege misuse: the agent uses broad tools (`update_record`, `raw_api_call`) beyond the task | B3 | A1 | least privilege (C2), no broad tools after C0 |
| T5 | Mass archive presented as "cleanup" | B3 | A1 | preview + approval, quotas (C2) |
| T6 | Agent reaches test endpoints to reset or read canaries | B3 → B6 | A5, A2 | hard deny in gateway (all configs) + separate test token in EventSim (implemented in P0) |
| T7 | Token leakage into prompts, logs or workflow exports | all | A3 | gateway holds tokens; gitleaks in CI; stripped exports (SR-13) |
| T8 | System prompt disclosure | B1 | A4 | security prompt (C1), output filter with canary match |
| T9 | Tool description tampering (rug-pull) | B3 | A1 | pinned tool descriptions with hashes (SR-10) |
| T10 | Confused deputy: a reader's chat performs editor writes | B1 → B4 | A1 | per-role bearer → per-user EventSim token (FR-GW-04) |

## 4. Controls already in place (P0)

- EventSim enforces roles on every route (reader / editor / admin). The gateway cannot raise privileges because EventSim checks again.
- There is no `DELETE` route anywhere, and a test asserts this.
- `/_test/*` requires `X-Test-Token`. User tokens, admin included, are refused. The routes are hidden from OpenAPI and can be switched off.
- The data is synthetic: invented names, `example.*` domains, `+99` phone numbers.
- Canaries are planted in private fields and are not searchable through `/search`.

## 5. Out of scope for v0

Attacks on Docker or the host, on Google's infrastructure, or on n8n itself (CVE-level). Denial of service.
