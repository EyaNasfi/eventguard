# EventGuard web UI

React + Vite + TypeScript (strict) + Tailwind CSS + React Router. Dark operations console for the EventGuard lab. All data is fictional.

## Run

```powershell
$env:Path = "C:\Program Files\nodejs;$env:Path"   # if npm is not on PATH
cd web
npm install
npm run dev          # http://localhost:5173
npm run typecheck; npm run lint; npm run build
```

### Mock mode (default)

`VITE_USE_MOCKS=true` (or no `web/.env.local`). Every page runs on bundled fictional data: a copy of EventSim seed 42 plus a scripted demo agent. The **Demo guide** in the top bar replays the jury script (normal task on C3, attack on C0, same attack blocked on C3).

### Live mode (Events against a real EventSim)

1. Run EventSim on `127.0.0.1:8000`, for example `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build --wait` from the repo root.
2. Copy `web/.env.example` to `web/.env.local`, set `VITE_USE_MOCKS=false`, and put in the three local user tokens of that EventSim.
3. `npm run dev`. The Events page now reads and archives on EventSim. The other pages keep their "Sample data · not measured" label, and the demo controls are hidden.

> **Local development only.** By Vite convention, `VITE_*` values can end up in the browser bundle. This project limits that: client code never reads the tokens, `envPrefix` in `vite.config.ts` only exposes `VITE_USE_MOCKS`, and the tokens are attached server-side by the dev proxy. The proxy only exists in `npm run dev`. Even so, use throwaway fictional tokens here, never the lab's real ones, and never deploy a build that was configured with tokens.

The EventSim test-only routes and their token are never used by the front end.

## Layout

| Path | What |
|---|---|
| `src/api/types.ts` | The data contract (EventSim types mirror `eventsim/models.py`; gateway-side types are a proposal) |
| `src/api/live.ts` | Real EventSim calls (through the `/eventsim` dev proxy) |
| `src/api/mock/` | Fictional data and the scripted demo engine |
| `src/components/ui/` | Base components; `status.ts` is the single state vocabulary |
| `src/components/agent/` | Cue sheet, preview card, untrusted-text frame |
| `src/pages/` | One file per page; Gateway, Attack lab and Results are paused ("coming later") |
| `/dev/components` | Component gallery |

Status of each page, the live-mode checks and the endpoints still needed: `docs/frontend/status.md`.
