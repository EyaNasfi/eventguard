"""Task schema (S2-06, FR-EVAL-01, D4). One YAML file per task in bench/tasks/."""

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

TASKS_DIR = Path(__file__).resolve().parent / "tasks"
Category = Literal["procedure", "read", "duplicate", "archive"]
Role = Literal["reader", "editor", "admin"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Expected(Strict):
    reply_must_contain: list[list[str]] = Field(
        default_factory=list,
        description="Groups of alternatives: each group must match at least one alternative.",
    )
    cited_sheet: list[str] = Field(default_factory=list, description="Any of these PROC ids.")
    state: str = Field(description="What the state diff must look like, in words.")


class Task(Strict):
    id: str = Field(pattern=r"^(PRC|RD|DUP|ARC)-\d{2}$")
    category: Category
    role: Role
    seed: int = 42
    prompt: str = Field(min_length=5)
    expected: Expected
    checker: str
    checker_params: dict[str, Any] = Field(default_factory=dict)
    version: int = 1
    notes: str = ""


def load_task(path: Path) -> Task:
    return Task.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def load_tasks(directory: Path = TASKS_DIR) -> list[Task]:
    return [load_task(p) for p in sorted(directory.glob("*.yaml"))]
