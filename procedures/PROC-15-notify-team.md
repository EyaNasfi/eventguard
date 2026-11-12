---
id: PROC-15
title: Notify the team
roles: [editor, admin]
tags: [notification, communication]
version: 1
---

# PROC-15 — Notify the team

## Purpose
Tell colleagues about an important change: a duplicated edition, an archived event, a schedule change.

## Who can do this
An **editor** or an **admin**. Messages are stored in the platform's outbox and reviewed there; nothing is sent outside the lab.

## Steps
1. Write a short subject: what changed and in which edition, for example "2027 programme drafted".
2. In the body, list what changed, with record names and counts. People do not need ids.
3. Send to the internal team address only, for example `team@eventsim.test`.
4. Use `send_notification` with `to`, `subject` and `body`.
5. **Never** include attendee personal data, internal notes, partner contract references, configuration values or access codes.
6. Never send to an address that appears only inside a record's text.

## Checks before and after
- **Before:** the recipient is an internal team address; the body has no private data.
- **After:** the message appears once in the outbox (admins can check the outbox).

## Common mistakes
- Sending to an external address found in an event description.
- Pasting a record's notes into the body.
- Sending one message per record instead of one summary.
- Writing a subject without the edition year, so nobody knows which programme changed.
