#!/usr/bin/env python3
# this_file: src/vexy_overnight/hooks.py
"""Template-driven continuation hook management for vomgr."""

from __future__ import annotations

import importlib.resources as resources
from pathlib import Path

from loguru import logger

TEMPLATE_PACKAGE = "vexy_overnight.hooks_tpl"
TERMINAL_ENV_KEY = "VOMGR_TERMINAL_APP"
FORCE_DIRECT_ENV_KEY = "VOMGR_HOOK_FORCE_DIRECT"


class HookManager:
    """Manage installation and removal of continuation hook scripts."""

    def __init__(self) -> None:
        """Initialise hook paths rooted at the user's HOME directory."""
        home = Path.home()
        self.claude_dir = home / ".claude" / "hooks"
        self.claude_hook_path = self.claude_dir / "vocl-go.py"
        self.claude_helper_path = self.claude_dir / "vocl-new.py"
        self.claude_config_name = "vocl-new.json"

        self.codex_dir = home / ".codex"
        self.codex_hook_path = self.codex_dir / "voco-go.py"
        self.codex_helper_path = self.codex_dir / "voco-new.py"
        self.codex_config_name = "voco-new.json"

        self.gemini_dir = home / ".gemini"
        self.gemini_hook_path = self.gemini_dir / "voge-go.py"

    def install_hooks(self) -> None:
        """Install continuation hook scripts for all supported CLIs."""
        self._install_claude_hook()
        self._install_codex_hook()
        self._install_gemini_hook()

    def uninstall_hooks(self) -> None:
        """Remove hook scripts and companions for all tools."""
        for path in (
            self.claude_hook_path,
            self.claude_helper_path,
            self.claude_dir / self.claude_config_name,
            self.codex_hook_path,
            self.codex_helper_path,
            self.codex_dir / self.codex_config_name,
            self.gemini_hook_path,
        ):
            self._remove_file(path)

    def _install_claude_hook(self) -> None:
        """Install Claude continuation hook using packaged templates."""
        self.claude_dir.mkdir(parents=True, exist_ok=True)
        context = dict(
            source_tool="claude",
            cli_executable="claude",
            new_script_name=self.claude_helper_path.name,
            config_filename=self.claude_config_name,
            env_project_key="CLAUDE_PROJECT_DIR",
            prompt_fallback="Continue working on the current task",
            terminal_env_key=TERMINAL_ENV_KEY,
            force_direct_env_key=FORCE_DIRECT_ENV_KEY,
        )
        self._write_template("vocl_go.py", self.claude_hook_path, context)
        self._write_template(
            "vocl_new.py",
            self.claude_helper_path,
            dict(config_filename=self.claude_config_name),
        )
        logger.debug("Installed Claude continuation hook at {}", self.claude_hook_path)

    def _install_codex_hook(self) -> None:
        """Install Codex continuation hook using packaged templates."""
        self.codex_dir.mkdir(parents=True, exist_ok=True)
        context = dict(
            source_tool="codex",
            cli_executable="codex",
            new_script_name=self.codex_helper_path.name,
            config_filename=self.codex_config_name,
            sessions_relative=".codex/sessions",
            terminal_env_key=TERMINAL_ENV_KEY,
            force_direct_env_key=FORCE_DIRECT_ENV_KEY,
        )
        self._write_template("voco_go.py", self.codex_hook_path, context)
        self._write_template(
            "voco_new.py",
            self.codex_helper_path,
            dict(config_filename=self.codex_config_name),
        )
        logger.debug("Installed Codex continuation hook at {}", self.codex_hook_path)

    def _install_gemini_hook(self) -> None:
        """Install Gemini placeholder hook."""
        self.gemini_dir.mkdir(parents=True, exist_ok=True)
        self._write_template("voge_go.py", self.gemini_hook_path, {})
        logger.debug("Installed Gemini placeholder hook at {}", self.gemini_hook_path)

    def _write_template(
        self, template_name: str, destination: Path, context: dict[str, str]
    ) -> None:
        """Render a stored template and write it to destination."""
        template = resources.files(TEMPLATE_PACKAGE).joinpath(template_name)
        content = template.read_text(encoding="utf-8")
        try:
            rendered = content.format(**context)
        except KeyError as error:
            raise ValueError(f"Missing template context value: {error}") from error
        destination.write_text(rendered, encoding="utf-8")
        destination.chmod(0o755)

    @staticmethod
    def _remove_file(path: Path) -> None:
        """Delete path if it exists, logging the outcome."""
        if not path.exists():
            return
        path.unlink()
        logger.debug("Removed hook artefact {}", path)


__all__ = ["HookManager"]
