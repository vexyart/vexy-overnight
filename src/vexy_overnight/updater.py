#!/usr/bin/env python3
# this_file: src/vexy_overnight/updater.py
"""Update management for vomgr."""

import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger


class UpdateManager:
    """Manages updates for CLI tools and vexy-overnight package."""

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
        """Initialize update manager."""
        self.update_log = Path.home() / ".vexy-overnight" / "update.log"
        self.update_log.parent.mkdir(parents=True, exist_ok=True)

    def check_versions(self) -> dict[str, dict[str, str]]:
        """Check current and available versions for all tools."""
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
        """Get version of a command-line tool."""
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
        """Get available brew package version."""
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
        """Get available PyPI package version."""
        try:
            import urllib.request
            import json

            url = f"https://pypi.org/pypi/{package}/json"
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read())
                return data.get("info", {}).get("version", "latest")
        except Exception as e:
            logger.debug(f"Failed to get PyPI version for {package}: {e}")

        return "latest"

    def update_cli_tools(self, dry_run: bool = False, skip: list[str] = None):
        """Update all CLI tools."""
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
        """Update vexy-overnight package."""
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
        """Log update operation to file."""
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.update_log, "a") as f:
            f.write(f"[{timestamp}] {message}\n")