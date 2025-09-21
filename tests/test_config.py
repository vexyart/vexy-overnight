#!/usr/bin/env python3
# this_file: tests/test_config.py
"""Tests for safe configuration editing in ConfigManager."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import tomli

from vexy_overnight.config import ConfigManager


@pytest.fixture()
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provide an isolated HOME directory for configuration tests."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


def _write_toml(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _read_toml(path: Path) -> dict:
    return tomli.loads(path.read_text())


def test_enable_claude_hook_when_write_fails_then_original_restored(
    fake_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Enable should restore original settings when writing fails."""
    settings_path = fake_home / ".claude" / "settings.json"
    original = {"hooks": {"Stop": []}}
    _write_json(settings_path, original)

    manager = ConfigManager()

    def boom(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("boom")

    monkeypatch.setattr(json, "dump", boom)

    with pytest.raises(RuntimeError):
        manager.enable_claude_hook()

    assert _read_json(settings_path) == original, (
        "Claude config must be restored from backup on failure"
    )


def test_enable_claude_hook_when_validation_fails_then_original_restored(
    fake_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Validation errors must roll back Claude settings."""
    settings_path = fake_home / ".claude" / "settings.json"
    original = {"hooks": {"Stop": []}}
    _write_json(settings_path, original)

    manager = ConfigManager()

    def fail_validation(self: ConfigManager, path: Path) -> None:  # noqa: ARG001
        raise ValueError("invalid")

    monkeypatch.setattr(ConfigManager, "_validate_json_file", fail_validation, raising=False)

    with pytest.raises(ValueError):
        manager.enable_claude_hook()

    assert _read_json(settings_path) == original, (
        "Claude config must roll back when validation fails"
    )


def test_enable_claude_hook_when_called_then_sets_stop_hook(fake_home: Path) -> None:
    """Successful enable should write vocl-go command and produce valid JSON."""
    settings_path = fake_home / ".claude" / "settings.json"
    _write_json(settings_path, {})

    manager = ConfigManager()
    manager.enable_claude_hook()

    config = _read_json(settings_path)
    hooks = config["hooks"]["Stop"][0]["hooks"][0]
    assert "vocl-go.py" in hooks["command"], "Claude Stop hook must call vocl-go.py"


def test_disable_claude_hook_when_enabled_then_removes_stop(fake_home: Path) -> None:
    """Disable should remove Stop hook entries."""
    settings_path = fake_home / ".claude" / "settings.json"
    _write_json(
        settings_path,
        {
            "hooks": {
                "Stop": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": "vocl-go.py",
                            }
                        ]
                    }
                ]
            }
        },
    )

    manager = ConfigManager()
    manager.disable_claude_hook()

    config = _read_json(settings_path)
    assert "Stop" not in config.get("hooks", {}), "Claude Stop hook should be removed when disabled"


def test_enable_codex_hook_when_write_fails_then_original_restored(
    fake_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Enable should restore Codex config when writing fails."""
    config_path = fake_home / ".codex" / "config.toml"
    _write_toml(config_path, "profile = 'gpt4'")

    manager = ConfigManager()

    def boom(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("boom")

    import tomli_w

    monkeypatch.setattr(tomli_w, "dump", boom)

    with pytest.raises(RuntimeError):
        manager.enable_codex_hook()

    assert _read_toml(config_path) == {"profile": "gpt4"}, (
        "Codex config must be restored on failure"
    )


def test_enable_codex_hook_when_validation_fails_then_original_restored(
    fake_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Validation errors must roll back Codex config."""
    config_path = fake_home / ".codex" / "config.toml"
    _write_toml(config_path, "profile = 'gpt4'")

    manager = ConfigManager()

    def fail_validation(self: ConfigManager, path: Path) -> None:  # noqa: ARG001
        raise ValueError("invalid")

    monkeypatch.setattr(ConfigManager, "_validate_toml_file", fail_validation, raising=False)

    with pytest.raises(ValueError):
        manager.enable_codex_hook()

    assert _read_toml(config_path) == {"profile": "gpt4"}, (
        "Codex config must roll back when validation fails"
    )


def test_enable_codex_hook_when_called_then_sets_notify(fake_home: Path) -> None:
    """Successful enable should add voco-go path to notify list."""
    config_path = fake_home / ".codex" / "config.toml"
    _write_toml(config_path, "")

    manager = ConfigManager()
    manager.enable_codex_hook()

    config = _read_toml(config_path)
    assert config["notify"] == [str(fake_home / ".codex" / "voco-go.py")], (
        "Codex notify must reference voco-go"
    )


def test_disable_codex_hook_when_notify_present_then_removed(fake_home: Path) -> None:
    """Disable should remove notify list when hooks were enabled."""
    config_path = fake_home / ".codex" / "config.toml"
    _write_toml(config_path, "notify = ['something']")

    manager = ConfigManager()
    manager.disable_codex_hook()

    config = _read_toml(config_path)
    assert "notify" not in config, "Codex notify key should be removed when disabling hook"


def test_enable_codex_hook_when_existing_config_then_creates_backup(fake_home: Path) -> None:
    """Enabling Codex hook should write a timestamped backup first."""
    config_path = fake_home / ".codex" / "config.toml"
    _write_toml(config_path, "profile = 'gpt4'")

    manager = ConfigManager()
    manager.enable_codex_hook()

    backups = list(config_path.parent.glob("config.toml.backup.*"))
    assert backups, "Enabling Codex hook must produce a backup before editing"
