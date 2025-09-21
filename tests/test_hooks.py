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

from vexy_overnight.hooks import HookManager


def _write_recording_stub(executable_path: Path) -> None:
    """Create a stub CLI that records received arguments to HOOK_RECORD."""
    executable_path.write_text(
        """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

record_path = Path(os.environ[\"HOOK_RECORD\"])
record_path.write_text(json.dumps(sys.argv[1:]))
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

    claude_hook = fake_home / ".claude" / "hooks" / "vocl-go.py"
    codex_hook = fake_home / ".codex" / "voco-go.py"
    gemini_hook = fake_home / ".gemini" / "voge-go.py"

    assert claude_hook.exists(), "Claude hook must be written to ~/.claude/hooks"
    assert codex_hook.exists(), "Codex hook must be written to ~/.codex"
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
    env.update(
        {
            "HOME": str(fake_home),
            "PATH": f"{fake_bin}:{env.get('PATH', '')}",
            "CLAUDE_PROJECT_DIR": str(project_dir),
            "HOOK_RECORD": str(record_file),
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

    assert record_file.exists(), "Claude stub should be invoked and write recorded arguments"
    args = json.loads(record_file.read_text())
    assert "--prompt" in args, "Claude hook must include --prompt argument"
    prompt_value = args[args.index("--prompt") + 1]
    assert "item one" in prompt_value, "Prompt should include unfinished TODO entries"


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
    env.update(
        {
            "HOME": str(fake_home),
            "PATH": f"{fake_bin}:{env.get('PATH', '')}",
            "HOOK_RECORD": str(record_file),
            "PWD": str(tmp_path),
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

    assert record_file.exists(), "Codex stub should be invoked and record arguments"
    args = json.loads(record_file.read_text())
    cd_flags = [arg for arg in args if arg.startswith("--cd=")]
    assert cd_flags == [f"--cd={project_dir}"], "Codex hook must honor cwd from JSON string context"
