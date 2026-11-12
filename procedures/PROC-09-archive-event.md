---
id: PROC-09
title: Archive a single event
roles: [editor, admin]
tags: [archive, event]
version: 1
---

# PROC-09 — Archive a single event

## Purpose
Hide an event that is cancelled or finished, without losing it. **Nothing is ever deleted**: archiving can be undone (PROC-11).

## Who can do this
An **editor** can archive a single event in **any** edition. An **admin** can too. A reader cannot. Editors never archive editions, sessions or attendees.

## Steps
1. Identify the exact event with `list_events` or `search_records`. Confirm the name, date and edition with the requester when more than one event matches.
2. Run the pre-archiving checklist (PROC-12).
3. Call `archive_record` with `entity=events` and the event id.
4. The event's status becomes `archived`; its previous status is kept for a later unarchive.
5. Archiving is **not cascading**: the event's sessions stay as they are. Do not archive them unless the requester asks and you are an admin.
6. Tell the team if needed (PROC-15).

## Checks before and after
- **Before:** exactly one event matches the request.
- **After:** `get_event` shows `status = archived`; no other record changed.

## Common mistakes
- Archiving all events with a similar name.
- Archiving by guessing the id instead of reading it.
- Looking for a delete action: there is none, by design.
- Archiving an event in the wrong edition because two years share the same event name.
