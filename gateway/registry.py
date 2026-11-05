"""Tool registry: one place that holds every tool's name, description, input schema and handler.

Descriptions and schemas are plain data so they can be hashed and pinned later (SR-10).
"""

import hashlib
import json
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from typing import Any

from gateway.pipeline import ToolCall, ToolResult
from gateway.platform import PlatformClient

ToolHandler = Callable[[PlatformClient, ToolCall], Awaitable[ToolResult]]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: ToolHandler
    read_only: bool = False

    def public(self) -> dict[str, Any]:
        """The part the model sees (and that SR-10 will pin)."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


class Registry:
    def __init__(self, specs: Iterable[ToolSpec]) -> None:
        self._specs: dict[str, ToolSpec] = {}
        for spec in specs:
            if spec.name in self._specs:
                raise ValueError(f"duplicate tool name: {spec.name}")
            self._specs[spec.name] = spec

    def __contains__(self, name: object) -> bool:
        return name in self._specs

    def get(self, name: str) -> ToolSpec | None:
        return self._specs.get(name)

    def names(self) -> list[str]:
        return list(self._specs)

    def select(self, allowed: Iterable[str]) -> "Registry":
        """Sub-registry with exactly the configuration's allow-list, in that order."""
        allowed = list(allowed)
        unknown = [name for name in allowed if name not in self._specs]
        if unknown:
            raise ValueError(f"configuration lists unknown tool(s): {', '.join(unknown)}")
        return Registry(self._specs[name] for name in allowed)

    def descriptions_hash(self) -> str:
        canonical = json.dumps(
            [spec.public() for spec in self._specs.values()],
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode()).hexdigest()
