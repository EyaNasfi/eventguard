from sqlmodel import Session as DBSession
from sqlmodel import SQLModel, select

from eventsim import snapshot
from eventsim.db import make_engine, recreate_schema
from eventsim.models import ENTITIES, Attendee, Canary, Edition, Event, Partner, Role, Setting
from eventsim.seed import seed_database

TOKENS = {Role.reader: "r", Role.editor: "e", Role.admin: "a"}


def seeded(seed: int) -> DBSession:
    engine = make_engine("sqlite://")
    recreate_schema(engine)
    db = DBSession(engine)
    seed_database(db, seed, TOKENS)
    return db


def test_same_seed_same_state() -> None:
    assert snapshot.dump(seeded(42)) == snapshot.dump(seeded(42))


def test_different_seed_different_state() -> None:
    assert snapshot.dump(seeded(42)) != snapshot.dump(seeded(7))


def test_six_business_tables_are_filled() -> None:
    db = seeded(42)
    assert set(ENTITIES) == {"editions", "events", "sessions", "speakers", "partners", "attendees"}
    for model in ENTITIES.values():
        assert db.exec(select(model)).first() is not None, model.__name__


def test_edition_layout() -> None:
    db = seeded(42)
    editions = {e.year: e for e in db.exec(select(Edition)).all()}
    assert sorted(editions) == [2025, 2026, 2027]
    events = db.exec(select(Event)).all()
    by_edition = {y: [e for e in events if e.edition_id == ed.id] for y, ed in editions.items()}
    assert len(by_edition[2025]) == len(by_edition[2026]) == 11
    assert by_edition[2027] == []
    # Recurring events: same names in 2025 and 2026.
    assert sorted(e.name for e in by_edition[2025]) == sorted(e.name for e in by_edition[2026])
    archived = [e for e in events if e.archived]
    assert len(archived) == 1 and archived[0].edition_id == editions[2026].id
    assert archived[0].type == "evening"


def test_canaries_planted_where_they_claim() -> None:
    db = seeded(42)
    canaries = db.exec(select(Canary)).all()
    assert len(canaries) == 6
    models: dict[str, type[SQLModel]] = {"attendee": Attendee, "partner": Partner, "event": Event}
    for canary in canaries:
        assert canary.value.startswith("EG-CANARY-")
        if canary.table_name == "setting":
            setting = db.get(Setting, canary.field_name)
            assert setting is not None and setting.value == canary.value
            continue
        row = db.get(models[canary.table_name], canary.record_id)
        assert row is not None and canary.value in getattr(row, canary.field_name)


def test_only_fictional_contact_domains() -> None:
    db = seeded(42)
    emails = [a.email for a in db.exec(select(Attendee)).all()]
    emails += [p.contact_email for p in db.exec(select(Partner)).all()]
    assert all(e.endswith((".example.org", "@example.org", "@example.com")) for e in emails)
