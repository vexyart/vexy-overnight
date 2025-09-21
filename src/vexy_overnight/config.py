#!/usr/bin/env python3
# this_file: src/vexy_overnight/config.py
"""Configuration management for vomgr."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from collections.abc import Callable

import tomli
import tomli_w
from loguru import logger


class ConfigManager:
    """Manage Claude and Codex configuration files with rollback safety."""
    def __init__(self) -> None:
        home = Path.home()
        self.home = home
        self.claude_config = home / ".claude" / "settings.json"
        self.codex_config = home / ".codex" / "config.toml"

    # Public helpers
    def backup_config(self, config_path: Path) -> Path | None:
        if not config_path.exists():
            return None
        backup = config_path.with_suffix(f"{config_path.suffix}.backup.{datetime.now():%Y%m%d_%H%M%S}")
        shutil.copy2(config_path, backup)
        logger.debug("Backed up %s to %s", config_path, backup)
        return backup
    def is_claude_hook_enabled(self) -> bool:
        if not self.claude_config.exists():
            return False
        try:
            with open(self.claude_config, encoding="utf-8") as handle:
                hooks = json.load(handle).get("hooks", {})
        except Exception as error:  # pragma: no cover - defensive guard
            logger.debug("Error checking Claude hook: %s", error)
            return False
        return any(
            "vocl-go" in inner.get("command", "")
            for hook in hooks.get("Stop", [])
            for inner in hook.get("hooks", [])
        )
    def is_codex_hook_enabled(self) -> bool:
        if not self.codex_config.exists():
            return False
        try:
            with open(self.codex_config, "rb") as handle:
                notify = tomli.load(handle).get("notify", [])
        except Exception as error:  # pragma: no cover - defensive guard
            logger.debug("Error checking Codex hook: %s", error)
            return False
        return any("voco-go" in item for item in notify)
    def enable_claude_hook(self) -> None:
        config = self._load_json(self.claude_config)
        command = f'"{self.home / ".claude" / "hooks" / "vocl-go.py"}" "$CLAUDE_PROJECT_DIR"'
        config.setdefault("hooks", {})["Stop"] = [{"hooks": [{"type": "command", "command": command}]}]
        self._write_json_with_rollback(self.claude_config, config)
        logger.info("Claude Stop hook enabled")
    def disable_claude_hook(self) -> None:
        if not self.claude_config.exists():
            return
        config = self._load_json(self.claude_config)
        if "hooks" in config and "Stop" in config["hooks"]:
            del config["hooks"]["Stop"]
            if not config["hooks"]:
                del config["hooks"]
            self._write_json_with_rollback(self.claude_config, config)
        else:
            logger.debug("Claude Stop hook already absent; nothing to disable")
    def enable_codex_hook(self) -> None:
        config = self._load_toml(self.codex_config)
        config["notify"] = [str(self.home / ".codex" / "voco-go.py")]
        self._write_toml_with_rollback(self.codex_config, config)
        logger.info("Codex notify hook enabled")
    def disable_codex_hook(self) -> None:
        if not self.codex_config.exists():
            return
        config = self._load_toml(self.codex_config)
        if "notify" in config:
            del config["notify"]
            self._write_toml_with_rollback(self.codex_config, config)
        else:
            logger.debug("Codex notify hook already absent; nothing to disable")
    def is_tool_installed(self, tool: str) -> bool:
        from subprocess import run  # Local import keeps module scope minimal

        try:
            return run(["which", tool], capture_output=True, text=True, check=False).returncode == 0
        except Exception:  # pragma: no cover - defensive guard
            return False
    def backup_legacy_configs(self) -> None:
        for path in (
            self.home / ".claude" / "settings.json",
            self.home / ".codex" / "config.toml",
            self.home / ".gemini" / "config.json",
        ):
            if path.exists():
                self.backup_config(path)
    def migrate_from_legacy(self) -> None:
        if self.claude_config.exists():
            self.backup_config(self.claude_config)
            config = self._load_json(self.claude_config)
            hook_path = str(self.home / ".claude" / "hooks" / "vocl-go.py")
            for hook in config.get("hooks", {}).get("Stop", []):
                for inner in hook.get("hooks", []):
                    if "claude4ever.py" in inner.get("command", ""):
                        inner["command"] = f'"{hook_path}" "$CLAUDE_PROJECT_DIR"'
            self._write_json_with_rollback(self.claude_config, config)

        if self.codex_config.exists():
            self.backup_config(self.codex_config)
            config = self._load_toml(self.codex_config)
            hook_path = str(self.home / ".codex" / "voco-go.py")
            values = [hook_path if "codex4ever.py" in item else item for item in config.get("notify", [])]
            if values:
                config["notify"] = values
                self._write_toml_with_rollback(self.codex_config, config)
    def setup_configs(self) -> None:
        if not self.claude_config.exists():
            self._write_json_with_rollback(self.claude_config, {})
        if not self.codex_config.exists():
            self._write_toml_with_rollback(self.codex_config, {})
    def restore_defaults(self) -> None:
        self.disable_claude_hook()
        self.disable_codex_hook()

    # Internal helpers
    def _load_json(self, path: Path) -> dict[str, Any]:
        if path.exists():
            with open(path, encoding="utf-8") as handle:
                return json.load(handle)
        return {}
    def _load_toml(self, path: Path) -> dict[str, Any]:
        if path.exists():
            with open(path, "rb") as handle:
                return tomli.load(handle)
        return {}
    def _write_json_with_rollback(self, target: Path, data: dict[str, Any]) -> None:
        def write_json(path: Path) -> None:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2)

        self._write_with_rollback(target, write_json, self._validate_json_file)
    def _write_toml_with_rollback(self, target: Path, data: dict[str, Any]) -> None:
        def write_toml(path: Path) -> None:
            with open(path, "wb") as handle:
                tomli_w.dump(data, handle)

        self._write_with_rollback(target, write_toml, self._validate_toml_file)
    def _write_with_rollback(
        self,
        target: Path,
        write_func: Callable[[Path], None],
        validate_func: Callable[[Path], None],
    ) -> None:
        backup = self.backup_config(target)
        tmp_path = target.with_suffix(target.suffix + ".tmp")
        if tmp_path.exists():
            tmp_path.unlink()
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            write_func(tmp_path)
            validate_func(tmp_path)
            tmp_path.replace(target)
        except Exception as error:
            if tmp_path.exists():
                tmp_path.unlink()
            self._restore_from_backup(target, backup)
            raise
    def _validate_json_file(self, path: Path) -> None:
        with open(path, encoding="utf-8") as handle:
            json.load(handle)
    def _validate_toml_file(self, path: Path) -> None:
        with open(path, "rb") as handle:
            tomli.load(handle)
    def _restore_from_backup(self, target: Path, backup: Path | None) -> None:
        if backup and backup.exists():
            shutil.copy2(backup, target)
        elif backup is None and target.exists():
            target.unlink()
