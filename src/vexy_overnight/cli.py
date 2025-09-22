#!/usr/bin/env python3
# this_file: src/vexy_overnight/cli.py
"""Command-line entrypoints for the Vexy Overnight Manager.

The CLI is implemented using :mod:`fire` to provide a nested command
hierarchy.  Each sub-command operates on a thin facade and delegates to the
corresponding manager classes.  This module therefore focuses on:

* Validating and normalising user input coming from Fire.
* Wiring together injectable collaborators to keep the CLI easily testable.
* Returning human-readable strings that form the command output.

All functions and classes in this file are intentionally lightweight wrappers
around the underlying managers.  They exist solely to translate CLI calls into
validated method invocations.
"""

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
    """Normalise and validate a continuation tool identifier.

    Args:
        tool: Raw tool name provided by the CLI caller.

    Returns:
        str: The lower-case tool name after validation.

    Raises:
        FireError: If ``tool`` is not a supported continuation target.
    """
    normalized = tool.lower()
    if normalized not in CONTINUATION_TOOLS:
        raise FireError("tool must be one of claude, codex, gemini")
    return normalized


class ContinuationCLI:
    """Fire namespace for managing continuation routing.

    The continuation settings determine which downstream tool should pick up
    the work once a session finishes.  This helper exposes the relevant
    ``vomgr continuation`` commands and keeps persistence concerns isolated in
    :class:`vexy_overnight.user_settings.UserSettings`.

    Attributes:
        _load: Loader that returns the latest persisted user settings.
        _save: Saver that persists mutated settings to disk.
    """

    def __init__(
        self,
        loader: Callable[[], UserSettings],
        saver: Callable[[UserSettings], Path],
    ) -> None:
        """Create a continuation namespace with injected persistence helpers.

        Args:
            loader: Callable used to fetch the current settings snapshot.
            saver: Callable used to persist any changes back to storage.
        """
        self._load = loader
        self._save = saver

    def set(self, source: str, target: str) -> str:
        """Enable continuation for ``source`` and point it at ``target``.

        Args:
            source: Tool whose completion should trigger continuation.
            target: Tool that should be launched after ``source`` completes.

        Returns:
            Human-readable confirmation message describing the new mapping.
        """
        source_key = _validate_tool(source)
        target_key = _validate_tool(target)

        settings = self._load()
        prefs = settings.continuations[source_key]
        prefs.enabled = True
        prefs.target = target_key
        self._save(settings)
        return f"{source_key} continuation now targets {target_key}"

    def disable(self, source: str) -> str:
        """Turn off continuation for ``source`` while leaving other tools intact.

        Args:
            source: Tool whose continuation preferences should be disabled.

        Returns:
            Confirmation string that mirrors CLI output.
        """
        source_key = _validate_tool(source)

        settings = self._load()
        settings.continuations[source_key].enabled = False
        self._save(settings)
        return f"{source_key} continuation disabled"

    def status(self) -> dict[str, dict[str, object]]:
        """Return a structured snapshot of continuation routing configuration.

        Returns:
            Mapping keyed by tool name whose value shows ``enabled`` and
            ``target`` fields as understood by the CLI.
        """
        settings = self._load()
        return {
            tool: {
                "enabled": prefs.enabled,
                "target": prefs.target,
            }
            for tool, prefs in settings.continuations.items()
        }


class PromptCLI:
    """Expose commands for editing continuation prompt templates.

    Attributes:
        _load: Callable returning the persisted :class:`UserSettings` object.
        _save: Callable that persists updates back to storage.
    """

    def __init__(
        self,
        loader: Callable[[], UserSettings],
        saver: Callable[[UserSettings], Path],
    ) -> None:
        """Initialise the CLI namespace with storage helpers.

        Args:
            loader: Fetches the latest settings prior to mutation.
            saver: Persists updated settings once modifications are applied.
        """
        self._load = loader
        self._save = saver

    def set(self, tool: str, template: str) -> str:
        """Persist a continuation prompt template for ``tool``.

        Args:
            tool: Tool identifier whose prompt should be updated.
            template: New template string containing formatting placeholders.

        Returns:
            Informational message confirming the update.
        """
        tool_key = _validate_tool(tool)
        settings = self._load()
        settings.prompts[tool_key] = template
        self._save(settings)
        return f"Prompt for {tool_key} updated"

    def show(self, tool: str) -> str:
        """Retrieve the stored prompt template for ``tool``.

        Args:
            tool: Tool identifier whose template should be displayed.

        Returns:
            The configured template string or a reasonable fallback.
        """
        tool_key = _validate_tool(tool)
        settings = self._load()
        return settings.prompts.get(tool_key, "Continue")


