"""Snapshot and state diff (FR-SIM-07).

A dump is {table: {row_key: row_as_json}}. The diff lists, per table, the rows
added, removed and changed (with before/after values of the changed fields only).
"""

from typing import Any

from sqlmodel import Session as DBSession
from sqlmodel import SQLModel, select

from eventsim.models import DIFF_TABLES

Row = dict[str, Any]
Dump = dict[str, dict[str, Row]]


def _key(row: SQLModel) -> str:
    keys = [str(getattr(row, col.name)) for col in row.__table__.primary_key.columns]  # type: ignore[attr-defined]
    return ":".join(keys)


def dump(db: DBSession) -> Dump:
    return {
        name: {_key(row): row.model_dump(mode="json") for row in db.exec(select(model)).all()}
        for name, model in DIFF_TABLES.items()
    }


def diff(before: Dump, after: Dump) -> dict[str, dict[str, list[Row]]]:
    result: dict[str, dict[str, list[Row]]] = {}
    for table in DIFF_TABLES:
        old, new = before.get(table, {}), after.get(table, {})
        changed = []
        for key in sorted(old.keys() & new.keys(), key=_sort_key):
            fields = {
                f for f in old[key].keys() | new[key].keys() if old[key].get(f) != new[key].get(f)
            }
            if fields:
                changed.append(
                    {
                        "key": key,
                        "fields": sorted(fields),
                        "before": {f: old[key].get(f) for f in sorted(fields)},
                        "after": {f: new[key].get(f) for f in sorted(fields)},
                    }
                )
        result[table] = {
            "added": [new[k] for k in sorted(new.keys() - old.keys(), key=_sort_key)],
            "removed": [old[k] for k in sorted(old.keys() - new.keys(), key=_sort_key)],
            "changed": changed,
        }
    return result


def is_empty(state_diff: dict[str, dict[str, list[Row]]]) -> bool:
    return all(not rows for table in state_diff.values() for rows in table.values())


def _sort_key(key: str) -> tuple[int, ...]:
    return tuple(int(part) for part in key.split(":"))
