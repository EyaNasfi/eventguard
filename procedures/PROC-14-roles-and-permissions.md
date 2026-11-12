---
id: PROC-14
title: Roles and permissions
roles: [reader, editor, admin]
tags: [roles, permissions, access]
version: 1
---

# PROC-14 — Roles and permissions

## Purpose
Explain who may do what, so that requests go to the right person.

## Who can do this
Everyone should know this sheet. Only an **admin** can change a person's role, outside the platform.

## Steps
1. **Reader:** reads editions, events, sessions, speakers and partners. Cannot read attendees. Cannot write anything. Does not see the internal notes of events.
2. **Editor:** everything a reader can, plus:
   - create and update events, sessions and links **only in draft editions**;
   - create and update speakers and partners (they are global);
   - archive and unarchive **single events** in any edition;
   - send team notifications.
3. **Admin:** everything, including editions, attendees, configuration, archiving any record, and reading the outbox.
4. **Nobody** can delete. Archive instead.
5. When the platform refuses an action (HTTP 403), do not retry with another account: escalate (PROC-18).

## Checks before and after
- **Before:** match the request to the lowest role that can do it.
- **After:** the action was done by an account allowed to do it.

## Common mistakes
- Asking an editor to change a published (`active`) edition.
- Sharing attendee data with readers or editors.
- Treating a 403 as a bug instead of a rule.
