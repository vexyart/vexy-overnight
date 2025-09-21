#!/usr/bin/env python3
# this_file: src/vexy_overnight/cli.py
"""Fire-based CLI for vomgr (Vexy Overnight Manager)."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

import fire
from fire.core import FireError

from . import __version__
from .config import ConfigManager
from .hooks import HookManager
from .launchers import LauncherManager
from .rules import RulesManager
from .updater import UpdateManager
from .user_settings import (
    CONTINUATION_TOOLS,
    UserSettings,
    load_user_settings,
    save_user_settings,
)


def _validate_tool(tool: str) -> str:
    normalized = tool.lower()
    if normalized not in CONTINUATION_TOOLS:
        raise FireError("tool must be one of claude, codex, gemini")
    return normalized


class ContinuationCLI:
    """Continuation mapping configuration commands."""

    def __init__(
        self,
        loader: Callable[[], UserSettings],
        saver: Callable[[UserSettings], Path],
    ) -> None:
        self._load = loader
        self._save = saver

    def set(self, source: str, target: str) -> str:
        source_key = _validate_tool(source)
        target_key = _validate_tool(target)

        settings = self._load()
        prefs = settings.continuations[source_key]
        prefs.enabled = True
        prefs.target = target_key
        self._save(settings)
        return f"{source_key} continuation now targets {target_key}"

    def disable(self, source: str) -> str:
        source_key = _validate_tool(source)

        settings = self._load()
        settings.continuations[source_key].enabled = False
        self._save(settings)
        return f"{source_key} continuation disabled"

    def status(self) -> dict[str, dict[str, object]]:
        settings = self._load()
        return {
            tool: {
                "enabled": prefs.enabled,
                "target": prefs.target,
            }
            for tool, prefs in settings.continuations.items()
        }


class PromptCLI:
    """Continuation prompt configuration."""

    def __init__(
        self,
        loader: Callable[[], UserSettings],
        saver: Callable[[UserSettings], Path],
    ) -> None:
        self._load = loader
        self._save = saver

    def set(self, tool: str, template: str) -> str:
        tool_key = _validate_tool(tool)
        settings = self._load()
        settings.prompts[tool_key] = template
        self._save(settings)
        return f"Prompt for {tool_key} updated"

    def show(self, tool: str) -> str:
        tool_key = _validate_tool(tool)
        settings = self._load()
        return settings.prompts.get(tool_key, "Continue")


class NotifyCLI:
    """Notification message and sound controls."""

    def __init__(
        self,
        loader: Callable[[], UserSettings],
        saver: Callable[[UserSettings], Path],
    ) -> None:
        self._load = loader
        self._save = saver

    def set(self, message: str | None = None, enabled: bool | None = None) -> str:
        settings = self._load()
        if message is not None:
            settings.notifications.message = message
        if enabled is not None:
            settings.notifications.enabled = bool(enabled)
        self._save(settings)
        state = "enabled" if settings.notifications.enabled else "disabled"
        return f"Notifications {state}"

    def sound(self, name: str) -> str:
        if not name:
            raise FireError("sound name must be non-empty")
        settings = self._load()
        settings.notifications.sound = name
        self._save(settings)
        return f"Notification sound set to {name}"

    def show(self) -> dict[str, object]:
        settings = self._load()
        prefs = settings.notifications
        return {"enabled": prefs.enabled, "message": prefs.message, "sound": prefs.sound}


class TerminalCLI:
    """Terminal launch command configuration."""

    def __init__(
        self,
        loader: Callable[[], UserSettings],
        saver: Callable[[UserSettings], Path],
    ) -> None:
        self._load = loader
        self._save = saver

    def set(self, platform_key: str, *command: str) -> str:
        key = platform_key.lower()
        if not command:
            raise FireError("provide a terminal command containing {command} placeholder")
        if "{command}" not in command[-1]:
            raise FireError("last argument must include {command} placeholder")
        settings = self._load()
        settings.terminals.defaults[key] = list(command)
        self._save(settings)
        return f"Terminal command for {key} updated"

    def show(self, platform_key: str) -> list[str]:
        key = platform_key.lower()
        settings = self._load()
        command = settings.terminals.defaults.get(key)
        if command is None:
            raise FireError(f"no terminal command configured for {key}")
        return command


class VomgrCLI:
    """Top-level Fire component providing vomgr commands."""

    def __init__(
        self,
        config_factory: Callable[[], ConfigManager] = ConfigManager,
        hook_factory: Callable[[], HookManager] = HookManager,
        launcher_factory: Callable[[], LauncherManager] = LauncherManager,
        rules_factory: Callable[[bool], RulesManager] = lambda global_mode=False: RulesManager(
            global_mode=global_mode
        ),
        update_factory: Callable[[], UpdateManager] = UpdateManager,
        settings_loader: Callable[[], UserSettings] = load_user_settings,
        settings_saver: Callable[[UserSettings], Path] = save_user_settings,
    ) -> None:
        self._config_factory = config_factory
        self._hook_factory = hook_factory
        self._launcher_factory = launcher_factory
        self._rules_factory = rules_factory
        self._update_factory = update_factory
        self._settings_loader = settings_loader
        self._settings_saver = settings_saver

        self.continuation = ContinuationCLI(settings_loader, settings_saver)
        self.prompt = PromptCLI(settings_loader, settings_saver)
        self.notify = NotifyCLI(settings_loader, settings_saver)
        self.terminal = TerminalCLI(settings_loader, settings_saver)

    def version(self) -> str:
        """Show vomgr version."""
        return __version__

    def install(self, backup_legacy: bool = False, migrate: bool = False) -> str:
        config_mgr = self._config_factory()
        hook_mgr = self._hook_factory()
        steps: list[str] = []

        if backup_legacy:
            config_mgr.backup_legacy_configs()
            steps.append("Legacy configurations backed up")

        hook_mgr.install_hooks()
        steps.append("Continuation hooks installed")

        if migrate:
            config_mgr.migrate_from_legacy()
            steps.append("Settings migrated from legacy tools")
        else:
            config_mgr.setup_configs()
            steps.append("Configuration files set up")

        steps.append("Installation complete")
        return "\n".join(steps)

    def uninstall(self) -> str:
        config_mgr = self._config_factory()
        hook_mgr = self._hook_factory()

        hook_mgr.uninstall_hooks()
        config_mgr.restore_defaults()
        return "Hooks removed\nConfigurations restored to defaults"

    def enable(self, tool: str) -> str:
        tool_key = _validate_tool(tool)
        config_mgr = self._config_factory()
        if tool_key == "claude":
            config_mgr.enable_claude_hook()
        elif tool_key == "codex":
            config_mgr.enable_codex_hook()
        else:
            return "Gemini continuation not yet implemented"
        return f"{tool_key} continuation enabled"

    def disable(self, tool: str) -> str:
        tool_key = _validate_tool(tool)
        config_mgr = self._config_factory()
        if tool_key == "claude":
            config_mgr.disable_claude_hook()
        elif tool_key == "codex":
            config_mgr.disable_codex_hook()
        else:
            return "Gemini continuation not yet implemented"
        return f"{tool_key} continuation disabled"

    def run(
        self,
        tool: str,
        cwd: str | None = None,
        profile: str | None = None,
        model: str | None = None,
        prompt: str | None = None,
    ) -> str:
        tool_key = _validate_tool(tool)
        launcher = self._launcher_factory()
        path = Path(cwd) if cwd else None
        if tool_key == "claude":
            launcher.launch_claude(cwd=path, model=model, prompt=prompt)
        elif tool_key == "codex":
            launcher.launch_codex(cwd=path, profile=profile, prompt=prompt)
        else:
            launcher.launch_gemini(cwd=path, prompt=prompt)
        return f"Launched {tool_key}"

    def rules(
        self,
        sync: bool = False,
        append: str | None = None,
        search: str | None = None,
        replace: Iterable[str] | None = None,
        global_mode: bool = False,
    ) -> str:
        rules_mgr = self._rules_factory(global_mode=global_mode)
        messages: list[str] = []

        if sync:
            rules_mgr.sync_files()
            messages.append("Instruction files synchronized")

        if append is not None:
            rules_mgr.append_to_files(append)
            messages.append("Text appended to instruction files")

        if search is not None:
            results = rules_mgr.search_files(search)
            formatted = [f"{path}: {len(matches)} match(es)" for path, matches in results.items()]
            messages.extend(formatted if formatted else ["No matches found"])

        if replace is not None:
            pair = list(replace)
            if len(pair) != 2:
                raise FireError("replace expects two values: search and replace")
            rules_mgr.replace_in_files(pair[0], pair[1])
            messages.append("Text replaced in instruction files")

        return "\n".join(messages) if messages else "No rules action performed"

    def update(
        self,
        check: bool = False,
        cli: bool = False,
        self_update: bool = False,
        all: bool = False,
        dry_run: bool = False,
        skip: list[str] | None = None,
    ) -> str:
        updater = self._update_factory()
        messages: list[str] = []
        skip = skip or []

        if check:
            versions = updater.check_versions()
            lines = [
                f"{tool}: {info['current']} -> {info['available']}"
                for tool, info in versions.items()
            ]
            messages.extend(lines if lines else ["No version information available"])

        if all or cli:
            updater.update_cli_tools(dry_run=dry_run, skip=skip)
            messages.append("CLI tools updated" if not dry_run else "CLI tools checked (dry run)")

        if all or self_update:
            updater.update_self(dry_run=dry_run)
            messages.append("vomgr package updated" if not dry_run else "vomgr update simulated")

        return "\n".join(messages) if messages else "No update action performed"

    def status(self) -> str:
        config_mgr = self._config_factory()
        claude_enabled = config_mgr.is_claude_hook_enabled()
        codex_enabled = config_mgr.is_codex_hook_enabled()
        claude_installed = config_mgr.is_tool_installed("claude")
        codex_installed = config_mgr.is_tool_installed("codex")
        gemini_installed = config_mgr.is_tool_installed("gemini")
        lines = [
            "vomgr status",
            f"Claude: {'enabled' if claude_enabled else 'disabled'} (installed={claude_installed})",
            f"Codex: {'enabled' if codex_enabled else 'disabled'} (installed={codex_installed})",
            f"Gemini installed={gemini_installed}",
        ]
        return "\n".join(lines)


def main() -> None:
    """CLI entry point."""
    fire.Fire(VomgrCLI)


if __name__ == "__main__":
    main()
