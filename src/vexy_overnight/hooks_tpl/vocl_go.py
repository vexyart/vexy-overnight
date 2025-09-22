#!/usr/bin/env python3
# this_file: src/vexy_overnight/hooks_tpl/vocl_go.py
"""Template for Claude continuation hook that spawns a fresh session."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

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
ENV_PROJECT_KEY = "{env_project_key}"
PROMPT_FALLBACK = "{prompt_fallback}"
TERMINAL_ENV_KEY = "{terminal_env_key}"
FORCE_DIRECT_ENV_KEY = "{force_direct_env_key}"


def read_payload() -> dict[str, Any]:
    """Read JSON payload supplied on stdin, returning an empty dict on failure."""
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


def determine_project_dir(payload: dict[str, Any]) -> Path:
    """Select the project directory from env, payload, or current working directory."""
    env_value = os.environ.get(ENV_PROJECT_KEY)
    if env_value:
        path = Path(env_value).expanduser()
        if path.exists():
            return path

    candidate = payload.get("project_dir") or payload.get("cwd")
    if isinstance(candidate, str) and candidate.strip():
        path = Path(candidate.strip()).expanduser()
        if path.exists():
            return path

    fallback = os.environ.get("PWD", os.getcwd())
    return Path(fallback)


def _remove_stale_config(script_dir: Path) -> None:
    """Drop a stale config file when continuation is disabled."""
    config_path = script_dir / CONFIG_FILENAME
    if config_path.exists():
        try:
            config_path.unlink()
        except Exception:
            pass


def main() -> None:
    """Entry point for the Claude continuation hook."""
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
