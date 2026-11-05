"""Public EventSim API. There is no DELETE route anywhere: archive / unarchive only.

Role matrix (ADR-002, accepted 2026-11-02):

| action                                   | reader | editor               | admin |
|------------------------------------------|--------|----------------------|-------|
| read editions/events/sessions/speakers/partners | yes | yes             | yes   |
| read event internal_notes                | no     | yes                  | yes   |
| read attendees (all attendee routes)     | no     | no                   | yes   |
| create/update editions                   | no     | no                   | yes   |
| create/update events, sessions, links    | no     | draft edition only   | yes   |
| create/update speakers, partners         | no     | yes (global records) | yes   |
| archive/unarchive events                 | no     | yes, one at a time   | yes   |
| archive/unarchive anything else          | no     | no                   | yes   |
| send notifications                       | no     | yes                  | yes   |
| read outbox, read /config                | no     | no                   | yes   |
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlmodel import Session as DBSession
from sqlmodel import SQLModel, col, select

from eventsim.auth import RANK, current_user, ensure, get_db, require
from eventsim.models import (
    ENTITIES,
    Attendee,
    Edition,
    Event,
    EventPartner,
    EventType,
    Outbox,
    Partner,
    PartnerTier,
    Record,
    Role,
    Session,
    SessionSpeaker,
    Setting,
    Speaker,
    Status,
    StatusRecord,
    User,
)
from eventsim.schemas import (
    UPDATES,
    AttendeeCreate,
    EditionCreate,
    EventCreate,
    Notification,
    PartnerCreate,
    PartnerLink,
    SessionCreate,
    SpeakerCreate,
    SpeakerLink,
)

router = APIRouter()
Json = dict[str, Any]


class EntityName(StrEnum):
    editions = "editions"
    events = "events"
    sessions = "sessions"
    speakers = "speakers"
    partners = "partners"
    attendees = "attendees"


WRITE_ROLE = {
    EntityName.editions: Role.admin,
    EntityName.events: Role.editor,
    EntityName.sessions: Role.editor,
    EntityName.speakers: Role.editor,
    EntityName.partners: Role.editor,
    EntityName.attendees: Role.admin,
}
ARCHIVE_ROLE = {name: Role.admin for name in EntityName} | {EntityName.events: Role.editor}
# Entities whose writes by an editor are limited to draft editions.
EDITION_SCOPED = {EntityName.events, EntityName.sessions}


def now() -> datetime:
    return datetime.now(UTC)


def out(row: SQLModel, **extra: Any) -> Json:
    return row.model_dump(mode="json") | extra


def out_event(event: Event, user: User, **extra: Any) -> Json:
    data = out(event, **extra)
    if user.role is Role.reader:
        del data["internal_notes"]
    return data


def fetch[T: Record](db: DBSession, model: type[T], record_id: int) -> T:
    row = db.get(model, record_id)
    if row is None:
        name = model.__name__.lower()
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{name} {record_id} not found")
    return row


def active_parent[T: Record](db: DBSession, model: type[T], record_id: int) -> T:
    row = fetch(db, model, record_id)
    if row.archived:
        name = model.__name__.lower()
        raise HTTPException(status.HTTP_409_CONFLICT, f"{name} {record_id} is archived")
    return row


def require_draft(user: User, edition: Edition, action: str) -> None:
    """Editors write only into draft editions; admins anywhere."""
    if RANK[user.role] < RANK[Role.admin] and edition.status is not Status.draft:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"role '{user.role.value}' can only {action} in a draft edition "
            f"(edition {edition.year} is {edition.status.value})",
        )


def edition_of(db: DBSession, row: Record) -> Edition:
    if isinstance(row, Session):
        row = fetch(db, Event, row.event_id)
    assert isinstance(row, Event)  # noqa: S101  (only events and sessions are edition-scoped)
    return fetch(db, Edition, row.edition_id)


def save[T: SQLModel](db: DBSession, row: T) -> T:
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def stamps(user: User) -> Json:
    t = now()
    return {"created_at": t, "updated_at": t, "created_by": user.id}


# ---------------------------------------------------------------- identity, config


@router.get("/health")
def health() -> Json:
    return {"status": "ok"}


@router.get("/me")
def me(user: User = Depends(current_user)) -> Json:
    return {"id": user.id, "username": user.username, "role": user.role.value}


@router.get("/config")
def read_config(
    db: DBSession = Depends(get_db),
    _: User = Depends(require(Role.admin, "read the platform configuration")),
) -> Json:
    return {s.key: s.value for s in db.exec(select(Setting).order_by(col(Setting.key))).all()}


# ---------------------------------------------------------------- reads


@router.get("/editions")
def list_editions(
    year: int | None = None,
    edition_status: Status | None = Query(default=None, alias="status"),
    archived: bool | None = None,
    db: DBSession = Depends(get_db),
    _: User = Depends(current_user),
) -> list[Json]:
    query = select(Edition).order_by(col(Edition.year))
    if year is not None:
        query = query.where(Edition.year == year)
    if edition_status is not None:
        query = query.where(Edition.status == edition_status)
    if archived is not None:
        query = query.where(Edition.archived == archived)
    return [out(e) for e in db.exec(query).all()]


@router.get("/editions/{record_id}")
def get_edition(
    record_id: int, db: DBSession = Depends(get_db), _: User = Depends(current_user)
) -> Json:
    edition = fetch(db, Edition, record_id)
    event_ids = db.exec(select(Event.id).where(Event.edition_id == record_id)).all()
    return out(edition, event_ids=sorted(i for i in event_ids if i is not None))


@router.get("/events")
def list_events(
    edition_id: int | None = None,
    year: int | None = None,
    type: EventType | None = None,  # noqa: A002  (public query parameter name)
    event_status: Status | None = Query(default=None, alias="status"),
    archived: bool | None = None,
    db: DBSession = Depends(get_db),
    user: User = Depends(current_user),
) -> list[Json]:
    query = select(Event).order_by(col(Event.start_at), col(Event.id))
    if edition_id is not None:
        query = query.where(Event.edition_id == edition_id)
    if year is not None:
        query = query.join(Edition).where(Edition.year == year)
    if type is not None:
        query = query.where(Event.type == type)
    if event_status is not None:
        query = query.where(Event.status == event_status)
    if archived is not None:
        query = query.where(Event.archived == archived)
    return [out_event(e, user) for e in db.exec(query).all()]


@router.get("/events/{record_id}")
def get_event(
    record_id: int, db: DBSession = Depends(get_db), user: User = Depends(current_user)
) -> Json:
    event = fetch(db, Event, record_id)
    session_ids = db.exec(select(Session.id).where(Session.event_id == record_id)).all()
    partner_ids = db.exec(
        select(EventPartner.partner_id).where(EventPartner.event_id == record_id)
    ).all()
    return out_event(
        event,
        user,
        session_ids=sorted(i for i in session_ids if i is not None),
        partner_ids=sorted(partner_ids),
    )


@router.get("/sessions")
def list_sessions(
    event_id: int | None = None,
    speaker_id: int | None = None,
    archived: bool | None = None,
    db: DBSession = Depends(get_db),
    _: User = Depends(current_user),
) -> list[Json]:
    query = select(Session).order_by(col(Session.start_at), col(Session.id))
    if event_id is not None:
        query = query.where(Session.event_id == event_id)
    if speaker_id is not None:
        query = query.join(SessionSpeaker).where(SessionSpeaker.speaker_id == speaker_id)
    if archived is not None:
        query = query.where(Session.archived == archived)
    return [out(s) for s in db.exec(query).all()]


@router.get("/sessions/{record_id}")
def get_session(
    record_id: int, db: DBSession = Depends(get_db), _: User = Depends(current_user)
) -> Json:
    session = fetch(db, Session, record_id)
    speaker_ids = db.exec(
        select(SessionSpeaker.speaker_id).where(SessionSpeaker.session_id == record_id)
    ).all()
    return out(session, speaker_ids=sorted(speaker_ids))


@router.get("/speakers")
def list_speakers(
    q: str | None = None,
    archived: bool | None = None,
    db: DBSession = Depends(get_db),
    _: User = Depends(current_user),
) -> list[Json]:
    query = select(Speaker).order_by(col(Speaker.last_name), col(Speaker.id))
    if archived is not None:
        query = query.where(Speaker.archived == archived)
    rows = db.exec(query).all()
    if q:
        rows = [s for s in rows if _matches(q, s.first_name, s.last_name, s.email, s.company)]
    return [out(s) for s in rows]


@router.get("/speakers/{record_id}")
def get_speaker(
    record_id: int, db: DBSession = Depends(get_db), _: User = Depends(current_user)
) -> Json:
    speaker = fetch(db, Speaker, record_id)
    session_ids = db.exec(
        select(SessionSpeaker.session_id).where(SessionSpeaker.speaker_id == record_id)
    ).all()
    return out(speaker, session_ids=sorted(session_ids))


@router.get("/partners")
def list_partners(
    q: str | None = None,
    tier: PartnerTier | None = None,
    event_id: int | None = None,
    archived: bool | None = None,
    db: DBSession = Depends(get_db),
    _: User = Depends(current_user),
) -> list[Json]:
    query = select(Partner).order_by(col(Partner.name))
    if tier is not None:
        query = query.where(Partner.tier == tier)
    if event_id is not None:
        query = query.join(EventPartner).where(EventPartner.event_id == event_id)
    if archived is not None:
        query = query.where(Partner.archived == archived)
    rows = db.exec(query).all()
    if q:
        rows = [p for p in rows if _matches(q, p.name, p.contact_email)]
    return [out(p) for p in rows]


@router.get("/partners/{record_id}")
def get_partner(
    record_id: int, db: DBSession = Depends(get_db), _: User = Depends(current_user)
) -> Json:
    partner = fetch(db, Partner, record_id)
    event_ids = db.exec(
        select(EventPartner.event_id).where(EventPartner.partner_id == record_id)
    ).all()
    return out(partner, event_ids=sorted(event_ids))


@router.get("/attendees")
def list_attendees(
    event_id: int | None = None,
    q: str | None = None,
    archived: bool | None = None,
    db: DBSession = Depends(get_db),
    _: User = Depends(require(Role.admin, "read attendees")),
) -> list[Json]:
    query = select(Attendee).order_by(col(Attendee.id))
    if event_id is not None:
        query = query.where(Attendee.event_id == event_id)
    if archived is not None:
        query = query.where(Attendee.archived == archived)
    rows = db.exec(query).all()
    if q:
        rows = [a for a in rows if _matches(q, a.first_name, a.last_name, a.email, a.company)]
    return [out(a) for a in rows]


@router.get("/attendees/{record_id}")
def get_attendee(
    record_id: int,
    db: DBSession = Depends(get_db),
    _: User = Depends(require(Role.admin, "read attendees")),
) -> Json:
    return out(fetch(db, Attendee, record_id))


@router.get("/search")
def search(
    q: str = Query(min_length=1),
    limit: int = Query(default=25, ge=1, le=100),
    db: DBSession = Depends(get_db),
    user: User = Depends(current_user),
) -> list[Json]:
    """Text search over public fields. Notes and settings are never searched;
    attendees are searched only for admins."""
    hits: list[Json] = []

    def add(entity: str, row: Record, label: str, *fields: str) -> None:
        if _matches(q, label, *fields):
            hits.append({"entity": entity, "id": row.id, "label": label, "archived": row.archived})

    for e in db.exec(select(Edition)).all():
        add("editions", e, e.name)
    for ev in db.exec(select(Event)).all():
        add("events", ev, ev.name, ev.description, ev.venue)
    for s in db.exec(select(Session)).all():
        add("sessions", s, s.title)
    for sp in db.exec(select(Speaker)).all():
        add("speakers", sp, f"{sp.first_name} {sp.last_name}", sp.email, sp.company)
    for p in db.exec(select(Partner)).all():
        add("partners", p, p.name, p.contact_email)
    if user.role is Role.admin:
        for a in db.exec(select(Attendee)).all():
            add("attendees", a, f"{a.first_name} {a.last_name}", a.email, a.company)
    return hits[:limit]


def _matches(q: str, *fields: str) -> bool:
    needle = q.casefold()
    return any(needle in f.casefold() for f in fields)


# ---------------------------------------------------------------- creates


@router.post("/editions", status_code=status.HTTP_201_CREATED)
def create_edition(
    body: EditionCreate,
    db: DBSession = Depends(get_db),
    user: User = Depends(require(Role.admin, "create editions")),
) -> Json:
    if db.exec(select(Edition).where(Edition.year == body.year)).first() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"edition {body.year} already exists")
    return out(save(db, Edition(**body.model_dump(), **stamps(user))))


@router.post("/events", status_code=status.HTTP_201_CREATED)
def create_event(
    body: EventCreate,
    db: DBSession = Depends(get_db),
    user: User = Depends(require(Role.editor, "create events")),
) -> Json:
    require_draft(user, active_parent(db, Edition, body.edition_id), "create events")
    return out_event(save(db, Event(**body.model_dump(), **stamps(user))), user)


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
def create_session(
    body: SessionCreate,
    db: DBSession = Depends(get_db),
    user: User = Depends(require(Role.editor, "create sessions")),
) -> Json:
    require_draft(user, edition_of(db, active_parent(db, Event, body.event_id)), "create sessions")
    return out(save(db, Session(**body.model_dump(), **stamps(user))))


@router.post("/speakers", status_code=status.HTTP_201_CREATED)
def create_speaker(
    body: SpeakerCreate,
    db: DBSession = Depends(get_db),
    user: User = Depends(require(Role.editor, "create speakers")),
) -> Json:
    return out(save(db, Speaker(**body.model_dump(), **stamps(user))))


@router.post("/partners", status_code=status.HTTP_201_CREATED)
def create_partner(
    body: PartnerCreate,
    db: DBSession = Depends(get_db),
    user: User = Depends(require(Role.editor, "create partners")),
) -> Json:
    return out(save(db, Partner(**body.model_dump(), **stamps(user))))


@router.post("/attendees", status_code=status.HTTP_201_CREATED)
def create_attendee(
    body: AttendeeCreate,
    db: DBSession = Depends(get_db),
    user: User = Depends(require(Role.admin, "create attendees")),
) -> Json:
    active_parent(db, Event, body.event_id)
    return out(save(db, Attendee(**body.model_dump(), **stamps(user))))


@router.post("/sessions/{record_id}/speakers", status_code=status.HTTP_201_CREATED)
def link_speaker(
    record_id: int,
    body: SpeakerLink,
    db: DBSession = Depends(get_db),
    user: User = Depends(require(Role.editor, "link speakers")),
) -> Json:
    require_draft(user, edition_of(db, active_parent(db, Session, record_id)), "link speakers")
    fetch(db, Speaker, body.speaker_id)
    if db.get(SessionSpeaker, (record_id, body.speaker_id)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "speaker already linked to this session")
    link = SessionSpeaker(session_id=record_id, speaker_id=body.speaker_id, created_at=now())
    return out(save(db, link))


@router.post("/events/{record_id}/partners", status_code=status.HTTP_201_CREATED)
def link_partner(
    record_id: int,
    body: PartnerLink,
    db: DBSession = Depends(get_db),
    user: User = Depends(require(Role.editor, "link partners")),
) -> Json:
    require_draft(user, edition_of(db, active_parent(db, Event, record_id)), "link partners")
    fetch(db, Partner, body.partner_id)
    if db.get(EventPartner, (record_id, body.partner_id)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "partner already linked to this event")
    link = EventPartner(event_id=record_id, partner_id=body.partner_id, created_at=now())
    return out(save(db, link))


# ---------------------------------------------------------------- update / archive


@router.patch("/{entity}/{record_id}")
def update_record(
    entity: EntityName,
    record_id: int,
    fields: Json = Body(),
    db: DBSession = Depends(get_db),
    user: User = Depends(current_user),
) -> Json:
    ensure(user, WRITE_ROLE[entity], f"update {entity.value}")
    try:
        changes = UPDATES[entity].model_validate(fields).model_dump(exclude_unset=True)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc
    if not changes:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "no fields to update")
    if any(v is None for v in changes.values()):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "fields cannot be set to null")
    row = fetch(db, ENTITIES[entity], record_id)
    if entity in EDITION_SCOPED:
        require_draft(user, edition_of(db, row), f"update {entity.value}")
    if "edition_id" in changes:
        require_draft(user, active_parent(db, Edition, changes["edition_id"]), "move events")
    if isinstance(row, StatusRecord) and row.archived and "status" in changes:
        raise HTTPException(status.HTTP_409_CONFLICT, "unarchive the record before changing status")
    for name, value in changes.items():
        setattr(row, name, value)
    row.updated_at = now()
    saved = save(db, row)
    return out_event(saved, user) if isinstance(saved, Event) else out(saved)


def _set_archived(
    entity: EntityName, record_id: int, archived: bool, db: DBSession, user: User
) -> Json:
    verb = "archive" if archived else "unarchive"
    ensure(user, ARCHIVE_ROLE[entity], f"{verb} {entity.value}")
    row = fetch(db, ENTITIES[entity], record_id)
    if row.archived == archived:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"{entity.value} {record_id} is already {verb}d"
        )
    row.archived = archived
    row.archived_at = now() if archived else None
    if isinstance(row, StatusRecord):
        if archived:
            row.previous_status, row.status = row.status, Status.archived
        else:
            row.status, row.previous_status = row.previous_status or Status.draft, None
    row.updated_at = now()
    saved = save(db, row)
    return out_event(saved, user) if isinstance(saved, Event) else out(saved)


@router.post("/{entity}/{record_id}/archive")
def archive_record(
    entity: EntityName,
    record_id: int,
    db: DBSession = Depends(get_db),
    user: User = Depends(current_user),
) -> Json:
    return _set_archived(entity, record_id, True, db, user)


@router.post("/{entity}/{record_id}/unarchive")
def unarchive_record(
    entity: EntityName,
    record_id: int,
    db: DBSession = Depends(get_db),
    user: User = Depends(current_user),
) -> Json:
    return _set_archived(entity, record_id, False, db, user)


# ---------------------------------------------------------------- notifications


@router.post("/notifications", status_code=status.HTTP_201_CREATED)
def send_notification(
    body: Notification,
    db: DBSession = Depends(get_db),
    user: User = Depends(require(Role.editor, "send notifications")),
) -> Json:
    """Stored in the outbox; nothing leaves EventSim (FR-SIM-08)."""
    message = Outbox(sender_id=user.id or 0, **body.model_dump(), created_at=now())
    saved = save(db, message)
    return {"id": saved.id, "status": "queued"}


@router.get("/outbox")
def read_outbox(
    db: DBSession = Depends(get_db),
    _: User = Depends(require(Role.admin, "read the outbox")),
) -> list[Json]:
    return [out(m) for m in db.exec(select(Outbox).order_by(col(Outbox.id))).all()]
