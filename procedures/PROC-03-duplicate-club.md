---
id: PROC-03
title: Duplicate a club
roles: [editor, admin]
tags: [duplicate, club, event]
version: 1
---

# PROC-03 — Duplicate a club

## Purpose
Copy one club meeting into another edition. Clubs are short, recurring evening meetings of a community, usually with one or two sessions.

## Who can do this
An **editor** when the target edition is a **draft**; an **admin** anywhere. A reader cannot create anything.

## Steps
1. Find the club with `list_events` (`type=club`) or `search_records` with its name. Read it with `get_event`.
2. Confirm the club is not archived and note its `partner_ids`.
3. List its live sessions with `list_sessions` (`event_id`, `archived=false`); read each with `get_session` for its speakers.
4. Write the plan first: 1 event, N sessions, the speaker links and the partner links.
5. Create the club with `create_event` in the target edition: same name, type `club`, venue and description, status `draft`, start and end moved by the year difference (PROC-05).
6. Create each session with `create_session` on the new club.
7. Re-link speakers (PROC-06) and partners (PROC-07).
8. Report what was created, with the new ids.

## Checks before and after
- **Before:** the target edition exists and is `draft`; the club is not already copied there (search by name in the target year).
- **After:** exactly one new club in the target edition, `draft`, with the same sessions, speakers and partners.

## Common mistakes
- Duplicating twice because nobody checked for an existing copy.
- Copying the club into an `active` edition: an editor is refused (HTTP 403).
- Changing the club's name: copies keep the same name.
