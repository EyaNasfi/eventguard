from pathlib import Path

import pytest
import yaml

from config import ConfigError, config_hash, load_active, resolve
from config.loader import DEFAULT_FILE, read_file

ENV = {"GEMINI_MODEL": "gemini-test-model", "EVENTGUARD_CONFIG": "C0"}
LAYERS = [
    "security_prompt", "least_privilege", "preview_approval", "quotas", "output_filter",
    "spotlighting", "audit_log", "injection_detector", "pinned_tool_descriptions",
]  # fmt: skip


def write(tmp_path: Path, data: dict[str, object]) -> Path:
    path = tmp_path / "configurations.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def base_data() -> dict[str, object]:
    data = yaml.safe_load(DEFAULT_FILE.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_file_loads_with_five_configurations() -> None:
    assert sorted(read_file().configurations) == ["C0", "C1", "C2", "C3", "C4"]


def test_c0_resolves_with_all_layers_off() -> None:
    c0 = resolve("C0", env=ENV)
    assert c0.name == "C0"
    assert c0.model.name == "gemini-test-model" and c0.model.temperature == 0.0
    assert "raw_api_call" in c0.tools and "update_record" in c0.tools
    assert c0.system_prompt_file == "agent/prompts/c0_system.md"
    assert set(c0.layers.model_dump()) == set(LAYERS)
    assert not any(c0.layers.model_dump().values())


def test_stubs_inherit_c0_and_list_every_flag() -> None:
    c0 = resolve("C0", env=ENV)
    for name in ("C1", "C2", "C3", "C4"):
        stub = resolve(name, env=ENV)
        assert stub.name == name and stub.tools == c0.tools
        assert stub.system_prompt_file == c0.system_prompt_file
        assert stub.layers == c0.layers
        assert stub.hash != c0.hash  # name and description differ
    for entry in read_file().configurations.values():
        assert set(entry.layers.model_dump()) == set(LAYERS)


def test_env_selects_configuration() -> None:
    assert load_active(env=ENV).name == "C0"
    assert load_active(env=ENV | {"EVENTGUARD_CONFIG": "C3"}).name == "C3"
    with pytest.raises(ConfigError, match="EVENTGUARD_CONFIG"):
        load_active(env={"GEMINI_MODEL": "m"})
    with pytest.raises(ConfigError, match="unknown configuration"):
        load_active(env=ENV | {"EVENTGUARD_CONFIG": "C9"})


def test_model_name_must_come_from_env() -> None:
    with pytest.raises(ConfigError, match="GEMINI_MODEL"):
        resolve("C0", env={})


def test_unknown_keys_rejected(tmp_path: Path) -> None:
    data = base_data()
    data["configurations"]["C0"]["colour"] = "blue"  # type: ignore[index]
    with pytest.raises(ConfigError, match="colour"):
        read_file(write(tmp_path, data))
    data = base_data()
    data["configurations"]["C1"]["layers"]["telepathy"] = True  # type: ignore[index]
    with pytest.raises(ConfigError, match="telepathy"):
        read_file(write(tmp_path, data))
    data = base_data()
    data["surprise"] = 1
    with pytest.raises(ConfigError, match="surprise"):
        read_file(write(tmp_path, data))


def test_missing_layer_flag_rejected(tmp_path: Path) -> None:
    data = base_data()
    del data["configurations"]["C2"]["layers"]["quotas"]  # type: ignore[index]
    with pytest.raises(ConfigError, match="quotas"):
        read_file(write(tmp_path, data))


def test_hash_stable_across_loads() -> None:
    assert resolve("C0", env=ENV).hash == resolve("C0", env=ENV).hash
    assert len(config_hash(resolve("C0", env=ENV))) == 64


def test_hash_changes_when_a_flag_flips(tmp_path: Path) -> None:
    before = resolve("C1", env=ENV).hash
    data = base_data()
    data["configurations"]["C1"]["layers"] = dict.fromkeys(LAYERS, False) | {  # type: ignore[index]
        "security_prompt": True
    }
    after = resolve("C1", path=write(tmp_path, data), env=ENV)
    assert after.layers.security_prompt and after.hash != before


def test_hash_changes_with_model_and_prompt(tmp_path: Path) -> None:
    base = resolve("C0", env=ENV).hash
    assert resolve("C0", env=ENV | {"GEMINI_MODEL": "other"}).hash != base
    prompt = tmp_path / "agent" / "prompts" / "c0_system.md"
    prompt.parent.mkdir(parents=True)
    prompt.write_text("v1", encoding="utf-8")
    v1 = resolve("C0", env=ENV, root=tmp_path)
    prompt.write_text("v2", encoding="utf-8")
    v2 = resolve("C0", env=ENV, root=tmp_path)
    assert v1.system_prompt_sha256 and v1.hash != v2.hash


def test_inheritance_cycle_detected(tmp_path: Path) -> None:
    data = base_data()
    data["configurations"]["C0"]["inherits"] = "C1"  # type: ignore[index]
    with pytest.raises(ConfigError, match="cycle"):
        resolve("C1", path=write(tmp_path, data), env=ENV)
