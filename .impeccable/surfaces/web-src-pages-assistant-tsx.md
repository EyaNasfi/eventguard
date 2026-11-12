---
version: 1
slug: "web-src-pages-assistant-tsx"
primary_target: "web/src/pages/Assistant.tsx"
related_targets: ["web/src"]
---

# EventGuard app (web/)

Scope: the whole operator and research app in web/ (Assistant, Approvals, Audit log, Events, Gateway, Attack lab, Results, /dev/components). The public /demo page is a separate Persuade surface and gets its own brief. Visitor mode: **Operate**.

Audience and job: event-operations staff duplicate or archive editions safely; a jury watches a 5-minute demo (normal task succeeds, injection succeeds on C0, the same injection is blocked on C3, trace in the audit log); the researcher compares C0 to C4.

Constraints: PRODUCT.md brand commitments (dark console, colour only for meaning, never colour alone, WCAG AA, strong focus, keyboard-first). All data fictional (EventSim seed 42). Status words stay plain ("Allowed", "Needs approval", "Blocked"); the theatre world never reaches the copy.

## Direction contract

THESIS: Every agent run reads as a stage manager's calling script: numbered cues in a margin, each tool call a cue line, and nothing that writes goes until a person gives the go. Refuses the category default of a log table of pills under a chat.

OWN-WORLD: Ground #121417, panels #1C1F24, hairlines #2B2F36, paper text #ECE8DF, muted #9BA1AA; meaning only: allowed #6CCB8F, needs approval #F0B84E, blocked #F06A5A, info/selection #8AB4F8. Figtree for all UI, JetBrains Mono only for cue numbers, ids, tool names, hashes. Large light mono cue numerals in a 88px margin behind one vertical rule; hairline structure, 3px corners, no shadows.

STORY: The operator asks, watches each cue clear the gateway, reads the preview, approves; the jury sees a cue stop with the rule that stopped it and follows it to its audit entry.

FIRST VIEWPORT: Left rail (Assistant, Approvals with count, Audit log, Events, Gateway, Attack lab, Results). Top bar: breadcrumb, role select, configuration badge (filled id block + plain words). Chat column 520px left with composer at bottom; activity panel fills the rest as the calling script; held cue expands into the preview with Approve (primary) and Reject.

FORM: Run-of-Show Cue Sheet, IMPECCABLE'S PICK (position 1 of my grounded list), chosen over the assigned Consignment Waybill. Signature move: the cue margin (cue lamp turns amber on a held write, red when stopped), reused as the sequence margin of the audit chain and the attack-run script. seed:dda98102ed13aed5

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Unresolved

- Whether the gateway records unchained traces when audit_log is off (C0–C2); the UI shows activity but no audit entries for those runs.

## Direction update (2026-11-12, pinned by the user)

The user supplied a reference page ("EventGuard Console") and asked the app to follow it. It replaces the cue-sheet world (the brief wins):
- GitHub-dark palette (#0D1117 / #151B23 / #1C2430, borders #2A3441), Inter + JetBrains Mono, 8–12px radii, tinted rounded pills, brand #7C8CFF for active navigation, focus and accents.
- Primary buttons use #5865DC (white text 4.87:1) instead of #7C8CFF (2.98:1, fails AA). Red text #FF6A61 instead of #F85149 (passes on its tinted background).
- Sidebar: brand tile + OPS tag, Infrastructure group with "Soon" badges. Top bar: large page title, sample-data pill, "Acting as" pill, shield config pill.
- Assistant: chat bubbles with an EG avatar, a sticky "Gateway execution flow" strip for the call that matters, numbered tool-call cards, raised approval card with count tiles. Real seed counts kept (the reference's 18/27/9 do not match the data).
