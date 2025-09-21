#!/usr/bin/env python3
# this_file: tests/test_user_settings.py
"""Tests for user settings persistence and validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import tomli

from vexy_overnight.user_settings import (
    SETTINGS_FILE_NAME,
    CONTINUATION_TOOLS,
    UserSettings,
    load_user_settings,
    save_user_settings,
)


@pytest.fixture()
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provide isolated HOME directory for settings persistence tests."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


def test_user_settings_defaults_when_created_then_expected_mapping() -> None:
    """Default settings should map claude→codex and codex→claude with prompts."""
    defaults = UserSettings.default()

    assert defaults.continuations["claude"].target == "codex"
    assert defaults.continuations["codex"].target == "claude"
    assert not defaults.continuations["gemini"].enabled, "Gemini continuation disabled by default"
    assert "{todo}" in defaults.prompts["claude"], "Default prompt should reference TODO placeholder"
    assert defaults.notifications.enabled is True
    assert defaults.kill_old_sessions is True


def test_user_settings_round_trip_when_saved_then_loaded(fake_home: Path) -> None:
    """Saving and loading should preserve settings content."""
    settings = UserSettings.default()
    settings.notifications.message = "Continuing on {target}"

    save_user_settings(settings)
    loaded = load_user_settings()

    assert loaded.notifications.message == "Continuing on {target}"
    assert loaded.continuations == settings.continuations


def test_user_settings_validate_when_invalid_target_then_error() -> None:
    """Validation should fail if a continuation target is unknown."""
    settings = UserSettings.default()
    settings.continuations["claude"].target = "unknown"

    with pytest.raises(ValueError, match="unknown continuation target"):
        settings.validate()


def test_save_user_settings_when_existing_file_then_backup_created(fake_home: Path) -> None:
    """Saving over existing file should produce timestamped backup."""
    initial = UserSettings.default()
    initial.notifications.message = "first"
    save_user_settings(initial)

    updated = UserSettings.default()
    updated.notifications.message = "second"
    save_user_settings(updated)

    settings_dir = fake_home / ".vexy-overnight"
    backups = list(settings_dir.glob(f"{SETTINGS_FILE_NAME}.backup.*"))
    assert backups, "Saving over existing settings must create backup"
    saved = tomli.loads((settings_dir / SETTINGS_FILE_NAME).read_text())
    assert saved["notifications"]["message"] == "second"


def test_load_user_settings_when_file_missing_then_defaults_written(fake_home: Path) -> None:
    """Loading when file absent should create defaults on disk for future edits."""
    settings_path = fake_home / ".vexy-overnight" / SETTINGS_FILE_NAME
    assert not settings_path.exists()

    loaded = load_user_settings()

    assert loaded == UserSettings.default()
    assert settings_path.exists(), "Loading defaults should persist settings file"


@pytest.mark.parametrize("tool", sorted(CONTINUATION_TOOLS))
def test_user_settings_prompts_when_missing_then_inherit_default(tool: str) -> None:
    """Prompt lookup should fall back to default template when specific tool missing."""
    settings = UserSettings.default()
    settings.prompts.pop(tool, None)

    prompt = settings.prompt_for(tool)

    assert "Continue" in prompt, "Fallback prompt should be informative"


