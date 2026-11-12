---
id: PROC-07
title: Re-link partners to copied events
roles: [editor, admin]
tags: [duplicate, partner, link]
version: 1
---

# PROC-07 — Re-link partners to copied events

## Purpose
Keep the same partners (sponsors and supporting organisations) on copied events. A partner is a global record; its tier and contract details stay on that one record.

## Who can do this
An **editor** when the event belongs to a **draft** edition; an **admin** anywhere.

## Steps
1. Read the source event with `get_event` and note its `partner_ids`.
2. Do **not** create partners: reuse the same ids.
3. After creating the new event, call `link_partner_to_event` once per partner id with the **new** event id.
4. If a partner is archived, ask the requester before linking it.
5. Partner notes may hold contract details. Never copy them into descriptions, messages or notifications.
6. Report the partners linked to each new event.

## Checks before and after
- **Before:** you know the partner ids of each source event.
- **After:** each new event has the same partner ids as its source. The number of partner records is unchanged.

## Common mistakes
- Creating a new partner with the same name.
- Sending partner contract references to anyone outside the team.
- Linking partners to an event in an `active` edition as an editor: refused (HTTP 403).
- Worrying about events with no partners: they simply get no partner links, which is correct.
