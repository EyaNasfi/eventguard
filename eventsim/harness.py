"""Test-only endpoints for the evaluation harness (FR-SIM-06, FR-SIM-07).

Guarded by X-Test-Token, a secret the gateway and the agent never receive.
User bearer tokens (admin included) do not open these routes.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session as DBSession
from sqlmodel import col, select

from eventsim import snapshot
from eventsim.auth import get_db, test_access
from eventsim.db import recreate_schema
from eventsim.models import Canary, Outbox, Role
from eventsim.schemas import ResetRequest
from eventsim.seed import seed_database
from eventsim.settings import Settings

router = APIRouter(prefix="/_test", dependencies=[Depends(test_access)], include_in_schema=False)


def reset_state(request: Request, seed: int) -> None:
    settings: Settings = request.app.state.settings
    recreate_schema(request.app.state.engine)
    with DBSession(request.app.state.engine) as db:
        seed_database(db, seed, role_tokens(settings))
    request.app.state.seed = seed
    request.app.state.snapshot = None


def role_tokens(settings: Settings) -> dict[Role, str]:
    return {
        Role.reader: settings.token_reader.get_secret_value(),
        Role.editor: settings.token_editor.get_secret_value(),
        Role.admin: settings.token_admin.get_secret_value(),
    }


@router.post("/reset")
def reset(body: ResetRequest, request: Request) -> dict[str, Any]:
    reset_state(request, body.seed)
    return {"status": "reset", "seed": body.seed}


@router.post("/snapshot")
def take_snapshot(request: Request, db: DBSession = Depends(get_db)) -> dict[str, Any]:
    request.app.state.snapshot = snapshot.dump(db)
    counts = {t: len(rows) for t, rows in request.app.state.snapshot.items()}
    return {"status": "snapshot taken", "seed": request.app.state.seed, "counts": counts}


@router.get("/state-diff")
def state_diff(request: Request, db: DBSession = Depends(get_db)) -> dict[str, Any]:
    if request.app.state.snapshot is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "no snapshot taken since last reset")
    result = snapshot.diff(request.app.state.snapshot, snapshot.dump(db))
    return {"seed": request.app.state.seed, "empty": snapshot.is_empty(result), "tables": result}


@router.get("/export")
def export(db: DBSession = Depends(get_db)) -> dict[str, Any]:
    return snapshot.dump(db)


@router.get("/outbox")
def outbox(db: DBSession = Depends(get_db)) -> list[dict[str, Any]]:
    return [m.model_dump(mode="json") for m in db.exec(select(Outbox).order_by(col(Outbox.id)))]


@router.get("/canaries")
def canaries(db: DBSession = Depends(get_db)) -> list[dict[str, Any]]:
    return [c.model_dump(mode="json") for c in db.exec(select(Canary).order_by(col(Canary.id)))]
