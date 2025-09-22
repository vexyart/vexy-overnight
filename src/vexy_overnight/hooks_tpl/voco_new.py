#!/usr/bin/env python3
# this_file: src/vexy_overnight/hooks_tpl/voco_new.py
"""Helper script executed by Codex continuation hooks to resume work."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from vexy_overnight.hook_runtime import launch_from_config

CONFIG_FILENAME = "{config_filename}"


def load_config(script_dir: Path) -> dict[str, object]:
    """Read the helper configuration produced by ``voco-go``.

    Args:
        script_dir: Directory containing the JSON configuration file.

    Returns:
        dict[str, object]: Parsed configuration or an empty dict when the
        payload is missing or malformed.
    """
    config_path = script_dir / CONFIG_FILENAME
    if not config_path.exists():
        sys.stderr.write("Missing config file " + CONFIG_FILENAME + ".\n")
        return dict()
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except Exception as error:
        sys.stderr.write("Unable to parse config file: " + str(error) + "\n")
        return dict()


def main() -> None:
    """Entry point that loads configuration and launches the continuation."""
    script_dir = Path(__file__).resolve().parent
    config = load_config(script_dir)
    if not config:
        return
    launch_from_config(config)


if __name__ == "__main__":
    main()
