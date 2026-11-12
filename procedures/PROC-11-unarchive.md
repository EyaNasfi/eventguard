---
id: PROC-11
title: Unarchive a record
roles: [editor, admin]
tags: [archive, unarchive, restore]
version: 1
---

# PROC-11 — Unarchive a record

## Purpose
Bring back a record that was archived by mistake or that is needed again.

## Who can do this
An **editor** can unarchive single **events** in any edition. Every other record type (edition, session, speaker, partner, attendee) needs an **admin**.

## Steps
1. Find the archived record, for example with `list_events` (`archived=true`).
2. Confirm with the requester that this is the right record.
3. Call `unarchive_record` with the entity and the id.
4. Editions and events go back to their **exact previous status** (`draft` or `active`). Other records simply lose the archived flag.
5. Unarchiving is not cascading either: unarchive related records one by one if needed.
6. Tell the team when the record is visible again (PROC-15).

## Checks before and after
- **Before:** the record is archived and the requester confirmed it.
- **After:** `get_event` (or the matching read tool) shows the previous status again.

## Common mistakes
- Expecting an archived draft to come back as active: it comes back as draft.
- Unarchiving a cancelled event that should stay cancelled.
- Asking an editor to unarchive an edition: refused.
- Unarchiving an edition but forgetting its events: each one is unarchived separately.
- Unarchiving a record without telling the team, so nobody knows it is visible again.
