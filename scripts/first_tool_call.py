"""P0 evidence: a Gemini model calls a single `get_event` tool on EventSim.

Uses at most 2 Gemini calls (tool request, then final answer). Reads GEMINI_API_KEY,
GEMINI_MODEL and EVENTSIM_TOKEN_READER from the environment or `.env`; the key is never
printed or logged. EventSim must be reachable (dev compose override or local uvicorn).

    python scripts/first_tool_call.py [--event-id 12] [--eventsim-url http://127.0.0.1:8000]

Writes one JSON line to logs/first_tool_call.jsonl and exits 0 only if the model called
the tool and its answer contains the event's real name and venue.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from dotenv import dotenv_values
from google import genai
from google.genai import types

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "logs" / "first_tool_call.jsonl"

GET_EVENT = types.FunctionDeclaration(
    name="get_event",
    description="Get one EventSim event (conference, club or evening) by its numeric id.",
    parameters_json_schema={
        "type": "object",
        "properties": {"event_id": {"type": "integer", "description": "Event id"}},
        "required": ["event_id"],
    },
)


def settings() -> dict[str, str]:
    values = {k: v for k, v in dotenv_values(ROOT / ".env").items() if v is not None}
    values.update(os.environ)
    missing = [
        k for k in ("GEMINI_API_KEY", "GEMINI_MODEL", "EVENTSIM_TOKEN_READER") if not values.get(k)
    ]
    if missing:
        sys.exit(f"missing in environment/.env: {', '.join(missing)}")
    return values


def git_commit() -> str | None:
    try:
        result = subprocess.run(  # noqa: S603
            ["git", "rev-parse", "HEAD"],  # noqa: S607  (git from PATH, fixed arguments)
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def tokens(response: types.GenerateContentResponse) -> dict[str, int | None]:
    usage = response.usage_metadata
    if usage is None:
        return {"prompt": None, "output": None, "total": None}
    return {
        "prompt": usage.prompt_token_count,
        "output": usage.candidates_token_count,
        "total": usage.total_token_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="First Gemini tool call against EventSim")
    parser.add_argument("--event-id", type=int, default=12)
    parser.add_argument("--eventsim-url", default=None)
    args = parser.parse_args()
    env = settings()
    base_url = args.eventsim_url or env.get("EVENTSIM_URL", "http://127.0.0.1:8000")
    secret = env["GEMINI_API_KEY"]

    eventsim = httpx.Client(
        base_url=base_url, headers={"Authorization": f"Bearer {env['EVENTSIM_TOKEN_READER']}"}
    )
    truth = eventsim.get(f"/events/{args.event_id}").raise_for_status().json()

    client = genai.Client(api_key=secret)
    config = types.GenerateContentConfig(
        temperature=0.0,
        tools=[types.Tool(function_declarations=[GET_EVENT])],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    question = (
        f"In EventSim, what are the name, venue and start date of event {args.event_id}? "
        "Use the get_event tool."
    )
    contents: list[types.Content] = [types.Content(role="user", parts=[types.Part(text=question)])]
    record: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "model_requested": env["GEMINI_MODEL"],
        "temperature": 0.0,
        "event_id": args.event_id,
        "git_commit": git_commit(),
        "calls": [],
    }

    started = time.perf_counter()
    try:
        first = client.models.generate_content(
            model=env["GEMINI_MODEL"], contents=contents, config=config
        )
        record["model_version"] = first.model_version
        record["calls"].append({"step": "tool_request", "tokens": tokens(first)})
        calls = first.function_calls or []
        record["tool_calls"] = [{"name": c.name, "args": c.args} for c in calls]
        answer = ""
        if calls:
            assert first.candidates and first.candidates[0].content  # noqa: S101
            contents.append(first.candidates[0].content)
            parts = []
            for call in calls:
                if call.name != "get_event" or not call.args:
                    result: dict[str, Any] = {"error": f"unknown tool {call.name}"}
                else:
                    event_id = int(call.args["event_id"])
                    result = eventsim.get(f"/events/{event_id}").json()
                parts.append(
                    types.Part.from_function_response(name="get_event", response={"result": result})
                )
            contents.append(types.Content(role="user", parts=parts))
            second = client.models.generate_content(
                model=env["GEMINI_MODEL"], contents=contents, config=config
            )
            record["calls"].append({"step": "final_answer", "tokens": tokens(second)})
            answer = second.text or ""
    except Exception as exc:  # noqa: BLE001  (report any API failure without leaking the key)
        message = str(exc).replace(secret, "***")
        record["error"] = f"{type(exc).__name__}: {message}"
        answer = ""
    record["latency_ms"] = round((time.perf_counter() - started) * 1000)

    record["answer"] = answer
    record["checks"] = {
        "called_get_event": any(c["name"] == "get_event" for c in record.get("tool_calls", [])),
        "asked_right_event": any(
            int((c["args"] or {}).get("event_id", -1)) == args.event_id
            for c in record.get("tool_calls", [])
        ),
        "answer_has_name": truth["name"].casefold() in answer.casefold(),
        "answer_has_venue": truth["venue"].casefold() in answer.casefold(),
        "answer_has_year": truth["start_at"][:4] in answer,
    }
    record["expected"] = {k: truth[k] for k in ("name", "venue", "start_at")}
    record["total_tokens"] = sum((c["tokens"]["total"] or 0) for c in record["calls"])
    record["passed"] = all(record["checks"].values())

    LOG.parent.mkdir(exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    shown = ("model_requested", "model_version", "tool_calls", "answer", "expected", "checks",
             "total_tokens", "latency_ms", "passed")  # fmt: skip
    summary = {k: record[k] for k in shown if k in record}
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if "error" in record:
        print(record["error"], file=sys.stderr)
    return 0 if record["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
