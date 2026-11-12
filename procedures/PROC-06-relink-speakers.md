---
id: PROC-06
title: Re-link speakers to copied sessions
roles: [editor, admin]
tags: [duplicate, speaker, link]
version: 1
---

# PROC-06 — Re-link speakers to copied sessions

## Purpose
Keep the same speakers on copied sessions without creating duplicate speaker records. A speaker is a global record shared by all editions.

## Who can do this
An **editor** when the session belongs to a **draft** edition; an **admin** anywhere.

## Steps
1. For each source session, read `speaker_ids` with `get_session`.
2. Do **not** create speakers. The copy uses the same speaker ids.
3. After creating the new session, call `link_speaker_to_session` once per speaker id, with the **new** session id.
4. If a speaker record is archived, ask the requester before linking it.
5. If you find two records for the same person, stop and follow PROC-16.
6. Report how many links were created per session.

## Checks before and after
- **Before:** you have the list of speaker ids per source session.
- **After:** every new session has the same speaker ids as its source session. The total number of speakers in the platform has not changed.

## Common mistakes
- Calling `create_speaker` for people who already exist.
- Linking speakers to the source session again (it already has them).
- Forgetting sessions that have two or more speakers.
- Linking a speaker twice to the same session: one link per speaker is enough.
