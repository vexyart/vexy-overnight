#!/usr/bin/env python3
# this_file: src/vexy_overnight/updater.py
"""Update CLI toolchain dependencies used by the Vexy Overnight Manager."""

import subprocess
import sys
from pathlib import Path

from loguru import logger


class UpdateManager:
    """Coordinate checking and updating of CLI tools and this package."""

    NPM_PACKAGES = {
        "claude": "@anthropic-ai/claude-code@latest",
        "gemini": "@google/gemini-cli@nightly",
        "llxprt": "@vybestack/llxprt-code@nightly",
        "qwen": "@qwen-code/qwen-code@nightly",
        "terragon": "@terragon-labs/cli@latest",
        "justevery": "@just-every/code@latest",
    }

    BREW_PACKAGES = ["codex"]

    def __init__(self):
        """Create a manager and ensure the update log directory exists."""
        self.update_log = Path.home() / ".vexy-overnight" / "update.log"
        self.update_log.parent.mkdir(parents=True, exist_ok=True)

    def check_versions(self) -> dict[str, dict[str, str]]:
        """Return observed current versions and nominal available versions.

        Returns:
            dict[str, dict[str, str]]: Mapping of tool name to ``current`` and
            ``available`` version strings.
        """
        versions = {}

        # Check Claude
        versions["claude"] = {
            "current": self._get_version("claude", "--version"),
            "available": "latest",
        }

        # Check Codex
        versions["codex"] = {
            "current": self._get_version("codex", "--version"),
            "available": self._get_brew_version("codex"),
        }

        # Check Gemini
        versions["gemini"] = {
            "current": self._get_version("gemini", "--version"),
            "available": "nightly",
        }

        # Check vexy-overnight
        try:
            from . import __version__

            versions["vexy-overnight"] = {
                "current": __version__.__version__,
                "available": self._get_pypi_version("vexy-overnight"),
            }
        except Exception:
            versions["vexy-overnight"] = {
                "current": "unknown",
                "available": "unknown",
            }

        return versions

    def _get_version(self, cmd: str, flag: str) -> str:
        """Return the version string produced by ``cmd flag``.

        Args:
            cmd: Command name to execute.
            flag: Flag used to request version output (e.g. ``--version``).

        Returns:
            str: Parsed semantic version or a fallback description.
        """
        try:
            result = subprocess.run(
                [cmd, flag],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                # Parse version from output
                output = result.stdout.strip()
                # Look for version patterns
                import re

                version_match = re.search(r"(\d+\.\d+\.\d+)", output)
                if version_match:
                    return version_match.group(1)
                return output.split()[0] if output else "unknown"
        except Exception as e:
            logger.debug(f"Failed to get version for {cmd}: {e}")

        return "not installed"

    def _get_brew_version(self, package: str) -> str:
        """Return the latest version reported by Homebrew for ``package``.

        Args:
            package: Homebrew formula name.

        Returns:
            str: Version string or ``"latest"`` when unavailable.
        """
        try:
            result = subprocess.run(
                ["brew", "info", "--json=v2", package],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                import json

                info = json.loads(result.stdout)
                if "formulae" in info and info["formulae"]:
                    return info["formulae"][0].get("version", "latest")
        except Exception as e:
            logger.debug(f"Failed to get brew version for {package}: {e}")

        return "latest"

    def _get_pypi_version(self, package: str) -> str:
        """Return the latest version number published on PyPI for ``package``.

        Args:
            package: PyPI package name.

        Returns:
            str: Version string or ``"latest"`` when unavailable.
        """
        try:
            import json
            import urllib.request

            url = f"https://pypi.org/pypi/{package}/json"
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read())
                return data.get("info", {}).get("version", "latest")
        except Exception as e:
            logger.debug(f"Failed to get PyPI version for {package}: {e}")

        return "latest"

    def update_cli_tools(self, dry_run: bool = False, skip: list[str] | None = None):
        """Update CLI tools managed by vomgr.

        Args:
            dry_run: When ``True`` log intended commands without executing.
            skip: Optional list of tool names that should not be updated.
        """
        skip = skip or []

        # Log current versions
        versions_before = self.check_versions()
        self._log_update(f"Starting CLI tools update. Versions before: {versions_before}")

        # Update NPM packages
        for tool, package in self.NPM_PACKAGES.items():
            if tool in skip:
                logger.info(f"Skipping {tool}")
                continue

            logger.info(f"Updating {tool}...")

            if dry_run:
                logger.info(f"[DRY RUN] Would run: npm install -g {package}")
            else:
                try:
                    result = subprocess.run(
                        ["npm", "install", "-g", package],
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode == 0:
                        logger.info(f"✓ Updated {tool}")
                    else:
                        logger.warning(f"Failed to update {tool}: {result.stderr}")
                except Exception as e:
                    logger.error(f"Error updating {tool}: {e}")

        # Update Brew packages
        for package in self.BREW_PACKAGES:
            if package in skip:
                logger.info(f"Skipping {package}")
                continue

            logger.info(f"Updating {package}...")

            if dry_run:
                logger.info(f"[DRY RUN] Would run: brew upgrade {package}")
            else:
                try:
                    # First update brew
                    subprocess.run(["brew", "update"], capture_output=True)

                    # Then upgrade package
                    result = subprocess.run(
                        ["brew", "upgrade", package],
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode == 0 or "already installed" in result.stderr:
                        logger.info(f"✓ Updated {package}")
                    else:
                        logger.warning(f"Failed to update {package}: {result.stderr}")
                except Exception as e:
                    logger.error(f"Error updating {package}: {e}")

        # Log new versions
        if not dry_run:
            versions_after = self.check_versions()
            self._log_update(f"CLI tools update complete. Versions after: {versions_after}")

    def update_self(self, dry_run: bool = False):
        """Update the ``vexy-overnight`` Python package itself.

        Args:
            dry_run: When ``True`` only log the commands that would run.
        """
        logger.info("Updating vexy-overnight package...")

        if dry_run:
            logger.info("[DRY RUN] Would run: uv pip install --upgrade vexy-overnight")
            logger.info("[DRY RUN] Or: pip install --upgrade vexy-overnight")
        else:
            # Try uv first, then pip
            try:
                # Check if uv is available
                result = subprocess.run(["which", "uv"], capture_output=True)
                if result.returncode == 0:
                    result = subprocess.run(
                        ["uv", "pip", "install", "--upgrade", "vexy-overnight"],
                        capture_output=True,
                        text=True,
                    )
                else:
                    result = subprocess.run(
                        [sys.executable, "-m", "pip", "install", "--upgrade", "vexy-overnight"],
                        capture_output=True,
                        text=True,
                    )

                if result.returncode == 0:
                    logger.info("✓ Updated vexy-overnight package")
                    self._log_update("vexy-overnight package updated successfully")
                else:
                    logger.warning(f"Failed to update vexy-overnight: {result.stderr}")
            except Exception as e:
                logger.error(f"Error updating vexy-overnight: {e}")

    def _log_update(self, message: str):
        """Append ``message`` to the persistent update log with a timestamp.

        Args:
            message: Human-readable update summary to persist.
        """
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.update_log, "a") as f:
            f.write(f"[{timestamp}] {message}\n")