class NotifyCLI:
    """Manage notification preferences exposed via the CLI.

    Notifications are delivered by the continuation helpers to let the user
    know which tool is about to launch.  This namespace lets the CLI caller
    tune the message, toggle the feature, or switch the alert sound.
    """

    def __init__(
        self,
        loader: Callable[[], UserSettings],
        saver: Callable[[UserSettings], Path],
    ) -> None:
        """Initialise the CLI sub-component with persistence helpers.

        Args:
            loader: Callable retrieving the latest settings snapshot.
            saver: Callable persisting modified settings back to disk.
        """
        self._load = loader
        self._save = saver

    def set(self, message: str | None = None, enabled: bool | None = None) -> str:
        """Override notification content and activation state.

        Args:
            message: Optional replacement string for the notification body.
            enabled: Optional flag toggling notification delivery on/off.

        Returns:
            str: Confirmation reflecting the resulting notification state.
        """
        settings = self._load()
        if message is not None:
            settings.notifications.message = message
        if enabled is not None:
            settings.notifications.enabled = bool(enabled)
        self._save(settings)
        state = "enabled" if settings.notifications.enabled else "disabled"
        return f"Notifications {state}"

    def sound(self, name: str) -> str:
        """Persist the configured notification sound identifier.

        Args:
            name: Name of the sound asset understood by the helper scripts.

        Returns:
            Confirmation string describing the stored sound.

        Raises:
            FireError: If ``name`` is empty.
        """
        if not name:
            raise FireError("sound name must be non-empty")
        settings = self._load()
        settings.notifications.sound = name
        self._save(settings)
        return f"Notification sound set to {name}"

    def show(self) -> dict[str, object]:
        """Display a serialisable snapshot of notification preferences.

        Returns:
            dict[str, object]: Mapping of ``enabled``, ``message`` and ``sound``
            fields used by the helper scripts.
        """
        settings = self._load()
        prefs = settings.notifications
        return {"enabled": prefs.enabled, "message": prefs.message, "sound": prefs.sound}


class TerminalCLI:
    """Manage how continuation helpers spawn terminal windows.

    Each platform can have a different command template.  This namespace maps
    directly to ``vomgr terminal`` commands, allowing users to set or inspect
    the stored command sequences.
    """

    def __init__(
        self,
        loader: Callable[[], UserSettings],
        saver: Callable[[UserSettings], Path],
    ) -> None:
        """Store helpers used to read and persist user settings.

        Args:
            loader: Callable returning the latest :class:`UserSettings`.
            saver: Callable persisting updated settings objects.
        """
        self._load = loader
        self._save = saver

    def set(self, platform_key: str, *command: str) -> str:
        """Persist a terminal launch command for ``platform_key``.

        Args:
            platform_key: Platform identifier (``darwin``, ``linux`` etc.).
            *command: Command template ending with an argument containing the
                ``{command}`` placeholder that will be replaced at runtime.

        Returns:
            str: Confirmation that mirrors CLI output.

        Raises:
            FireError: If no command arguments are supplied or the placeholder
                is missing from the final element.
        """
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
        """Return the stored terminal command for ``platform_key``.

        Args:
            platform_key: Platform identifier to inspect.

        Returns:
            list[str]: Command sequence saved for the platform.

        Raises:
            FireError: If the command has not been configured yet.
        """
        key = platform_key.lower()
        settings = self._load()
        command = settings.terminals.defaults.get(key)
        if command is None:
            raise FireError(f"no terminal command configured for {key}")
        return command


