#!/usr/bin/env python3
# this_file: src/vexy_overnight/launchers.py
"""Fire-facing launch helpers for Claude, Codex, and Gemini CLIs."""

import os
import subprocess
import sys
from pathlib import Path

from loguru import logger


class LauncherManager:
    """Resolve CLI binaries and expose convenience launch methods.

    The manager keeps per-tool launch logic isolated so both CLI commands and
    tests can invoke the same code paths.  Each launch method performs minimal
    argument translation and delegates to :mod:`subprocess`.
    """

    def __init__(self):
        """Look up command paths once so subsequent launches are cheap."""
        self.claude_cmd = self._find_command("claude")
        self.codex_cmd = self._find_command("codex")
        self.gemini_cmd = self._find_command("gemini")

    def _find_command(self, cmd: str) -> str | None:
        """Locate ``cmd`` in ``PATH`` or known installation directories.

        Args:
            cmd: Command name to resolve.

        Returns:
            str | None: Absolute path to the executable, or ``None`` if not
            found.
        """
        result = subprocess.run(["which", cmd], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()

        # Check common locations
        common_paths = [
            f"/usr/local/bin/{cmd}",
            f"{Path.home()}/.local/bin/{cmd}",
            f"/opt/homebrew/bin/{cmd}",
        ]

        for path in common_paths:
            if Path(path).exists():
                return path

        return None

    def launch_claude(
        self,
        cwd: Path | None = None,
        model: str | None = None,
        prompt: str | None = None,
        **kwargs,
    ):
        """Launch the Claude CLI with continuation-friendly defaults.

        Args:
            cwd: Optional working directory for the launched process.
            model: Optional Claude model identifier; defaults to Sonnet 4.
            prompt: Optional prompt passed to Claude using ``--prompt``.
            **kwargs: Ignored extras to keep the signature Fire-friendly.
        """
        if not self.claude_cmd:
            logger.error(
                "Claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code"
            )
            sys.exit(1)

        cmd = [self.claude_cmd, "--dangerously-skip-permissions"]

        if model:
            cmd.extend(["--model", model])
        else:
            # Default to claude-sonnet-4
            cmd.extend(["--model", "claude-sonnet-4"])

        if prompt:
            cmd.extend(["--prompt", prompt])

        # Set working directory
        if cwd:
            os.chdir(cwd)

        logger.info(f"Launching Claude: {' '.join(cmd)}")

        try:
            subprocess.run(cmd)
        except Exception as e:
            logger.error(f"Failed to launch Claude: {e}")
            sys.exit(1)

    def launch_codex(
        self,
        cwd: Path | None = None,
        profile: str | None = None,
        exec_mode: bool = False,
        prompt: str | None = None,
        **kwargs,
    ):
        """Launch the Codex CLI with sensible defaults for continuation.

        Args:
            cwd: Optional working directory for the process.
            profile: Optional Codex profile (``-m`` flag); defaults to ``gpt5``.
            exec_mode: When ``True`` include ``-p``/``-e`` to enable exec mode.
            prompt: Optional prompt appended as positional argument.
            **kwargs: Ignored extras to keep the signature Fire-friendly.
        """
        if not self.codex_cmd:
            logger.error("Codex CLI not found. Install with: brew install codex")
            sys.exit(1)

        cmd = [self.codex_cmd]

        # Add working directory
        if cwd:
            cmd.append(f"--cd={cwd}")

        # Add profile
        if profile:
            cmd.extend(["-m", profile])
        else:
            # Default to gpt5
            cmd.extend(["-m", "gpt5"])

        # Add exec mode flags
        if exec_mode:
            cmd.extend(["-p", "-e"])

        # Add sandbox flags
        cmd.extend(
            [
                "--dangerously-bypass-approvals-and-sandbox",
                "--sandbox",
                "danger-full-access",
            ]
        )

        # Add prompt
        if prompt:
            cmd.append(prompt)

        logger.info(f"Launching Codex: {' '.join(cmd)}")

        try:
            subprocess.run(cmd)
        except Exception as e:
            logger.error(f"Failed to launch Codex: {e}")
            sys.exit(1)

    def launch_gemini(
        self,
        cwd: Path | None = None,
        prompt: str | None = None,
        **kwargs,
    ):
        """Launch the Gemini CLI with defaults matching continuation needs.

        Args:
            cwd: Optional working directory for the process.
            prompt: Optional prompt appended to the command line.
            **kwargs: Ignored extras to keep the signature Fire-friendly.
        """
        if not self.gemini_cmd:
            logger.error("Gemini CLI not found. Install with: npm install -g @google/gemini-cli")
            sys.exit(1)

        cmd = [self.gemini_cmd, "-c", "-y"]

        if prompt:
            cmd.append(prompt)

        # Set working directory
        if cwd:
            os.chdir(cwd)

        logger.info(f"Launching Gemini: {' '.join(cmd)}")

        try:
            subprocess.run(cmd)
        except Exception as e:
            logger.error(f"Failed to launch Gemini: {e}")
            sys.exit(1)


# Console script entry points
def vocl():
    """Console entry point that mirrors ``vocl`` behaviour."""
    launcher = LauncherManager()
    # Pass through all arguments
    import sys

    args = sys.argv[1:]
    prompt = " ".join(args) if args else None
    launcher.launch_claude(prompt=prompt)


def voco():
    """Console entry point that mirrors ``voco`` behaviour."""
    launcher = LauncherManager()
    import sys

    # Parse basic flags
    args = sys.argv[1:]
    profile = None
    exec_mode = False
    prompt_parts = []

    i = 0
    while i < len(args):
        if args[i] == "-m" and i + 1 < len(args):
            profile = args[i + 1]
            i += 2
        elif args[i] == "-p":
            exec_mode = True
            i += 1
        elif args[i] == "-e":
            exec_mode = True
            i += 1
        else:
            prompt_parts.append(args[i])
            i += 1

    prompt = " ".join(prompt_parts) if prompt_parts else None
    launcher.launch_codex(profile=profile, exec_mode=exec_mode, prompt=prompt)


def voge():
    """Console entry point that mirrors ``voge`` behaviour."""
    launcher = LauncherManager()
    import sys

    args = sys.argv[1:]
    prompt = " ".join(args) if args else None
    launcher.launch_gemini(prompt=prompt)
