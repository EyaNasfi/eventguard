"""Request bodies. Unknown fields are rejected (422) on every write route."""

from datetime import date
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, NaiveDatetime, model_validator

from eventsim.models import EventType, PartnerTier, Status


def _not_archived(value: Status) -> Status:
    if value is Status.archived:
        raise ValueError("use the archive route to archive a record")
    return value


# Status a client may set directly: draft or active. `archived` only via POST .../archive.
LiveStatus = Annotated[Status, AfterValidator(_not_archived)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EditionCreate(Strict):
    year: int = Field(ge=2000, le=2100)
    name: str = Field(min_length=1)
    status: LiveStatus = Status.draft
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def _dates(self) -> "EditionCreate":
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        return self


class EventCreate(Strict):
    edition_id: int
    type: EventType
    name: str = Field(min_length=1)
    status: LiveStatus = Status.draft
    start_at: NaiveDatetime
    end_at: NaiveDatetime
    venue: str
    description: str = ""
    internal_notes: str = ""

    @model_validator(mode="after")
    def _dates(self) -> "EventCreate":
        if self.end_at < self.start_at:
            raise ValueError("end_at must not be before start_at")
        return self


class SessionCreate(Strict):
    event_id: int
    title: str = Field(min_length=1)
    start_at: NaiveDatetime
    end_at: NaiveDatetime
    room: str = ""


class SpeakerCreate(Strict):
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    email: str
    company: str = ""
    bio: str = ""


class PartnerCreate(Strict):
    name: str = Field(min_length=1)
    tier: PartnerTier = PartnerTier.bronze
    contact_email: str = ""
    notes: str = ""


class AttendeeCreate(Strict):
    event_id: int
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    email: str
    company: str = ""
    phone: str = ""
    notes: str = ""


class EditionUpdate(Strict):
    name: str | None = None
    status: LiveStatus | None = None
    start_date: date | None = None
    end_date: date | None = None


class EventUpdate(Strict):
    edition_id: int | None = None
    name: str | None = None
    status: LiveStatus | None = None
    start_at: NaiveDatetime | None = None
    end_at: NaiveDatetime | None = None
    venue: str | None = None
    description: str | None = None
    internal_notes: str | None = None


class SessionUpdate(Strict):
    title: str | None = None
    start_at: NaiveDatetime | None = None
    end_at: NaiveDatetime | None = None
    room: str | None = None


class SpeakerUpdate(Strict):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    company: str | None = None
    bio: str | None = None


class PartnerUpdate(Strict):
    name: str | None = None
    tier: PartnerTier | None = None
    contact_email: str | None = None
    notes: str | None = None


class AttendeeUpdate(Strict):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    company: str | None = None
    phone: str | None = None
    notes: str | None = None


UPDATES: dict[str, type[Strict]] = {
    "editions": EditionUpdate,
    "events": EventUpdate,
    "sessions": SessionUpdate,
    "speakers": SpeakerUpdate,
    "partners": PartnerUpdate,
    "attendees": AttendeeUpdate,
}


class SpeakerLink(Strict):
    speaker_id: int


class PartnerLink(Strict):
    partner_id: int


class Notification(Strict):
    to: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    body: str


class ResetRequest(Strict):
    seed: int
