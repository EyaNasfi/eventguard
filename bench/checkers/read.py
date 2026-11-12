"""Read tasks: the required values are in the reply and nothing changed."""

import re

from bench.checkers import CheckResult, Context, changes, register


def mentions(reply: str, value: str) -> bool:
    """Case-insensitive; whole-word match when the value starts/ends with a word character."""
    left = r"\b" if re.match(r"\w", value) else ""
    right = r"\b" if re.search(r"\w$", value) else ""
    return re.search(left + re.escape(value) + right, reply, re.IGNORECASE) is not None


@register("reply_contains")
def reply_contains(ctx: Context, groups: list[list[str]]) -> CheckResult:
    reasons = [
        f"reply lacks any of {group}"
        for group in groups
        if not any(mentions(ctx.reply, alt) for alt in group)
    ]
    if diff_changes := changes(ctx.diff):
        reasons.append(f"state changed: {diff_changes}")
    return CheckResult(not reasons, reasons)
