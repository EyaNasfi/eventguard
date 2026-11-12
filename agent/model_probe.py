"""Which model version does Google actually serve? (S2-05, NFR-02)

n8n does not record the served version, and Google may serve a newer version than requested
(Sprint 0: `gemini-3.5-flash` served as `gemini-3.6-flash`). One tiny call (about 10 tokens)
records it; the smoke run calls this once per batch.

    python -m agent.model_probe
"""

import sys

from google import genai
from google.genai import types

from agent.n8n_lab import load_env


def served_version(api_key: str, model: str) -> dict[str, object]:
    client = genai.Client(api_key=api_key)
    r = client.models.generate_content(
        model=model,
        contents="Reply with the single word: ok",
        config=types.GenerateContentConfig(temperature=0.0, max_output_tokens=8),
    )
    tokens = r.usage_metadata.total_token_count if r.usage_metadata else None
    return {"model": model, "model_version": r.model_version, "probe_tokens": tokens}


def main() -> int:
    env = load_env()
    print(served_version(env["GEMINI_API_KEY"], env["GEMINI_MODEL"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
