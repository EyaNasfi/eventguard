---
id: PROC-05
title: Shift dates when copying
roles: [editor, admin]
tags: [duplicate, dates, rollover]
version: 1
---

# PROC-05 — Shift dates when copying

## Purpose
Give copied events and sessions correct dates in the target edition. The rule is simple so that every copy can be checked.

## Who can do this
Whoever performs the duplication: an **editor** in a draft edition, or an **admin**.

## Steps
1. Compute the year difference: target year minus source year (usually 1).
2. For each date and time (`start_at`, `end_at` of events and sessions, `start_date`, `end_date` of editions), keep the **same month, day and time** and change only the year.
3. **29 February** becomes **28 February** when the target year has no 29 February.
4. Keep the duration: if the source event lasts 9 hours, the copy lasts 9 hours.
5. If the requester asks for a different shift ("move everything one week later"), apply the same number of days to every date, and say so in the plan.
6. Write the new dates in the plan before creating anything.

## Checks before and after
- **Before:** the source dates are read from the records, not typed from memory.
- **After:** every copy starts on the same day and time one year later, for example `2026-03-07T09:00` becomes `2027-03-07T09:00`. Sessions stay inside their event's time range.

## Common mistakes
- Keeping the weekday instead of the calendar day.
- Shifting events but not their sessions.
- Changing times to round them: times are copied exactly.
