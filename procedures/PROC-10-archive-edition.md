---
id: PROC-10
title: Archive a whole edition (composed plan)
roles: [admin]
tags: [archive, edition, plan]
version: 1
---

# PROC-10 — Archive a whole edition (composed plan)

## Purpose
Close a past edition completely. Archiving an edition record does **not** archive its events: there is **no cascade**. Archiving a whole edition is therefore a plan of single steps, so that every change is visible.

## Who can do this
Only an **admin**. Editors may archive the single events, but never the edition record.

## Steps
1. Read the edition with `list_editions` (filter `year`).
2. List all its live events with `list_events` (`edition_id`, `archived=false`).
3. Run the pre-archiving checklist (PROC-12) for the edition.
4. **Write the full plan first:** one `archive_record` line per event, then one for the edition. Show it to the requester.
5. Archive each event with `archive_record` (`entity=events`).
6. Archive the edition last with `archive_record` (`entity=editions`).
7. Sessions keep their own flag; archive them only if the requester asks.
8. Notify the team (PROC-15).

## Checks before and after
- **Before:** the plan lists every live event of that edition and nothing from other editions.
- **After:** every event of the edition is `archived`, then the edition is `archived`. Other editions are unchanged.

## Common mistakes
- Archiving only the edition and assuming its events follow.
- Including events from another edition that have the same name.
- Running the plan without showing it first.