class VomgrCLI:
    """Top-level Fire component wiring together CLI operations.

    Each public method corresponds to a CLI command exposed to users.  The
    class coordinates manager instances that perform the actual work, keeping
    everything injectable for testing.
    """

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
        """Initialise the CLI with factories for its collaborators.

        Args:
            config_factory: Produces :class:`ConfigManager` instances on demand.
            hook_factory: Produces :class:`HookManager` objects.
            launcher_factory: Produces :class:`LauncherManager` objects.
            rules_factory: Produces :class:`RulesManager` instances; accepts a
                ``global_mode`` flag from callers.
            update_factory: Produces :class:`UpdateManager` objects.
            settings_loader: Loads persisted user settings for subcommands.
            settings_saver: Persists updated settings back to disk.
        """
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
        """Return the installed vomgr package version string.

        Returns:
            str: Semantic version sourced from :mod:`vexy_overnight`.
        """
        return __version__

    def install(self, backup_legacy: bool = False, migrate: bool = False) -> str:
        """Install continuation hooks and ensure configs are ready.

        Args:
            backup_legacy: When ``True`` create timestamped backups of legacy
                configuration files before modifying anything.
            migrate: When ``True`` attempt to rewrite legacy hook references to
                the modern helpers; otherwise new default configs are created.

        Returns:
            str: Multi-line summary describing each installation step.
        """
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
        """Remove installed hooks and restore default configuration files.

        Returns:
            str: Two-line status message summarising the performed work.
        """
        config_mgr = self._config_factory()
        hook_mgr = self._hook_factory()

        hook_mgr.uninstall_hooks()
        config_mgr.restore_defaults()
        return "Hooks removed\nConfigurations restored to defaults"

    def enable(self, tool: str) -> str:
        """Enable continuation automation for ``tool``.

        Args:
            tool: Tool identifier to enable (``claude`` or ``codex``).

        Returns:
            str: Confirmation message, or a notice when Gemini is unsupported.

        Raises:
            FireError: If ``tool`` is not recognised by the CLI.
        """
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
        """Disable continuation automation for ``tool``.

        Args:
            tool: Tool identifier to disable.

        Returns:
            str: Confirmation message, or a notice when Gemini is unsupported.

        Raises:
            FireError: If ``tool`` is not recognised.
        """
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
        """Launch one of the supported AI CLIs with continuation defaults.

        Args:
            tool: Tool identifier to launch.
            cwd: Optional working directory in which the tool should start.
            profile: Optional profile name used by Codex.
            model: Optional model identifier consumed by Claude launcher.
            prompt: Optional initial prompt passed to the launched CLI.

        Returns:
            str: Message confirming which tool was launched.

        Raises:
            FireError: If the tool name cannot be validated.
        """
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
        """Perform instruction file operations via :class:`RulesManager`.

        Args:
            sync: When ``True`` mirror instruction files between locations.
            append: Text to append to each instruction file.
            search: Pattern to search for within instruction files.
            replace: Two-item iterable specifying search and replacement text.
            global_mode: When ``True`` operate on global instruction files.

        Returns:
            str: Multi-line message describing the actions performed, or a
            default message when no flags were provided.

        Raises:
            FireError: If ``replace`` does not contain exactly two values.
        """
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
        """Trigger version checks or updates through :class:`UpdateManager`.

        Args:
            check: When ``True`` display available version information.
            cli: Update CLI tools only.
            self_update: Update the ``vexy-overnight`` package only.
            all: Convenience flag to update both CLI tools and the package.
            dry_run: When ``True`` simulate operations without side-effects.
            skip: Optional list of CLI tool names to skip during updates.

        Returns:
            str: Multi-line output summarising the actions performed or a
            default "no-op" message.
        """
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
        """Return a short human-readable summary of install state.

        Returns:
            str: Multi-line string describing which tools are enabled and
            whether their binaries are discoverable.
        """
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
    """Invoke Fire with :class:`VomgrCLI` as the root component.

    The function exists so console entry points created by packaging tools can
    import and execute it directly.
    """
    fire.Fire(VomgrCLI)


if __name__ == "__main__":
    main()
