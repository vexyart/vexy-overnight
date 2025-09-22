#!/usr/bin/env python3
# this_file: src/vexy_overnight/user_settings.py
"""Load, validate, and persist user settings for continuation behaviour."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import tomli
import tomli_w

SETTINGS_DIR_NAME = ".vexy-overnight"
SETTINGS_FILE_NAME = "settings.toml"
CONTINUATION_TOOLS = ("claude", "codex", "gemini")

_DEFAULT_PROMPTS = {
    "claude": "Continue work in the next tool. Outstanding tasks:\n{todo}",
    "codex": "Pick up the session with these TODOs:\n{todo}",
    "gemini": "Continue assisting with current plan:\n{plan}",
}
_DEFAULT_TERMINAL_DEFAULTS = {
    "darwin": [
        "open",
        "-a",
        "Terminal",
        "--args",
        "bash",
        "-lc",
        "{command}; exec bash",
    ],
    "windows": [
        "wt",
        "powershell",
        "-NoExit",
        "-Command",
        "{command}",
    ],
    "linux": [
        "gnome-terminal",
        "--",
        "bash",
        "-lc",
        "{command}; exec bash",
    ],
}


@dataclass
class ContinuationPrefs:
    """Describe whether continuation is enabled and the target tool."""

    enabled: bool
    target: str


@dataclass
class NotificationPrefs:
    """Describe notification preferences for continuation events."""

    enabled: bool
    message: str
    sound: str


@dataclass
class TerminalPrefs:
    """Store terminal launch commands used by helper scripts."""

    defaults: dict[str, list[str]] = field(default_factory=dict)
    per_tool: dict[str, dict[str, list[str]]] = field(default_factory=dict)

    def command_for(self, tool: str, platform_key: str) -> list[str] | None:
        """Return the terminal command sequence for ``tool`` on ``platform_key``."""
        tool_commands = self.per_tool.get(tool, {})
        return tool_commands.get(platform_key) or self.defaults.get(platform_key)


@dataclass
class UserSettings:
    """Concrete settings object persisted to ``settings.toml``."""

    continuations: dict[str, ContinuationPrefs]
    prompts: dict[str, str]
    notifications: NotificationPrefs
    terminals: TerminalPrefs
    kill_old_sessions: bool

    @classmethod
    def default(cls) -> UserSettings:
        """Return a :class:`UserSettings` instance with packaged defaults.

        Returns:
            UserSettings: Settings initialised with bundled defaults.
        """
        continuations = {
            "claude": ContinuationPrefs(True, "codex"),
            "codex": ContinuationPrefs(True, "claude"),
            "gemini": ContinuationPrefs(False, "claude"),
        }
        notifications = NotificationPrefs(True, "Continuing on {target}", "success")
        terminals = TerminalPrefs(defaults=_DEFAULT_TERMINAL_DEFAULTS.copy())
        return cls(continuations, _DEFAULT_PROMPTS.copy(), notifications, terminals, True)

    def validate(self) -> None:
        """Ensure continuation targets and control flags are valid.

        Raises:
            ValueError: If continuation targets reference unknown tools or the
                kill flag is not boolean.
        """
        for source, prefs in self.continuations.items():
            if prefs.target not in CONTINUATION_TOOLS:
                raise ValueError(f"unknown continuation target '{prefs.target}' for {source}")
        if not isinstance(self.kill_old_sessions, bool):
            raise ValueError("kill_old_sessions must be boolean")

    def to_dict(self) -> dict[str, object]:
        """Serialise the settings dataclass into a TOML-friendly mapping.

        Returns:
            dict[str, object]: Mapping ready to be written to ``settings.toml``.
        """
        return {
            "continuations": {
                tool: {"enabled": prefs.enabled, "target": prefs.target}
                for tool, prefs in self.continuations.items()
            },
            "prompts": self.prompts,
            "notifications": {
                "enabled": self.notifications.enabled,
                "message": self.notifications.message,
                "sound": self.notifications.sound,
            },
            "terminals": {
                "defaults": self.terminals.defaults,
                "per_tool": self.terminals.per_tool,
            },
            "kill_old_sessions": self.kill_old_sessions,
        }

    def prompt_for(self, tool: str) -> str:
        """Return the prompt template for ``tool`` with fallbacks.

        Args:
            tool: Tool name to fetch the prompt for.

        Returns:
            str: Template string with curly brace placeholders.
        """
        return self.prompts.get(tool) or self.prompts.get("claude") or "Continue"

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> UserSettings:
        """Create :class:`UserSettings` from a mapping previously serialised.

        Args:
            payload: Deserialised TOML content.

        Returns:
            UserSettings: Fully populated settings instance.
        """
        raw_cont = payload.get("continuations", {})
        continuations = {
            tool: ContinuationPrefs(
                bool(info.get("enabled", False)),
                info.get("target", "claude"),
            )
            for tool, info in raw_cont.items()
        }
        for tool in CONTINUATION_TOOLS:
            continuations.setdefault(tool, ContinuationPrefs(False, "claude"))
        prompts = _DEFAULT_PROMPTS.copy()
        prompts.update(payload.get("prompts", {}))
        notif_payload = payload.get("notifications", {})
        notifications = NotificationPrefs(
            bool(notif_payload.get("enabled", True)),
            notif_payload.get("message", "Continuing on {target}"),
            notif_payload.get("sound", "success"),
        )
        term_payload = payload.get("terminals", {})
        defaults = term_payload.get("defaults") or _DEFAULT_TERMINAL_DEFAULTS.copy()
        per_tool = term_payload.get("per_tool") or {}
        terminals = TerminalPrefs(defaults=defaults, per_tool=per_tool)
        kill_old_sessions = bool(payload.get("kill_old_sessions", True))
        settings = cls(continuations, prompts, notifications, terminals, kill_old_sessions)
        settings.validate()
        return settings


def settings_path(home: Path | None = None) -> Path:
    """Return the full path to ``settings.toml`` under ``home``.

    Args:
        home: Optional override directory; defaults to the current user's home.

    Returns:
        Path: Location of the settings file.
    """
    base = home or Path.home()
    return base / SETTINGS_DIR_NAME / SETTINGS_FILE_NAME


def load_user_settings(home: Path | None = None) -> UserSettings:
    """Load user settings from disk, creating defaults on first run.

    Args:
        home: Optional home directory override.

    Returns:
        UserSettings: Persisted settings or freshly created defaults.
    """
    path = settings_path(home)
    if not path.exists():
        settings = UserSettings.default()
        save_user_settings(settings, home)
        return settings
    with open(path, "rb") as handle:
        payload = tomli.load(handle)
    return UserSettings.from_dict(payload)


def save_user_settings(settings: UserSettings, home: Path | None = None) -> Path:
    """Persist ``settings`` to disk, creating a timestamped backup first.

    Args:
        settings: Settings instance to write.
        home: Optional home directory override.

    Returns:
        Path: Path to the written settings file.
    """
    settings.validate()
    target = settings_path(home)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        backup = target.with_suffix(f"{target.suffix}.backup.{datetime.now():%Y%m%d_%H%M%S}")
        shutil.copy2(target, backup)
    with open(target, "wb") as handle:
        tomli_w.dump(settings.to_dict(), handle)
    return target
