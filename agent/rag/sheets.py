"""Load procedure sheets (Markdown + YAML front matter) and split them into one chunk per
section. Chunk ids are stable (`PROC-03#steps`), which makes ingestion idempotent."""

import re
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[2]
SHEETS_DIR = ROOT / "procedures"
SECTIONS = ("Purpose", "Who can do this", "Steps", "Checks before and after", "Common mistakes")


class SheetMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^PROC-\d{2}$")
    title: str
    roles: list[str]
    tags: list[str]
    version: int


@dataclass(frozen=True)
class Sheet:
    meta: SheetMeta
    sections: dict[str, str]  # section name -> text
    words: int


@dataclass(frozen=True)
class Chunk:
    id: str
    sheet_id: str
    title: str
    section: str
    text: str


def parse_sheet(text: str) -> Sheet:
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text.replace("\r\n", "\n"), re.S)
    if not match:
        raise ValueError("missing YAML front matter")
    meta = SheetMeta.model_validate(yaml.safe_load(match.group(1)))
    body = match.group(2)
    sections: dict[str, str] = {}
    for part in re.split(r"^## ", body, flags=re.M)[1:]:
        heading, _, content = part.partition("\n")
        sections[heading.strip()] = content.strip()
    return Sheet(meta=meta, sections=sections, words=len(body.split()))


def load_sheets(directory: Path = SHEETS_DIR) -> list[Sheet]:
    return [parse_sheet(p.read_text(encoding="utf-8")) for p in sorted(directory.glob("PROC-*.md"))]


def slug(section: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", section.lower()).strip("-")


def chunks(sheets: list[Sheet]) -> list[Chunk]:
    out = []
    for sheet in sheets:
        for section, text in sheet.sections.items():
            out.append(
                Chunk(
                    id=f"{sheet.meta.id}#{slug(section)}",
                    sheet_id=sheet.meta.id,
                    title=sheet.meta.title,
                    section=section,
                    text=text,
                )
            )
    return out
