"""Smoke run: a few tasks, one model, C0, one repetition (S2-07). A pipeline test, not a measure.

    python -m bench.smoke --tasks PRC-01,RD-01,DUP-01,ARC-01,RD-02

Appends one line per task to results/smoke.jsonl and prints a summary: pass/fail, failure
classes, mean tokens per run, and the number of Gemini calls (model calls + 1 version probe).
"""

import argparse
import json
import sys
import time
from pathlib import Path
from statistics import mean

from agent.model_probe import served_version
from agent.n8n_lab import load_env
from bench.agent_client import run_task
from bench.schema import TASKS_DIR, load_task

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "smoke.jsonl"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", required=True, help="comma-separated task ids")
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument(
        "--pause",
        type=int,
        default=65,
        help="seconds between tasks: the free tier allows 15 generation requests per minute",
    )
    args = parser.parse_args(argv)
    tasks = [load_task(TASKS_DIR / f"{tid.strip()}.yaml") for tid in args.tasks.split(",")]
    env = load_env()
    probe = served_version(env["GEMINI_API_KEY"], env["GEMINI_MODEL"])
    print(f"model {probe['model']} served as {probe['model_version']}")
    run_id = time.strftime("smoke-%Y%m%dT%H%M%S")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for n, task in enumerate(tasks):
        if n:
            time.sleep(args.pause)
        row = run_task(task, run_id, str(probe["model_version"]))
        rows.append(row)
        with args.out.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        verdict = "PASS" if row["passed"] else f"FAIL ({row['failure_class']})"
        print(
            f"{task.id} [{task.role}] {verdict} in {row['latency_ms']} ms, "
            f"{row['model_calls']} model calls, {row['total_tokens']} tokens, "
            f"tools {row['tools']}"
        )
        for reason in row["reasons"]:
            print(f"    - {reason}")
    tokens = [r["total_tokens"] for r in rows if r["total_tokens"]]
    calls = sum(r["model_calls"] or 0 for r in rows) + 1
    print(
        f"\n{sum(r['passed'] for r in rows)}/{len(rows)} passed; "
        f"mean tokens per run {mean(tokens):.0f}; Gemini generation calls {calls} "
        f"(incl. 1 probe); run id {run_id}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
