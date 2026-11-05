"""Load, validate and hash a configuration.

The resolved configuration is what a run actually used: the entry after inheritance,
the model settings with the model name read from the environment, and the SHA-256 of
the system prompt file. Its hash (NFR-02) is recorded with every run and tool call.
"""

import hashlib
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FILE = ROOT / "config" / "configurations.yaml"
SELECTOR_ENV = "EVENTGUARD_CONFIG"


class ConfigError(Exception):
    """The configuration file or the environment is invalid."""


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Layers(Strict):
    security_prompt: bool
    least_privilege: bool
    preview_approval: bool
    quotas: bool
    output_filter: bool
    spotlighting: bool
    audit_log: bool
    injection_detector: bool
    pinned_tool_descriptions: bool


class ModelBlock(Strict):
    name_env: str
    temperature: float = Field(ge=0.0, le=2.0)
    max_output_tokens: int = Field(gt=0)


class Entry(Strict):
    """One entry as written in the file; fields may come from the parent."""

    inherits: str | None = None
    name: str
    description: str
    layers: Layers
    system_prompt_file: str | None = None
    tools: list[str] | None = None


class ConfigFile(Strict):
    model: ModelBlock
    configurations: dict[str, Entry]


class ModelSettings(Strict):
    name: str
    temperature: float
    max_output_tokens: int


class ResolvedConfig(Strict):
    name: str
    description: str
    tools: list[str]
    system_prompt_file: str
    system_prompt_sha256: str | None
    layers: Layers
    model: ModelSettings

    @property
    def hash(self) -> str:
        return config_hash(self)


def config_hash(config: ResolvedConfig) -> str:
    canonical = json.dumps(config.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def read_file(path: Path = DEFAULT_FILE) -> ConfigFile:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        return ConfigFile.model_validate(raw)
    except (OSError, yaml.YAMLError, ValidationError) as exc:
        raise ConfigError(f"invalid configuration file {path}: {exc}") from exc


def resolve(
    name: str,
    path: Path = DEFAULT_FILE,
    env: Mapping[str, str] | None = None,
    root: Path = ROOT,
) -> ResolvedConfig:
    env = os.environ if env is None else env
    file = read_file(path)
    entry = _flatten(file.configurations, name, seen=())

    model_name = env.get(file.model.name_env, "").strip()
    if not model_name:
        raise ConfigError(f"environment variable {file.model.name_env} is not set")

    prompt_path = root / entry["system_prompt_file"]
    prompt_hash = (
        hashlib.sha256(prompt_path.read_bytes()).hexdigest() if prompt_path.is_file() else None
    )
    try:
        return ResolvedConfig(
            name=entry["name"],
            description=entry["description"],
            tools=entry["tools"],
            system_prompt_file=entry["system_prompt_file"],
            system_prompt_sha256=prompt_hash,
            layers=entry["layers"],
            model=ModelSettings(
                name=model_name,
                temperature=file.model.temperature,
                max_output_tokens=file.model.max_output_tokens,
            ),
        )
    except (KeyError, ValidationError) as exc:
        raise ConfigError(f"configuration {name} is incomplete: {exc}") from exc


def load_active(
    path: Path = DEFAULT_FILE, env: Mapping[str, str] | None = None, root: Path = ROOT
) -> ResolvedConfig:
    """Resolve the configuration named by EVENTGUARD_CONFIG. No silent default."""
    env = os.environ if env is None else env
    name = env.get(SELECTOR_ENV, "").strip()
    if not name:
        raise ConfigError(f"{SELECTOR_ENV} is not set (expected one of C0..C4)")
    return resolve(name, path, env, root)


def _flatten(entries: dict[str, Entry], name: str, seen: tuple[str, ...]) -> dict[str, Any]:
    if name not in entries:
        raise ConfigError(f"unknown configuration {name!r}; known: {sorted(entries)}")
    if name in seen:
        raise ConfigError(f"inheritance cycle: {' -> '.join((*seen, name))}")
    entry = entries[name]
    own = entry.model_dump(exclude_none=True, exclude={"inherits"})
    if entry.inherits is None:
        return own
    return _flatten(entries, entry.inherits, (*seen, name)) | own
