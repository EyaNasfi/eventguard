"""EventSim application factory. Run with: uvicorn eventsim.main:app"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import Session as DBSession
from sqlmodel import SQLModel, select

from eventsim import api, harness
from eventsim.db import make_engine
from eventsim.models import User
from eventsim.seed import seed_database
from eventsim.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()  # values come from the env
    engine = make_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        SQLModel.metadata.create_all(engine)
        with DBSession(engine) as db:
            if db.exec(select(User)).first() is None:
                seed_database(db, settings.default_seed, harness.role_tokens(settings))
        yield
        engine.dispose()

    app = FastAPI(title="EventSim", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.engine = engine
    app.state.seed = settings.default_seed
    app.state.snapshot = None
    app.include_router(harness.router)
    app.include_router(api.router)
    return app


def app() -> FastAPI:
    """Factory for `uvicorn --factory eventsim.main:app`."""
    return create_app()
