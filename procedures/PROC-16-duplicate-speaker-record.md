---
id: PROC-16
title: Handle a duplicate speaker record
roles: [editor, admin]
tags: [speaker, data-quality, duplicate-record]
version: 1
---

# PROC-16 — Handle a duplicate speaker record

## Purpose
Fix the case where the same person exists twice as a speaker, without losing any session link.

## Who can do this
An **editor** can update speakers and link them in draft editions. Archiving the extra speaker record needs an **admin**.

## Steps
1. Search with `list_speakers` (`q` = last name) or `search_records`. Compare first name, last name, email and company.
2. Decide which record to keep: the one with the most session links, or the older one.
3. List the sessions of the extra record with `list_sessions` (`speaker_id`).
4. For sessions in **draft** editions, link the kept record with `link_speaker_to_session`.
5. For sessions in **active** editions, ask an admin to do the linking.
6. Update the kept record with `update_record` if the extra one had better information.
7. Ask an admin to **archive** (never delete) the extra record.

## Checks before and after
- **Before:** both records really are the same person (same email, or confirmed by the team).
- **After:** every session that had the extra record also has the kept record; the extra record is archived.

## Common mistakes
- Merging two different people who share a name.
- Archiving the extra record before moving its links.
- Creating a third record to be safe.
