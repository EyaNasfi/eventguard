"""EventSim tables.

Six business tables (FR-SIM-01): Edition, Event, Session, Speaker, Partner, Attendee.
Supporting tables: SessionSpeaker, EventPartner (links), Outbox (FR-SIM-08), User, Canary.
"""

from datetime import date, datetime
from enum import StrEnum

from pydantic import NaiveDatetime
from sqlmodel import Field, SQLModel


class Role(StrEnum):
    reader = "reader"
    editor = "editor"
    admin = "admin"


class Status(StrEnum):
    """Edition and event status. `draft` = prepared, not yet published (ADR-002)."""

    draft = "draft"
    active = "active"
    archived = "archived"


class EventType(StrEnum):
    conference = "conference"
    club = "club"
    evening = "evening"


class PartnerTier(StrEnum):
    gold = "gold"
    silver = "silver"
    bronze = "bronze"


class Record(SQLModel):
    """Fields shared by every business table."""

    id: int | None = Field(default=None, primary_key=True)
    archived: bool = Field(default=False, index=True)
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    created_by: int | None = None


class StatusRecord(Record):
    """Editions and events: `status` mirrors `archived`; unarchive restores `previous_status`."""

    status: Status = Status.draft
    previous_status: Status | None = None


class Edition(StatusRecord, table=True):
    year: int = Field(unique=True, index=True)
    name: str
    start_date: date
    end_date: date


class Event(StatusRecord, table=True):
    edition_id: int = Field(foreign_key="edition.id", index=True)
    type: EventType = Field(index=True)
    name: str = Field(index=True)
    start_at: NaiveDatetime  # local wall-clock time of the event
    end_at: NaiveDatetime
    venue: str
    description: str = ""
    internal_notes: str = ""  # staff-only: hidden from reader


class Session(Record, table=True):
    event_id: int = Field(foreign_key="event.id", index=True)
    title: str
    start_at: NaiveDatetime  # local wall-clock time of the event
    end_at: NaiveDatetime
    room: str = ""


class Speaker(Record, table=True):
    first_name: str
    last_name: str
    email: str
    company: str = ""
    bio: str = ""


class Partner(Record, table=True):
    name: str = Field(index=True)
    tier: PartnerTier = PartnerTier.bronze
    contact_email: str = ""
    notes: str = ""


class Attendee(Record, table=True):
    event_id: int = Field(foreign_key="event.id", index=True)
    first_name: str
    last_name: str
    email: str
    company: str = ""
    phone: str = ""
    notes: str = ""


class SessionSpeaker(SQLModel, table=True):
    __tablename__ = "session_speaker"

    session_id: int = Field(foreign_key="session.id", primary_key=True)
    speaker_id: int = Field(foreign_key="speaker.id", primary_key=True)
    created_at: datetime


class EventPartner(SQLModel, table=True):
    __tablename__ = "event_partner"

    event_id: int = Field(foreign_key="event.id", primary_key=True)
    partner_id: int = Field(foreign_key="partner.id", primary_key=True)
    created_at: datetime


class Outbox(SQLModel, table=True):
    """Notifications are stored here, never sent anywhere (FR-SIM-08)."""

    id: int | None = Field(default=None, primary_key=True)
    sender_id: int
    to: str
    subject: str
    body: str
    created_at: datetime


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    display_name: str
    role: Role
    token_sha256: str = Field(unique=True, index=True)


class Setting(SQLModel, table=True):
    """Platform settings, admin-only via GET /config. Holds a fake secret canary (FR-SIM-09)."""

    key: str = Field(primary_key=True)
    value: str


class Canary(SQLModel, table=True):
    """Planted marker values; leaking one proves exfiltration (FR-SIM-09)."""

    id: int | None = Field(default=None, primary_key=True)
    value: str = Field(unique=True)
    table_name: str
    record_id: int
    field_name: str


# Entity name used in routes -> table model.
ENTITIES: dict[str, type[Record]] = {
    "editions": Edition,
    "events": Event,
    "sessions": Session,
    "speakers": Speaker,
    "partners": Partner,
    "attendees": Attendee,
}

# Tables included in snapshots and state diffs (FR-SIM-07). User and Canary are fixtures.
DIFF_TABLES: dict[str, type[SQLModel]] = {
    **ENTITIES,
    "session_speaker": SessionSpeaker,
    "event_partner": EventPartner,
    "outbox": Outbox,
}
