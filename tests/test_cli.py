#!/usr/bin/env python3
# this_file: tests/test_cli.py
"""Tests for the Fire-based vomgr CLI."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fire.core import FireError

from vexy_overnight import __version__
from vexy_overnight.cli import VomgrCLI
from vexy_overnight.user_settings import UserSettings


@pytest.fixture()
def cli_with_mocks():
    """Return a CLI instance wired to mock collaborator objects.

    Returns:
        types.SimpleNamespace: Container exposing the CLI and the injected
        mocks so that tests can inspect calls and captured state.
    """
    config_mgr = MagicMock()
    hook_mgr = MagicMock()
    launcher_mgr = MagicMock()
    rules_mgr = MagicMock()
    update_mgr = MagicMock()
    settings = UserSettings.default()
    save_calls = []

    def config_factory() -> MagicMock:
        return config_mgr

    def hook_factory() -> MagicMock:
        return hook_mgr

    def launcher_factory() -> MagicMock:
        return launcher_mgr

    def rules_factory(*, global_mode: bool = False) -> MagicMock:
        rules_mgr.global_mode = global_mode
        return rules_mgr

    def update_factory() -> MagicMock:
        return update_mgr

    def loader() -> UserSettings:
        return settings

    def saver(updated: UserSettings) -> Path:
        save_calls.append(updated)
        return Path("/tmp/settings.toml")

    cli = VomgrCLI(
        config_factory=config_factory,
        hook_factory=hook_factory,
        launcher_factory=launcher_factory,
        rules_factory=rules_factory,
        update_factory=update_factory,
        settings_loader=loader,
        settings_saver=saver,
    )

    return SimpleNamespace(
        cli=cli,
        config=config_mgr,
        hook=hook_mgr,
        launcher=launcher_mgr,
        rules=rules_mgr,
        update=update_mgr,
        settings=settings,
        saves=save_calls,
    )


def test_install_command(cli_with_mocks):
    """Install command installs hooks and initialises configuration files."""
    result = cli_with_mocks.cli.install()
    assert "Installation complete" in result
    cli_with_mocks.hook.install_hooks.assert_called_once()
    cli_with_mocks.config.setup_configs.assert_called_once()


def test_install_with_backup_legacy(cli_with_mocks):
    """Requesting legacy backups triggers :meth:`ConfigManager.backup_legacy_configs`."""
    cli_with_mocks.cli.install(backup_legacy=True)
    cli_with_mocks.config.backup_legacy_configs.assert_called_once()


def test_install_with_migrate(cli_with_mocks):
    """Passing ``migrate=True`` invokes the legacy migration routine."""
    cli_with_mocks.cli.install(migrate=True)
    cli_with_mocks.config.migrate_from_legacy.assert_called_once()


def test_uninstall_command(cli_with_mocks):
    """Uninstall removes hooks and restores default configurations."""
    result = cli_with_mocks.cli.uninstall()
    assert "Hooks removed" in result
    cli_with_mocks.hook.uninstall_hooks.assert_called_once()
    cli_with_mocks.config.restore_defaults.assert_called_once()


def test_enable_claude(cli_with_mocks):
    """Enabling Claude delegates to :meth:`ConfigManager.enable_claude_hook`."""
    message = cli_with_mocks.cli.enable("claude")
    assert "claude continuation enabled" in message
    cli_with_mocks.config.enable_claude_hook.assert_called_once()


def test_enable_codex(cli_with_mocks):
    """Enabling Codex delegates to :meth:`ConfigManager.enable_codex_hook`."""
    message = cli_with_mocks.cli.enable("codex")
    assert "codex continuation enabled" in message
    cli_with_mocks.config.enable_codex_hook.assert_called_once()


def test_enable_gemini(cli_with_mocks):
    """Gemini enable call returns the placeholder "not implemented" message."""
    message = cli_with_mocks.cli.enable("gemini")
    assert "not yet implemented" in message


def test_enable_invalid_tool(cli_with_mocks):
    """Unsupported tool names raise a :class:`FireError`."""
    with pytest.raises(FireError):
        cli_with_mocks.cli.enable("invalid")


def test_disable_claude(cli_with_mocks):
    """Disable command deactivates Claude continuation hook."""
    message = cli_with_mocks.cli.disable("claude")
    assert "claude continuation disabled" in message
    cli_with_mocks.config.disable_claude_hook.assert_called_once()


def test_disable_codex(cli_with_mocks):
    """Disable command deactivates Codex continuation hook."""
    message = cli_with_mocks.cli.disable("codex")
    assert "codex continuation disabled" in message
    cli_with_mocks.config.disable_codex_hook.assert_called_once()


def test_status_command(cli_with_mocks):
    """Status command reports hook enablement and binary presence."""
    cli_with_mocks.config.is_claude_hook_enabled.return_value = True
    cli_with_mocks.config.is_codex_hook_enabled.return_value = False
    cli_with_mocks.config.is_tool_installed.side_effect = lambda tool: tool != "codex"

    status = cli_with_mocks.cli.status()

    assert "Claude: enabled" in status
    assert "Codex: disabled" in status
    assert "Gemini" in status


def test_run_claude(cli_with_mocks):
    """Run command for Claude triggers :meth:`LauncherManager.launch_claude`."""
    message = cli_with_mocks.cli.run("claude")
    assert message == "Launched claude"
    cli_with_mocks.launcher.launch_claude.assert_called_once()


def test_run_codex(cli_with_mocks):
    """Run command for Codex forwards options to :meth:`launch_codex`."""
    message = cli_with_mocks.cli.run("codex", profile="gpt5")
    assert message == "Launched codex"
    cli_with_mocks.launcher.launch_codex.assert_called_once_with(
        cwd=None, profile="gpt5", prompt=None
    )


def test_run_invalid_tool(cli_with_mocks):
    """Unknown tools cause Fire to raise a :class:`FireError`."""
    with pytest.raises(FireError):
        cli_with_mocks.cli.run("invalid")


def test_rules_sync(cli_with_mocks):
    """Rules command with ``sync=True`` invokes file synchronisation."""
    response = cli_with_mocks.cli.rules(sync=True)
    assert "Instruction files synchronized" in response
    cli_with_mocks.rules.sync_files.assert_called_once()


def test_rules_append(cli_with_mocks):
    """Rules command with ``append`` forwards text to the manager."""
    response = cli_with_mocks.cli.rules(append="extra")
    assert "Text appended" in response
    cli_with_mocks.rules.append_to_files.assert_called_with("extra")


def test_rules_search(cli_with_mocks):
    """Rules command with ``search`` surfaces formatted search results."""
    cli_with_mocks.rules.search_files.return_value = {"CLAUDE.md": ["match"]}
    response = cli_with_mocks.cli.rules(search="pattern")
    assert "CLAUDE.md" in response
    cli_with_mocks.rules.search_files.assert_called_with("pattern")


def test_update_check(cli_with_mocks):
    """Update command with ``check`` prints version comparisons."""
    cli_with_mocks.update.check_versions.return_value = {
        "claude": {"current": "1.0", "available": "1.1"}
    }
    message = cli_with_mocks.cli.update(check=True)
    assert "claude: 1.0 -> 1.1" in message
    cli_with_mocks.update.check_versions.assert_called_once()


def test_continuation_set_updates_target(cli_with_mocks):
    """Continuation.set updates the target mapping and persists settings."""
    message = cli_with_mocks.cli.continuation.set("claude", "gemini")
    assert "claude continuation now targets gemini" in message
    assert cli_with_mocks.settings.continuations["claude"].target == "gemini"
    assert cli_with_mocks.saves, "settings should be persisted"


def test_continuation_disable_turns_off(cli_with_mocks):
    """Continuation.disable flips the enabled flag to ``False``."""
    message = cli_with_mocks.cli.continuation.disable("codex")
    assert "codex continuation disabled" in message
    assert cli_with_mocks.settings.continuations["codex"].enabled is False


def test_prompt_set_updates_template(cli_with_mocks):
    """Prompt.set stores the provided template for the chosen tool."""
    message = cli_with_mocks.cli.prompt.set("claude", "Focus {todo}")
    assert "Prompt for claude updated" in message
    assert cli_with_mocks.settings.prompts["claude"] == "Focus {todo}"


def test_notify_set_updates_message_and_enabled(cli_with_mocks):
    """Notify.set mutates message text and activation state."""
    message = cli_with_mocks.cli.notify.set(message="Next: {target}", enabled=False)
    assert "Notifications disabled" in message
    prefs = cli_with_mocks.settings.notifications
    assert prefs.message == "Next: {target}"
    assert prefs.enabled is False


def test_notify_sound_updates_sound(cli_with_mocks):
    """Notify.sound persists the requested notification sound identifier."""
    message = cli_with_mocks.cli.notify.sound("ding")
    assert "Notification sound set to ding" in message
    assert cli_with_mocks.settings.notifications.sound == "ding"


def test_terminal_set_updates_command(cli_with_mocks):
    """Terminal.set records the terminal command for the given platform."""
    message = cli_with_mocks.cli.terminal.set("darwin", "open", "-a", "Alacritty", "{command}")
    assert "Terminal command for darwin updated" in message
    assert cli_with_mocks.settings.terminals.defaults["darwin"][-1] == "{command}"


def test_version_returns_package_version(cli_with_mocks):
    """Version command surfaces the package's ``__version__`` string."""
    assert cli_with_mocks.cli.version() == __version__
