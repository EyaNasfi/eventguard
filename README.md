# EventGuard

Research lab that builds, secures and evaluates a tool-using AI agent on **EventSim**, a simulated event platform. All data is generated and fictional.

Status: Sprint 0 (EventSim) done during Sprint 1. Gateway, n8n agent and benchmark are coming in S1. See [docs/sprints/](docs/sprints/).

## Layout

| Folder | Content |
|---|---|
| `eventsim/` | Simulated platform: FastAPI + SQLModel, seeded generator, test endpoints, reference duplication script |
| `tests/` | pytest suite |
| `docs/` | decisions, threat model, sprint logs and reports |

## Run the lab

```bash
cp .env.example .env          # then replace every change-me value
docker compose up -d --build  # EventSim on the internal network only
# host access for the harness / debugging (127.0.0.1 only):
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

## Develop and test (Python 3.12)

```bash
py -3.12 -m venv .venv && .venv/Scripts/pip install -e ".[dev]"   # Windows
ruff check . && ruff format --check . && mypy
pytest --cov=eventsim
```

## Reference duplication (FR-SIM-10)

```bash
EVENTSIM_URL=http://localhost:8000 EVENTSIM_TOKEN_ADMIN=... python -m eventsim.reference --source 2026 --target 2027
```

## EventSim API (v0)

Every route except `/health` needs `Authorization: Bearer <user token>`.

| Method | Path | Min. role |
|---|---|---|
| GET | `/health` | none |
| GET | `/me` | reader |
| GET | `/editions` (`year`, `status`, `archived`), `/editions/{id}` | reader |
| GET | `/events` (`edition_id`, `year`, `type`, `status`, `archived`), `/events/{id}` | reader |
| GET | `/sessions` (`event_id`, `speaker_id`, `archived`), `/sessions/{id}` | reader |
| GET | `/speakers` (`q`, `archived`), `/speakers/{id}` | reader |
| GET | `/partners` (`q`, `tier`, `event_id`, `archived`), `/partners/{id}` | reader |
| GET | `/attendees` (`event_id`, `q`, `archived`), `/attendees/{id}` | **admin** |
| GET | `/search?q=` (attendees in results for admin only) | reader |
| GET | `/config` | admin |
| POST | `/editions` | admin |
| POST | `/events`, `/sessions` | editor **in a draft edition**; admin anywhere |
| POST | `/speakers`, `/partners` | editor |
| POST | `/attendees` | admin |
| POST | `/sessions/{id}/speakers`, `/events/{id}/partners` (links) | editor in a draft edition; admin anywhere |
| PATCH | `/{entity}/{id}` | editor for speakers, partners and draft-edition events/sessions; admin for everything |
| POST | `/events/{id}/archive`, `/events/{id}/unarchive` | editor |
| POST | `/{other entity}/{id}/archive`, `.../unarchive` | admin |
| POST | `/notifications` (stored in the outbox) | editor |
| GET | `/outbox` | admin |
| POST/GET | `/_test/reset`, `/_test/snapshot`, `/_test/state-diff`, `/_test/export`, `/_test/outbox`, `/_test/canaries` | `X-Test-Token` header (harness only) |

There is no DELETE route. Editions and events have `status: draft | active | archived`; event `internal_notes` are hidden from reader. The full matrix is in `eventsim/api.py` and ADR-002 rev. 1.

Seed 42: editions 2025 (active), 2026 (active), 2027 (draft, empty); 22 events (11 per year, one archived 2026 evening); the reference duplication 2026 → 2027 creates **10** events.

Manual checks: [docs/manual-test-guide.md](docs/manual-test-guide.md).
