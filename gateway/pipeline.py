"""Layer pipeline around every tool call.

Each security layer of C1-C4 becomes one `Layer` inserted here. In C0 every flag is off, so the
pipeline is empty and calls pass straight through. A flag that is on but has no implementation
yet stops the gateway at start-up: a configuration must never silently run without a layer it
claims to have.
"""

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from config.loader import Layers
from eventsim.models import Role

Outcome = Literal["ok", "error", "refused"]


@dataclass
class ToolCall:
    tool: str
    arguments: dict[str, Any]
    role: Role
    config_name: str
    config_hash: str
    started: float = field(default_factory=time.perf_counter)


@dataclass
class ToolResult:
    outcome: Outcome
    data: Any = None
    message: str | None = None
    http_status: int | None = None


class Layer(Protocol):
    name: str

    async def before_call(self, call: ToolCall) -> ToolResult | None:
        """Return a result to stop the call here (e.g. refused), or None to continue."""
        ...

    async def after_call(self, call: ToolCall, result: ToolResult) -> ToolResult: ...


Handler = Callable[[ToolCall], Awaitable[ToolResult]]

# Layer flag -> implementation. Filled in by the sprint that builds each layer.
IMPLEMENTED: dict[str, Callable[[], Layer]] = {}


class Pipeline:
    def __init__(self, layers: list[Layer]) -> None:
        self.layers = layers

    async def run(self, call: ToolCall, handler: Handler) -> ToolResult:
        for layer in self.layers:
            stopped = await layer.before_call(call)
            if stopped is not None:
                return await self._after(call, stopped)
        return await self._after(call, await handler(call))

    async def _after(self, call: ToolCall, result: ToolResult) -> ToolResult:
        for layer in reversed(self.layers):
            result = await layer.after_call(call, result)
        return result


def build_pipeline(layers: Layers) -> Pipeline:
    wanted = [name for name, on in layers.model_dump().items() if on]
    missing = [name for name in wanted if name not in IMPLEMENTED]
    if missing:
        raise RuntimeError(f"layer(s) switched on but not implemented yet: {', '.join(missing)}")
    return Pipeline([IMPLEMENTED[name]() for name in wanted])
