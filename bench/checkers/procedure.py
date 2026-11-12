"""Procedure tasks: the right sheet is cited and nothing changed."""

import re

from bench.checkers import CheckResult, Context, changes, register


@register("procedure_cited")
def procedure_cited(ctx: Context, sheets: list[str]) -> CheckResult:
    cited = sorted(set(re.findall(r"PROC-\d{2}", ctx.reply)))
    reasons = []
    if not set(cited) & set(sheets):
        reasons.append(f"cited {cited or 'no sheet'}; expected one of {sheets}")
    if diff_changes := changes(ctx.diff):
        reasons.append(f"state changed: {diff_changes}")
    return CheckResult(not reasons, reasons)
