---
id: PROC-02
title: Duplicate a conference
roles: [editor, admin]
tags: [duplicate, conference, event]
version: 1
---

# PROC-02 — Duplicate a conference

## Purpose
Copy one conference, with its sessions and links, into another edition. Conferences are full-day events with several sessions, speakers and partners.

## Who can do this
An **editor** when the target edition is a **draft**; an **admin** anywhere. A reader cannot.

## Steps
1. Find the source conference with `list_events` (`type=conference`, `year`) or `search_records`, then read it with `get_event`.
2. Check that it is not archived. Archived conferences are not duplicated.
3. List its sessions with `list_sessions` (`event_id`, `archived=false`) and read each one with `get_session` to get its `speaker_ids`.
4. Write the plan: the new event, each new session with shifted times, each speaker link, each partner link.
5. Create the event with `create_event`: same name, type, venue and description, status `draft`, dates shifted (PROC-05).
6. Create each session with `create_session` on the new event, with the same title and room.
7. Link each speaker with `link_speaker_to_session` (PROC-06).
8. Link each partner of the source event with `link_partner_to_event` (PROC-07).

## Checks before and after
- **Before:** the target edition is `draft`; you know the number of live sessions, speaker links and partner links.
- **After:** the new conference has the same number of sessions and the same speakers and partners. The source conference is unchanged.

## Common mistakes
- Copying `internal_notes`: they stay with the original event.
- Forgetting that archived sessions are skipped.
- Linking speakers to the old session instead of the new one.
