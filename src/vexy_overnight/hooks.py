#!/usr/bin/env python3
# this_file: src/vexy_overnight/hooks.py
"""Manage the lifecycle of continuation hook scripts.

The :class:`HookManager` renders packaged templates into the user's home
directory, creating helper scripts for Claude, Codex, and Gemini.  Hooks are
idempotent and safe to re-run because installation overwrites existing files
while uninstallation removes all generated artefacts.
"""

from __future__ import annotations

import importlib.resources as resources
from pathlib import Path

from loguru import logger

TEMPLATE_PACKAGE = "vexy_overnight.hooks_tpl"
TERMINAL_ENV_KEY = "VOMGR_TERMINAL_APP"
FORCE_DIRECT_ENV_KEY = "VOMGR_HOOK_FORCE_DIRECT"


class HookManager:
    """Install and remove continuation helper scripts for supported CLIs.

    The manager expands Jinja-less string templates shipped in
    ``vexy_overnight.hooks_tpl``.  Each installation pass writes a launcher
    (``*-go.py``), a helper script (``*-new.py``), and any accompanying JSON
    configuration.
    """

    def __init__(self) -> None:
        """Derive canonical hook paths under the user's home directory."""
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
        """Render and install hook scripts for every supported CLI."""
        self._install_claude_hook()
        self._install_codex_hook()
        self._install_gemini_hook()

    def uninstall_hooks(self) -> None:
        """Remove all generated hook scripts and helper artefacts."""
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
        """Render and write Claude-specific hook and helper scripts."""
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
        """Render and write Codex hook and helper scripts."""
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
        """Render the placeholder Gemini hook script."""
        self.gemini_dir.mkdir(parents=True, exist_ok=True)
        self._write_template("voge_go.py", self.gemini_hook_path, {})
        logger.debug("Installed Gemini placeholder hook at {}", self.gemini_hook_path)

    def _write_template(
        self, template_name: str, destination: Path, context: dict[str, str]
    ) -> None:
        """Render a stored template and write the result to ``destination``.

        Args:
            template_name: Name of the file inside ``hooks_tpl``.
            destination: Path where the rendered script should be stored.
            context: Values interpolated into the template via ``str.format``.

        Raises:
            ValueError: If the provided context is missing required keys.
        """
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
        """Delete ``path`` if present and log the removal.

        Args:
            path: File path that may exist on disk.
        """
        if not path.exists():
            return
        path.unlink()
        logger.debug("Removed hook artefact {}", path)


__all__ = ["HookManager"]
