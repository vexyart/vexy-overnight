#!/usr/bin/env python3
# this_file: src/vexy_overnight/hooks_tpl/voco_go.py
"""Template for Codex continuation hook that spawns a fresh session."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from vexy_overnight.hook_runtime import (
    build_prompt,
    build_target_command,
    continuation_enabled,
    load_settings,
    prepare_env_updates,
    resolve_target,
    spawn_helper,
    write_config,
)

SOURCE_TOOL = "{source_tool}"
HELPER_NAME = "{new_script_name}"
CONFIG_FILENAME = "{config_filename}"
SESSIONS_RELATIVE = "{sessions_relative}"
FORCE_DIRECT_ENV_KEY = "{force_direct_env_key}"
TERMINAL_ENV_KEY = "{terminal_env_key}"
PROMPT_FALLBACK = "Continue working on the current task"


def read_payload() -> Dict[str, Any]:
    """Return JSON payload supplied on stdin, or an empty mapping."""
    try:
        raw = sys.stdin.read()
    except Exception:
        return dict()
    if not raw.strip():
        return dict()
    try:
        return json.loads(raw)
    except Exception:
        return dict()


def _ensure_path(value: Optional[str]) -> Optional[Path]:
    if not value:
        return None
    path = Path(value).expanduser()
    if path.exists():
        return path
    return None


def _context_to_mapping(context: Any) -> Dict[str, Any]:
    if isinstance(context, dict):
        return context
    if isinstance(context, str):
        stripped = context.strip()
        if not stripped:
            return dict()
        try:
            loaded = json.loads(stripped)
            if isinstance(loaded, dict):
                return loaded
        except Exception:
            path = _ensure_path(stripped)
            if path is not None:
                return dict(cwd=str(path))
    return dict()


def _latest_session_directory() -> Optional[Path]:
    sessions_root = Path.home() / SESSIONS_RELATIVE
    if not sessions_root.exists():
        return None
    candidates: list[tuple[float, Path]] = []
    for stream in sessions_root.glob("*.jsonl"):
        try:
            candidates.append((stream.stat().st_mtime, stream))
        except Exception:
            continue
    candidates.sort(reverse=True, key=lambda item: item[0])
    for _, stream in candidates:
        try:
            for line in stream.read_text(encoding="utf-8").splitlines():
                try:
                    record = json.loads(line)
                except Exception:
                    continue
                cwd = record.get("cwd")
                path = _ensure_path(str(cwd)) if isinstance(cwd, (str, os.PathLike)) else None
                if path is not None:
                    return path
        except Exception:
            continue
    return None


def determine_project_dir(payload: Dict[str, Any]) -> Path:
    """Infer Codex working directory from payload or session logs."""
    context = _context_to_mapping(payload.get("context"))
    candidate = context.get("cwd") or context.get("working_directory")
    project = _ensure_path(candidate if isinstance(candidate, str) else None)
    if project is not None:
        return project

    fallback = payload.get("cwd")
    project = _ensure_path(fallback if isinstance(fallback, str) else None)
    if project is not None:
        return project

    session_dir = _latest_session_directory()
    if session_dir is not None:
        return session_dir

    env_pwd = os.environ.get("PWD")
    project = _ensure_path(env_pwd)
    if project is not None:
        return project

    return Path(os.getcwd())


def _remove_stale_config(script_dir: Path) -> None:
    config_path = script_dir / CONFIG_FILENAME
    if config_path.exists():
        try:
            config_path.unlink()
        except Exception:
            pass


def main() -> None:
    """Entry point for the Codex continuation hook."""
    payload = read_payload()
    project_dir = determine_project_dir(payload)
    settings = load_settings()
    if not continuation_enabled(settings, SOURCE_TOOL):
        _remove_stale_config(Path(__file__).resolve().parent)
        return

    target_tool = resolve_target(settings, SOURCE_TOOL)
    prompt = build_prompt(settings, SOURCE_TOOL, target_tool, project_dir, PROMPT_FALLBACK)
    command = build_target_command(target_tool, project_dir, prompt)
    env_updates = prepare_env_updates(settings, SOURCE_TOOL, target_tool, prompt, project_dir)

    script_dir = Path(__file__).resolve().parent
    config_path = script_dir / CONFIG_FILENAME
    write_config(config_path, command, project_dir, env_updates)

    helper_script = script_dir / HELPER_NAME
    if not helper_script.exists():
        sys.stderr.write("Helper script " + HELPER_NAME + " is missing. Re-run vomgr install.\n")
        sys.exit(1)

    force_direct = os.environ.get(FORCE_DIRECT_ENV_KEY) == "1"
    spawn_helper(
        helper_script,
        project_dir,
        settings,
        target_tool,
        terminal_env_key=TERMINAL_ENV_KEY,
        force_direct=force_direct,
    )


if __name__ == "__main__":
    main()
