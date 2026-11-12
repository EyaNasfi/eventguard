# EventGuard — agent instructions

Research lab: a tool-using AI agent on EventSim (a simulated event platform), secured by a gateway and evaluated with an attack bench. All data is fictional. Start with `docs/START-HERE.md`.

## Standing rules

- **Never push to GitHub.** No `git push`, and no `gh` command that changes the remote (PRs, merges, releases, settings), unless Aya explicitly asks for a push in the current session. Work stays on local branches until then. (PL decision #3, recorded in `docs/decisions.md` as ADR-004.)
- Never merge to `main` without Aya's explicit go.
- Never print, log or commit secrets (`.env`, tokens, the Gemini key). `web/.env.local` is gitignored.
- The `/_test/*` token is for the evaluation harness only. It never goes into the gateway, the agent or the front end.
- Backend folders (`eventsim/`, `gateway/`, `agent/`, `bench/`, `config/`) change only in their own sprint task, not as a side effect of front-end work.
- Subagents: use a cheaper model (`sonnet`, or `haiku` for mechanical jobs). `.claude/settings.json` sets `CLAUDE_CODE_SUBAGENT_MODEL=sonnet`.

## Checks

- Python: `.\.venv\Scripts\python -m pytest -q`, `ruff check .`, `ruff format --check .`, `mypy`.
- Web: in `web/`, `npm run typecheck`, `npm run lint`, `npm run build`.
