#!/usr/bin/env python3
# this_file: src/vexy_overnight/hook_runtime.py
"""Shared utilities for continuation hook scripts."""

from __future__ import annotations

import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

try:
    from .user_settings import (
        CONTINUATION_TOOLS,
        ContinuationPrefs,
        NotificationPrefs,
        TerminalPrefs,
        UserSettings,
        load_user_settings,
    )
except Exception:  # pragma: no cover - defensive fallback when package import fails
    CONTINUATION_TOOLS = ("claude", "codex", "gemini")

    _DEFAULT_PROMPTS = {
        "claude": "Continue work in the next tool. Outstanding tasks:\n{todo}",
        "codex": "Pick up the session with these TODOs:\n{todo}",
        "gemini": "Continue assisting with current plan:\n{plan}",
    }
    _DEFAULT_TERMINALS = {
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
    class ContinuationPrefs:  # type: ignore[override]
        enabled: bool
        target: str

    @dataclass
    class NotificationPrefs:  # type: ignore[override]
        enabled: bool
        message: str
        sound: str

    @dataclass
    class TerminalPrefs:  # type: ignore[override]
        defaults: dict[str, list[str]] = field(default_factory=dict)
        per_tool: dict[str, dict[str, list[str]]] = field(default_factory=dict)

        def command_for(self, tool: str, platform_key: str) -> list[str] | None:
            per_tool = self.per_tool.get(tool, {})
            return per_tool.get(platform_key) or self.defaults.get(platform_key)

    @dataclass
    class UserSettings:  # type: ignore[override]
        continuations: dict[str, ContinuationPrefs]
        prompts: dict[str, str]
        notifications: NotificationPrefs
        terminals: TerminalPrefs
        kill_old_sessions: bool = True

        @classmethod
        def default(cls) -> UserSettings:
            return cls(
                continuations={
                    "claude": ContinuationPrefs(True, "codex"),
                    "codex": ContinuationPrefs(True, "claude"),
                    "gemini": ContinuationPrefs(False, "claude"),
                },
                prompts=_DEFAULT_PROMPTS.copy(),
                notifications=NotificationPrefs(True, "Continuing on {target}", "success"),
                terminals=TerminalPrefs(defaults=_DEFAULT_TERMINALS.copy()),
                kill_old_sessions=True,
            )

    def load_user_settings() -> UserSettings:  # type: ignore[override]
        return UserSettings.default()


try:  # pragma: no cover - tests patch HOME instead of import failures
    from .session_state import SessionStateManager
except Exception:  # pragma: no cover - optional dependency in template context
    SessionStateManager = None  # type: ignore[assignment]

_DEFAULT_SETTINGS = UserSettings.default()
DEFAULT_PROMPTS = _DEFAULT_SETTINGS.prompts
DEFAULT_TERMINALS = _DEFAULT_SETTINGS.terminals.defaults
DEFAULT_PROMPT_FALLBACK = "Continue working on the current task"


def load_settings() -> UserSettings:
    """Load user settings, falling back to defaults if parsing fails."""
    try:
        return load_user_settings()
    except Exception:  # pragma: no cover - defensive guard
        return UserSettings.default()


def continuation_enabled(settings: UserSettings, tool: str) -> bool:
    """Return True when continuation is enabled for the given tool."""
    prefs = settings.continuations.get(tool)
    return bool(prefs and getattr(prefs, "enabled", False))


def resolve_target(settings: UserSettings, tool: str) -> str:
    """Resolve the continuation target for the given tool."""
    prefs = settings.continuations.get(tool)
    target = getattr(prefs, "target", "claude") if prefs else "claude"
    return target if target in CONTINUATION_TOOLS else "claude"


def _collect_todo_lines(project_dir: Path) -> list[str]:
    todo_path = project_dir / "TODO.md"
    if not todo_path.exists():
        return []
    try:
        lines = [line.strip() for line in todo_path.read_text(encoding="utf-8").splitlines()]
    except Exception:  # pragma: no cover - IO failures
        return []
    return [line for line in lines if line.startswith("- [ ]")][:5]


def _collect_plan_hint(project_dir: Path) -> str:
    plan_path = project_dir / "PLAN.md"
    if not plan_path.exists():
        return ""
    try:
        lines = plan_path.read_text(encoding="utf-8").splitlines()
    except Exception:  # pragma: no cover - IO failures
        return ""
    snippet = [line.strip() for line in lines if line.strip()][:5]
    return "\n".join(snippet)


def build_prompt(
    settings: UserSettings,
    source_tool: str,
    target_tool: str,
    project_dir: Path,
    fallback: str = DEFAULT_PROMPT_FALLBACK,
) -> str:
    """Render the continuation prompt using templates and project context."""
    template = settings.prompts.get(source_tool) or DEFAULT_PROMPTS.get(source_tool) or fallback
    todo_lines = _collect_todo_lines(project_dir)
    todo_text = "\n".join(todo_lines) if todo_lines else "No open TODO items."
    plan_text = _collect_plan_hint(project_dir) or "No plan summary available."
    values = {
        "todo": todo_text,
        "plan": plan_text,
        "target": target_tool,
        "source": source_tool,
    }
    try:
        return template.format(**values)
    except Exception:  # pragma: no cover - formatting guard
        return template


def resolve_executable(command_name: str) -> str:
    """Return an absolute path to command when discoverable."""
    resolved = shutil.which(command_name)
    return resolved or command_name


def build_target_command(target_tool: str, project_dir: Path, prompt: str) -> list[str]:
    """Build the command sequence for launching the target tool."""
    if target_tool == "codex":
        command = [
            resolve_executable("codex"),
            f"--cd={project_dir}",
            "-m",
            "gpt5",
            "--dangerously-bypass-approvals-and-sandbox",
            "--sandbox",
            "danger-full-access",
        ]
        if prompt:
            command.append(prompt)
        return command
    if target_tool == "gemini":
        command = [resolve_executable("gemini"), "-c", "-y"]
        if prompt:
            command.append(prompt)
        return command
    # Default to Claude
    command = [resolve_executable("claude"), "--continue", "--dangerously-skip-permissions"]
    if prompt:
        command.extend(["--prompt", prompt])
    return command


def prepare_env_updates(
    settings: UserSettings,
    source_tool: str,
    target_tool: str,
    prompt: str,
    project_dir: Path,
) -> dict[str, str]:
    """Prepare environment exports for helper and launched CLI."""
    notifications = settings.notifications
    try:
        message = notifications.message.format(target=target_tool, source=source_tool)
    except Exception:  # pragma: no cover - formatting guard
        message = notifications.message
    env_updates: dict[str, str] = {
        "VOMGR_TARGET_TOOL": target_tool,
        "VOMGR_SOURCE_TOOL": source_tool,
        "VOMGR_PROMPT": prompt,
        "VOMGR_PROJECT_DIR": str(project_dir),
        "VOMGR_NOTIFICATION_ENABLED": "1" if notifications.enabled else "0",
        "VOMGR_NOTIFICATION_MESSAGE": message,
        "VOMGR_NOTIFICATION_SOUND": notifications.sound,
        "VOMGR_KILL_OLD": "1" if settings.kill_old_sessions else "0",
    }
    return {key: value for key, value in env_updates.items() if value is not None}


def write_config(
    config_path: Path,
    command: Iterable[str],
    project_dir: Path,
    env_updates: Mapping[str, str],
) -> None:
    """Persist helper configuration for launching the continuation."""
    payload = {
        "command": [str(part) for part in command],
        "cwd": str(project_dir),
        "env": {str(key): str(value) for key, value in env_updates.items()},
    }
    config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def spawn_helper(
    helper_script: Path,
    project_dir: Path,
    settings: UserSettings,
    target_tool: str,
    *,
    terminal_env_key: str,
    force_direct: bool = False,
) -> None:
    """Spawn the helper script either via terminal command or directly."""
    if force_direct:
        _run_helper_direct(helper_script, project_dir)
        return

    command_string = _helper_command_string(helper_script, project_dir)
    platform_key = platform.system().lower()
    terminal_command = settings.terminals.command_for(target_tool, platform_key)
    if not terminal_command:
        terminal_command = settings.terminals.defaults.get(platform_key)
    if terminal_command:
        formatted = [part.replace("{command}", command_string) for part in terminal_command]
        subprocess.Popen(formatted, cwd=str(project_dir), env=os.environ.copy())
        return

    if platform_key == "darwin":
        _run_on_macos(helper_script, project_dir, command_string, terminal_env_key)
        return
    if platform_key == "windows":
        _run_on_windows(command_string)
        return
    _run_helper_direct(helper_script, project_dir)


def launch_from_config(config: Mapping[str, object]) -> None:
    """Execute the continuation based on serialized helper configuration."""
    command = [str(part) for part in config.get("command", []) if str(part)]
    if not command:
        sys.stderr.write("No command configured.\n")
        return

    cwd_value = str(config.get("cwd", "")).strip()
    cwd = cwd_value or None
    env_payload = config.get("env", {})
    env_updates = {
        str(key): str(value) for key, value in getattr(env_payload, "items", lambda: [])()
    }
    environment = os.environ.copy()
    environment.update(env_updates)

    try:
        process = subprocess.Popen(command, cwd=cwd, env=environment)
    except Exception as error:  # pragma: no cover - defensive guard
        sys.stderr.write(f"Failed to launch continuation: {error}\n")
        return

    target_tool = env_updates.get("VOMGR_TARGET_TOOL", "claude")
    kill_old = env_updates.get("VOMGR_KILL_OLD", "1") == "1"

    if SessionStateManager is not None:
        try:
            manager = SessionStateManager()
            manager.rotate_session(target_tool, process.pid, cwd or os.getcwd(), kill_old=kill_old)
        except Exception:  # pragma: no cover - session persistence best-effort
            pass

    _emit_notification(env_updates)
    process.wait()


def _helper_command_string(helper_script: Path, project_dir: Path) -> str:
    python_exec = shlex.quote(sys.executable or "python3")
    script = shlex.quote(str(helper_script))
    directory = shlex.quote(str(project_dir))
    return f"cd {directory} && {python_exec} {script}"


def _run_helper_direct(helper_script: Path, project_dir: Path) -> None:
    subprocess.run(
        [sys.executable or "python3", str(helper_script)], cwd=str(project_dir), check=False
    )


def _escape_applescript(value: str) -> str:
    escaped = value.replace("\\", "\\\\")
    return escaped.replace('"', '"')


def _run_on_macos(
    helper_script: Path, project_dir: Path, command: str, terminal_env_key: str
) -> None:
    terminal_app = os.environ.get(terminal_env_key) or "Terminal"
    osa = f'tell application "{terminal_app}" to do script "{_escape_applescript(command)}"'
    subprocess.run(["osascript", "-e", osa], check=False)


def _run_on_windows(command: str) -> None:
    subprocess.Popen(["cmd.exe", "/c", "start", "", "cmd.exe", "/k", command])


def _emit_notification(env_updates: Mapping[str, str]) -> None:
    if env_updates.get("VOMGR_NOTIFICATION_ENABLED") != "1":
        return
    message = env_updates.get("VOMGR_NOTIFICATION_MESSAGE")
    if not message:
        return
    sys.stdout.write(f"[vomgr] {message}\n")
    sys.stdout.flush()
    try:
        print("", end="", flush=True)
    except Exception:  # pragma: no cover - console may reject bell
        pass
