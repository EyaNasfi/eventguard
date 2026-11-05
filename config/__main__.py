"""Print the active configuration and its hash:  python -m config

Reads EVENTGUARD_CONFIG and GEMINI_MODEL from the environment (or .env; pass --env-only
to ignore .env). Exits 2 with a
clear message if the configuration cannot be resolved.
"""

import json
import os
import sys

from dotenv import dotenv_values

from config.loader import ROOT, ConfigError, load_active


def main() -> int:
    # --env-only ignores .env, e.g. to check the refusal when EVENTGUARD_CONFIG is unset.
    use_dotenv = "--env-only" not in sys.argv[1:]
    dotenv = dotenv_values(ROOT / ".env") if use_dotenv else {}
    env = {k: v for k, v in dotenv.items() if v is not None} | dict(os.environ)
    try:
        config = load_active(env=env)
    except ConfigError as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2
    summary = {
        "name": config.name,
        "hash": config.hash,
        "model": config.model.name,
        "layers_on": [k for k, v in config.layers.model_dump().items() if v],
        "tools": len(config.tools),
        "system_prompt_sha256": config.system_prompt_sha256,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
