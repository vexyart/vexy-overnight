#!/usr/bin/env python3
# this_file: src/vexy_overnight/config.py
"""Helpers for managing Claude and Codex configuration files.

The :class:`ConfigManager` centralises filesystem operations required for
installing or removing continuation hooks.  All write operations are performed
via a defensive write-and-validate workflow that creates a backup before
touching the original files, guaranteeing users can roll back on failure.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import tomli
import tomli_w
from loguru import logger


class ConfigManager:
    """Encapsulate Claude/Codex configuration mutations with rollback safety.

    Instances are lightweight and stateless aside from pre-computing key
    filesystem paths.  The manager exposes high-level operations used by the
    CLI as well as a collection of private helpers for reading, writing and
    validating JSON/TOML files.
    """

    def __init__(self) -> None:
        """Initialise the manager with derived paths under the user home."""
        home = Path.home()
        self.home = home
        self.claude_config = home / ".claude" / "settings.json"
        self.codex_config = home / ".codex" / "config.toml"

    # Public helpers
    def backup_config(self, config_path: Path) -> Path | None:
        """Create a timestamped backup next to ``config_path``.

        Args:
            config_path: File that should be duplicated before mutation.

        Returns:
            Path | None: Path to the backup file, or ``None`` when the source
            file does not yet exist.
        """
        if not config_path.exists():
            return None
        backup = config_path.with_suffix(
            f"{config_path.suffix}.backup.{datetime.now():%Y%m%d_%H%M%S}"
        )
        shutil.copy2(config_path, backup)
        logger.debug("Backed up %s to %s", config_path, backup)
        return backup

    def is_claude_hook_enabled(self) -> bool:
        """Check whether the Claude "Stop" hook already references vocl-go.

        Returns:
            bool: ``True`` if the hook configuration references the helper.
        """
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
        """Check whether the Codex notify hook points to voco-go.

        Returns:
            bool: ``True`` when at least one notify entry references the
            helper script.
        """
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
        """Write a Claude Stop hook that launches ``vocl-go``."""
        config = self._load_json(self.claude_config)
        command = f'"{self.home / ".claude" / "hooks" / "vocl-go.py"}" "$CLAUDE_PROJECT_DIR"'
        config.setdefault("hooks", {})["Stop"] = [
            {"hooks": [{"type": "command", "command": command}]}
        ]
        self._write_json_with_rollback(self.claude_config, config)
        logger.info("Claude Stop hook enabled")

    def disable_claude_hook(self) -> None:
        """Remove the Claude Stop hook if present."""
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
        """Write a Codex "notify" hook pointing at ``voco-go``."""
        config = self._load_toml(self.codex_config)
        config["notify"] = [str(self.home / ".codex" / "voco-go.py")]
        self._write_toml_with_rollback(self.codex_config, config)
        logger.info("Codex notify hook enabled")

    def disable_codex_hook(self) -> None:
        """Remove the Codex notify hook when it exists."""
        if not self.codex_config.exists():
            return
        config = self._load_toml(self.codex_config)
        if "notify" in config:
            del config["notify"]
            self._write_toml_with_rollback(self.codex_config, config)
        else:
            logger.debug("Codex notify hook already absent; nothing to disable")

    def is_tool_installed(self, tool: str) -> bool:
        """Return whether ``tool`` is discoverable in ``PATH``.

        Args:
            tool: Command name to probe via ``which``.

        Returns:
            bool: ``True`` if the command resolves successfully.
        """
        from subprocess import run  # Local import keeps module scope minimal

        try:
            return run(["which", tool], capture_output=True, text=True, check=False).returncode == 0
        except Exception:  # pragma: no cover - defensive guard
            return False

    def backup_legacy_configs(self) -> None:
        """Create backups for all known legacy configuration files."""
        for path in (
            self.home / ".claude" / "settings.json",
            self.home / ".codex" / "config.toml",
            self.home / ".gemini" / "config.json",
        ):
            if path.exists():
                self.backup_config(path)

    def migrate_from_legacy(self) -> None:
        """Rewrite legacy continuation hooks to reference the new helpers."""
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
            values = [
                hook_path if "codex4ever.py" in item else item for item in config.get("notify", [])
            ]
            if values:
                config["notify"] = values
                self._write_toml_with_rollback(self.codex_config, config)

    def setup_configs(self) -> None:
        """Ensure default configuration files exist for Claude and Codex."""
        if not self.claude_config.exists():
            self._write_json_with_rollback(self.claude_config, {})
        if not self.codex_config.exists():
            self._write_toml_with_rollback(self.codex_config, {})

    def restore_defaults(self) -> None:
        """Remove helper hooks from both configurations."""
        self.disable_claude_hook()
        self.disable_codex_hook()

    # Internal helpers
    def _load_json(self, path: Path) -> dict[str, Any]:
        """Load JSON document from ``path`` returning an empty dict on miss.

        Args:
            path: File to read.

        Returns:
            dict[str, Any]: Parsed document or an empty dictionary.
        """
        if path.exists():
            with open(path, encoding="utf-8") as handle:
                return json.load(handle)
        return {}

    def _load_toml(self, path: Path) -> dict[str, Any]:
        """Load TOML document from ``path`` returning an empty dict on miss.

        Args:
            path: File to read.

        Returns:
            dict[str, Any]: Parsed document or an empty dictionary.
        """
        if path.exists():
            with open(path, "rb") as handle:
                return tomli.load(handle)
        return {}

    def _write_json_with_rollback(self, target: Path, data: dict[str, Any]) -> None:
        """Persist ``data`` to ``target`` as JSON using rollback semantics.

        Args:
            target: File that should receive the JSON document.
            data: Payload to serialise.
        """

        def write_json(path: Path) -> None:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2)

        self._write_with_rollback(target, write_json, self._validate_json_file)

    def _write_toml_with_rollback(self, target: Path, data: dict[str, Any]) -> None:
        """Persist ``data`` to ``target`` as TOML using rollback semantics.

        Args:
            target: File that should receive the TOML document.
            data: Payload to serialise.
        """

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
        """Write to ``target`` atomically by validating a temporary file first.

        Args:
            target: File that should be replaced.
            write_func: Callback that writes the payload to the temporary file.
            validate_func: Callback that validates the temporary file contents.

        Raises:
            Exception: Propagates exceptions from ``write_func`` or
                ``validate_func`` after restoring the backup.
        """
        backup = self.backup_config(target)
        tmp_path = target.with_suffix(target.suffix + ".tmp")
        if tmp_path.exists():
            tmp_path.unlink()
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            write_func(tmp_path)
            validate_func(tmp_path)
            tmp_path.replace(target)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink()
            self._restore_from_backup(target, backup)
            raise

    def _validate_json_file(self, path: Path) -> None:
        """Read ``path`` ensuring it contains valid JSON.

        Args:
            path: File whose JSON structure should be validated.
        """
        with open(path, encoding="utf-8") as handle:
            json.load(handle)

    def _validate_toml_file(self, path: Path) -> None:
        """Read ``path`` ensuring it contains valid TOML.

        Args:
            path: File whose TOML structure should be validated.
        """
        with open(path, "rb") as handle:
            tomli.load(handle)

    def _restore_from_backup(self, target: Path, backup: Path | None) -> None:
        """Restore ``target`` from ``backup`` or remove it when restoration fails.

        Args:
            target: File to restore.
            backup: Backup file previously created by :meth:`backup_config`.
        """
        if backup and backup.exists():
            shutil.copy2(backup, target)
        elif backup is None and target.exists():
            target.unlink()
