---
id: PROC-13
title: Year rollover checklist
roles: [admin, editor]
tags: [rollover, checklist, edition]
version: 1
---

# PROC-13 — Year rollover checklist

## Purpose
Move the team from one year to the next in a safe order: prepare the new edition, publish it, then close the old one.

## Who can do this
An **admin** owns the rollover. **Editors** do the duplication work inside the draft edition.

## Steps
1. **Admin:** create the N+1 edition as `draft` with `create_edition` (dates moved per PROC-05).
2. **Editors:** duplicate the programme (PROC-01) and fix details in the draft.
3. **Review:** count events per type in N and N+1; check that speakers and partners are linked, not duplicated.
4. **Naming:** check that names follow PROC-17.
5. **Admin:** publish N+1 by setting its status to `active` with `update_record` when the team agrees.
6. **Admin:** after year N has ended, archive it with the composed plan (PROC-10).
7. **Notify** the team at each milestone (PROC-15).

## Checks before and after
- **Before:** N is `active`; N+1 does not exist yet or is `draft`.
- **After:** N+1 is `active` and complete; N is archived event by event, then as an edition.

## Common mistakes
- Archiving N before N+1 is ready.
- Publishing N+1 while editors are still changing it.
- Editors trying to publish: only admins change an edition's status.
