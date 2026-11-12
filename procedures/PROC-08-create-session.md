---
id: PROC-08
title: Create a session
roles: [editor, admin]
tags: [session, create]
version: 1
---

# PROC-08 — Create a session

## Purpose
Add a talk, a workshop or a panel to an existing event.

## Who can do this
An **editor** when the event belongs to a **draft** edition; an **admin** anywhere. A reader cannot create sessions.

## Steps
1. Find the event with `list_events` or `search_records`; note its id and its edition.
2. Check the edition status with `get_edition`. If it is not `draft` and you are an editor, stop: the request needs an admin.
3. Agree the title, start and end time, and room with the requester.
4. Check that the session times fall inside the event's `start_at` and `end_at`.
5. Create it with `create_session` (`event_id`, `title`, `start_at`, `end_at`, `room`).
6. Link speakers with `link_speaker_to_session` (PROC-06). Use existing speaker records.
7. Report the new session id.

## Checks before and after
- **Before:** the event is live and its edition is `draft` (for editors).
- **After:** `list_sessions` with the event id shows the new session with the right times.

## Common mistakes
- Times outside the event's time range.
- Creating the session on the source event during a duplication.
- Typing a speaker's name into the title instead of linking a speaker record.
- Creating the same session twice after a slow answer: list the sessions first to check.
