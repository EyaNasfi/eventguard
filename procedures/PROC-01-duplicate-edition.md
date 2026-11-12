---
id: PROC-01
title: Duplicate an edition to the next year (N+1)
roles: [editor, admin]
tags: [duplicate, edition, rollover]
version: 1
---

# PROC-01 — Duplicate an edition to the next year (N+1)

## Purpose
Prepare next year's edition by copying this year's programme. The copy is a draft that the team edits before it is published. Nothing in the source edition changes.

## Who can do this
An **admin** creates the target edition if it does not exist yet. An **editor** can then copy events, sessions and links into it, because the target edition is a **draft**. A reader cannot duplicate anything.

## Steps
1. Read the source edition with `list_editions` (filter `year`) and note its id.
2. Check that the target edition (year N+1) exists and is `draft`. If not, ask an admin to create it with `create_edition`.
3. List the source events with `list_events` (`edition_id`, `archived=false`). Archived events are **not** copied.
4. Write the full plan before any write: one line per event and per session to create, with the new dates.
5. For each event, follow PROC-02, PROC-03 or PROC-04 depending on its type (conference, club, evening).
6. Move every date by one year on the same calendar day (PROC-05).
7. Re-link speakers (PROC-06) and partners (PROC-07). Never create new speaker or partner records.
8. Never copy attendees.

## Checks before and after
- **Before:** the target edition is `draft`; you know how many live events the source has.
- **After:** the target has the same number of events as the source has live events, all `draft`. The speaker and partner counts did not change.

## Common mistakes
- Copying the archived event too.
- Creating copies as `active`: copies always start as `draft`.
- Creating new speakers instead of linking the existing ones.
- Copying attendees or internal notes.
