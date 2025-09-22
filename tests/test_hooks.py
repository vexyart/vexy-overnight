#!/usr/bin/env python3
# this_file: tests/test_hooks.py
"""Tests for continuation hooks produced by HookManager."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from vexy_overnight.hooks import FORCE_DIRECT_ENV_KEY, HookManager
from vexy_overnight.session_state import SessionStateManager
from vexy_overnight.user_settings import UserSettings, save_user_settings


def _write_recording_stub(executable_path: Path) -> None:
    """Create a stub CLI that records arguments, env hints, and PID."""
    executable_path.write_text(
        """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

record_path = Path(os.environ[\"HOOK_RECORD\"])
payload = {
    "args": sys.argv[1:],
    "env": {key: value for key, value in os.environ.items() if key.startswith("VOMGR_")},
    "pid": os.getpid(),
}
record_path.write_text(json.dumps(payload))
"""
    )
    executable_path.chmod(0o755)


@pytest.fixture()
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provide an isolated HOME directory for hook installation."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


@pytest.fixture()
def hook_manager(fake_home: Path) -> HookManager:
    """Hook manager configured to use the fake HOME directory."""
    return HookManager()


def test_install_hooks_when_called_then_scripts_written(
    fake_home: Path, hook_manager: HookManager
) -> None:
    """Hook installation should create the expected hook scripts under HOME."""
    hook_manager.install_hooks()

    claude_dir = fake_home / ".claude" / "hooks"
    codex_dir = fake_home / ".codex"
    gemini_dir = fake_home / ".gemini"

    claude_hook = claude_dir / "vocl-go.py"
    claude_helper = claude_dir / "vocl-new.py"
    codex_hook = codex_dir / "voco-go.py"
    codex_helper = codex_dir / "voco-new.py"
    gemini_hook = gemini_dir / "voge-go.py"

    assert claude_hook.exists(), "Claude hook must be written to ~/.claude/hooks"
    assert claude_helper.exists(), "Claude helper script must accompany vocl-go.py"
    assert codex_hook.exists(), "Codex hook must be written to ~/.codex"
    assert codex_helper.exists(), "Codex helper script must accompany voco-go.py"
    assert gemini_hook.exists(), "Gemini hook placeholder must be written to ~/.gemini"


def test_vocl_go_when_todo_items_present_then_prompt_includes_unfinished(
    fake_home: Path, hook_manager: HookManager
) -> None:
    """Claude hook should surface TODO items in the prompt it forwards."""
    hook_manager.install_hooks()
    claude_hook = fake_home / ".claude" / "hooks" / "vocl-go.py"

    project_dir = fake_home / "project"
    project_dir.mkdir()
    (project_dir / "TODO.md").write_text("- [ ] item one\n- [x] done\n- [ ] item two\n")

    record_file = project_dir / "claude_args.json"
    fake_bin = fake_home / "bin"
    fake_bin.mkdir()
    _write_recording_stub(fake_bin / "claude")

    env = os.environ.copy()
    project_root = Path(__file__).resolve().parents[1]
    env.update(
        {
            "HOME": str(fake_home),
            "PATH": f"{fake_bin}:{env.get('PATH', '')}",
            "CLAUDE_PROJECT_DIR": str(project_dir),
            "HOOK_RECORD": str(record_file),
            FORCE_DIRECT_ENV_KEY: "1",
            "PYTHONPATH": f"{project_root}:{env.get('PYTHONPATH', '')}",
        }
    )

    payload = json.dumps({"session_id": "sess-123", "transcript_path": "transcript.json"})
    subprocess.run(
        [sys.executable, str(claude_hook)],
        input=payload,
        text=True,
        check=True,
        env=env,
        cwd=str(fake_home),
    )

    config_path = claude_hook.parent / "vocl-new.json"
    assert config_path.exists(), "Claude hook must persist launcher configuration"
    config = json.loads(config_path.read_text())

    assert record_file.exists(), "Claude stub should be invoked and write recorded arguments"
    recorded = json.loads(record_file.read_text())
    args = recorded["args"]
    assert Path(args[0]).name == "codex", "Continuation should invoke codex CLI by default"
    assert any(arg.startswith("--cd=") for arg in args), (
        "Codex command should include working directory"
    )
    prompt_value = recorded["env"].get("VOMGR_PROMPT", "")
    assert "item one" in prompt_value, "Prompt should include unfinished TODO entries"
    assert recorded["env"].get("VOMGR_TARGET_TOOL") == "codex", "Target metadata must reach helper"
    assert recorded["env"].get("VOMGR_NOTIFICATION_MESSAGE") == "Continuing on codex"
    assert recorded["env"].get("VOMGR_NOTIFICATION_SOUND") == "success"
    assert config.get("command"), "Config file must contain the command list"


def test_voco_go_when_context_string_then_uses_context_directory(
    fake_home: Path, hook_manager: HookManager, tmp_path: Path
) -> None:
    """Codex hook must interpret JSON context strings to locate the project directory."""
    hook_manager.install_hooks()
    codex_hook = fake_home / ".codex" / "voco-go.py"

    project_dir = fake_home / "codex_project"
    project_dir.mkdir()
    (project_dir / "TODO.md").write_text("- [ ] codex task\n")

    record_file = project_dir / "codex_args.json"
    fake_bin = fake_home / "bin"
    fake_bin.mkdir(exist_ok=True)
    _write_recording_stub(fake_bin / "codex")

    env = os.environ.copy()
    project_root = Path(__file__).resolve().parents[1]
    env.update(
        {
            "HOME": str(fake_home),
            "PATH": f"{fake_bin}:{env.get('PATH', '')}",
            "HOOK_RECORD": str(record_file),
            "PWD": str(tmp_path),
            FORCE_DIRECT_ENV_KEY: "1",
            "PYTHONPATH": f"{project_root}:{env.get('PYTHONPATH', '')}",
        }
    )

    context_payload = {"context": json.dumps({"cwd": str(project_dir)})}
    subprocess.run(
        [sys.executable, str(codex_hook)],
        input=json.dumps(context_payload),
        text=True,
        check=True,
        env=env,
        cwd=str(tmp_path),
    )

    config_path = codex_hook.parent / "voco-new.json"
    assert config_path.exists(), "Codex hook must persist launcher configuration"
    config = json.loads(config_path.read_text())

    assert record_file.exists(), "Codex stub should be invoked and record arguments"
    recorded = json.loads(record_file.read_text())
    args = recorded["args"]
    assert Path(args[0]).name == "claude", (
        "Codex continuation should pivot back to Claude by default"
    )
    assert "--prompt" in args, "Claude command should include prompt flag"
    prompt_value = args[args.index("--prompt") + 1]
    assert "codex task" in prompt_value, "Prompt should convey TODO items"
    assert recorded["env"].get("VOMGR_TARGET_TOOL") == "claude"
    assert recorded["env"].get("VOMGR_NOTIFICATION_MESSAGE") == "Continuing on claude"
    assert config.get("command"), "Config file must contain the command list"


def test_vocl_go_when_continuation_disabled_then_no_launch(
    fake_home: Path, hook_manager: HookManager
) -> None:
    """Claude hook must exit quietly when continuation is disabled."""
    settings = UserSettings.default()
    settings.continuations["claude"].enabled = False
    save_user_settings(settings, home=fake_home)

    hook_manager.install_hooks()
    claude_hook = fake_home / ".claude" / "hooks" / "vocl-go.py"
    record_file = fake_home / "no_launch.json"
    fake_bin = fake_home / "bin"
    fake_bin.mkdir()
    _write_recording_stub(fake_bin / "codex")

    env = os.environ.copy()
    project_root = Path(__file__).resolve().parents[1]
    env.update(
        {
            "HOME": str(fake_home),
            "PATH": f"{fake_bin}:{env.get('PATH', '')}",
            "HOOK_RECORD": str(record_file),
            FORCE_DIRECT_ENV_KEY: "1",
            "PYTHONPATH": f"{project_root}:{env.get('PYTHONPATH', '')}",
        }
    )

    subprocess.run(
        [sys.executable, str(claude_hook)],
        input=json.dumps({}),
        text=True,
        check=True,
        env=env,
        cwd=str(fake_home),
    )

    assert not record_file.exists(), "No continuation should be launched when disabled"
    config_path = claude_hook.parent / "vocl-new.json"
    assert not config_path.exists(), "Config should not be produced when continuation disabled"


def test_vocl_new_helper_when_run_then_session_state_rotated(
    fake_home: Path, hook_manager: HookManager
) -> None:
    """Helper execution should record the spawned session state."""
    settings = UserSettings.default()
    settings.kill_old_sessions = False
    save_user_settings(settings, home=fake_home)

    state_dir = fake_home / ".vexy-overnight"
    manager = SessionStateManager(state_dir)
    manager.write_session("claude", 12345, str(fake_home))

    hook_manager.install_hooks()
    claude_hook = fake_home / ".claude" / "hooks" / "vocl-go.py"

    project_dir = fake_home / "project"
    project_dir.mkdir()
    (project_dir / "TODO.md").write_text("- [ ] check rotation\n")

    record_file = project_dir / "codex_args.json"
    fake_bin = fake_home / "bin"
    fake_bin.mkdir(exist_ok=True)
    _write_recording_stub(fake_bin / "codex")

    env = os.environ.copy()
    project_root = Path(__file__).resolve().parents[1]
    env.update(
        {
            "HOME": str(fake_home),
            "PATH": f"{fake_bin}:{env.get('PATH', '')}",
            "CLAUDE_PROJECT_DIR": str(project_dir),
            "HOOK_RECORD": str(record_file),
            FORCE_DIRECT_ENV_KEY: "1",
            "PYTHONPATH": f"{project_root}:{env.get('PYTHONPATH', '')}",
        }
    )

    subprocess.run(
        [sys.executable, str(claude_hook)],
        input=json.dumps({}),
        text=True,
        check=True,
        env=env,
        cwd=str(fake_home),
    )

    recorded = json.loads(record_file.read_text())
    state_file = state_dir / "session_state.json"
    assert state_file.exists(), "Session state file must be written"
    session_payload = json.loads(state_file.read_text())
    assert session_payload["tool"] == "codex", "Target tool should be recorded"
    assert session_payload["cwd"] == str(project_dir)
    assert session_payload["pid"] == recorded["pid"], "PID must match launched process"
