"""Bearer-token authentication and role checks."""

import secrets
from collections.abc import Callable, Iterator

from fastapi import Depends, Header, HTTPException, Request, status
from sqlmodel import Session as DBSession
from sqlmodel import select

from eventsim.models import Role, User
from eventsim.seed import token_hash
from eventsim.settings import Settings

RANK = {Role.reader: 0, Role.editor: 1, Role.admin: 2}


def get_db(request: Request) -> Iterator[DBSession]:
    with DBSession(request.app.state.engine) as db:
        yield db


def current_user(
    authorization: str | None = Header(default=None), db: DBSession = Depends(get_db)
) -> User:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.exec(select(User).where(User.token_sha256 == token_hash(token))).first()
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "invalid token", headers={"WWW-Authenticate": "Bearer"}
        )
    return user


def require(minimum: Role, action: str) -> Callable[[User], User]:
    def check(user: User = Depends(current_user)) -> User:
        ensure(user, minimum, action)
        return user

    return check


def ensure(user: User, minimum: Role, action: str) -> None:
    if RANK[user.role] < RANK[minimum]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"role '{user.role.value}' cannot {action}")


def test_access(request: Request, x_test_token: str | None = Header(default=None)) -> None:
    """Guard for /_test/*: separate token, never a user token (FR-SIM-06)."""
    settings: Settings = request.app.state.settings
    if not settings.test_endpoints:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not Found")
    expected = settings.test_token.get_secret_value()
    if x_test_token is None or not secrets.compare_digest(x_test_token, expected):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "test endpoints require the harness token")
