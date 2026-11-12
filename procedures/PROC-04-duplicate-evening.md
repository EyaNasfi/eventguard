---
id: PROC-04
title: Duplicate an evening
roles: [editor, admin]
tags: [duplicate, evening, event]
version: 1
---

# PROC-04 — Duplicate an evening

## Purpose
Copy an evening event (a gala, a networking night or an awards evening) into another edition. Evenings often have partners but few sessions.

## Who can do this
An **editor** when the target edition is a **draft**; an **admin** anywhere.

## Steps
1. Find the evening with `list_events` (`type=evening`). Read it with `get_event`.
2. **Check its status.** A cancelled evening is archived, and archived evenings are **not** duplicated. Tell the requester instead.
3. List its live sessions, if any, with `list_sessions`.
4. Write the plan: the event, its sessions, its partner links.
5. Create the evening with `create_event`: same name, type `evening`, venue and description, status `draft`, times moved by the year difference (PROC-05).
6. Create sessions with `create_session`, then link speakers (PROC-06).
7. Link partners with `link_partner_to_event` (PROC-07).
8. Report the new event id and what was linked.

## Checks before and after
- **Before:** the evening is live (`archived=false`); the target edition is `draft`.
- **After:** one new `draft` evening with the same partners; the source is unchanged.

## Common mistakes
- Copying a cancelled (archived) evening.
- Moving an evening to another weekday to keep it on a Friday: dates move by the year difference only, unless the requester asks for a shift (PROC-05).
- Copying the guest list: attendees are never copied.
