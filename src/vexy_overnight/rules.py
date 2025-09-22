#!/usr/bin/env python3
# this_file: src/vexy_overnight/rules.py
"""Synchronise and edit shared instruction files across CLI tools."""

import os
import subprocess
from pathlib import Path

from loguru import logger


class RulesManager:
    """Coordinate instruction file discovery and synchronisation tasks.

    The manager operates on either the current working directory or the
    user's global configuration directories, depending on ``global_mode``.
    It provides helper methods invoked by CLI commands for syncing, appending,
    searching, and replacing text across instruction files such as
    ``CLAUDE.md`` or ``.cursorrules``.
    """

    INSTRUCTION_FILES = [
        "CLAUDE.md",
        "AGENTS.md",
        "GEMINI.md",
        "QWEN.md",
        "LLXPRT.md",
        ".cursorrules",
    ]

    def __init__(self, global_mode: bool = False):
        """Create a manager with the desired search scope.

        Args:
            global_mode: When ``True`` operate on configuration directories in
                the user's home folder; otherwise operate on the current
                working directory only.
        """
        self.global_mode = global_mode

        if global_mode:
            self.search_paths = [
                Path.home() / ".claude",
                Path.home() / ".codex",
                Path.home() / ".gemini",
                Path.home() / ".qwen",
                Path.home() / ".llxprt",
                Path.home() / ".cursor",
            ]
        else:
            self.search_paths = [Path.cwd()]

    def find_instruction_files(self) -> dict[str, list[Path]]:
        """Discover instruction files within the configured search paths.

        Returns:
            dict[str, list[Path]]: Mapping of file names to the paths discovered
            for each name.
        """
        files_by_name = {}

        for filename in self.INSTRUCTION_FILES:
            files_by_name[filename] = []

            for search_path in self.search_paths:
                if search_path.exists():
                    # Use fd if available for faster search
                    if self._command_exists("fd"):
                        result = subprocess.run(
                            ["fd", "-t", "f", filename, str(search_path)],
                            capture_output=True,
                            text=True,
                        )
                        if result.returncode == 0:
                            for line in result.stdout.strip().split("\n"):
                                if line:
                                    files_by_name[filename].append(Path(line))
                    else:
                        # Fallback to pathlib
                        for file_path in search_path.rglob(filename):
                            files_by_name[filename].append(file_path)

        return files_by_name

    def _command_exists(self, cmd: str) -> bool:
        """Return whether ``cmd`` resolves via ``which``.

        Args:
            cmd: Command name to probe for availability.

        Returns:
            bool: ``True`` if the tool exists on the current ``PATH``.
        """
        result = subprocess.run(["which", cmd], capture_output=True)
        return result.returncode == 0

    def sync_files(self):
        """Synchronise instruction files by linking them to a common parent."""
        files_by_name = self.find_instruction_files()

        for filename, file_paths in files_by_name.items():
            if len(file_paths) < 2:
                continue

            # Find the most recent non-empty file as parent
            parent_file = self._find_parent_file(file_paths)
            if not parent_file:
                continue

            logger.debug(f"Syncing {filename} with parent: {parent_file}")

            # Link all other files to parent
            for file_path in file_paths:
                if file_path != parent_file:
                    try:
                        # Remove existing file
                        file_path.unlink()
                        # Create hard link
                        os.link(parent_file, file_path)
                        logger.debug(f"Linked {file_path} to {parent_file}")
                    except Exception:
                        # If hard link fails, try symbolic link
                        try:
                            file_path.unlink()
                            file_path.symlink_to(parent_file)
                            logger.debug(f"Symlinked {file_path} to {parent_file}")
                        except Exception as e2:
                            logger.warning(f"Failed to link {file_path}: {e2}")

    def _find_parent_file(self, file_paths: list[Path]) -> Path | None:
        """Select the most recent non-empty file to use as the canonical copy.

        Args:
            file_paths: Candidate files discovered during syncing.

        Returns:
            Path | None: The chosen parent file or ``None`` if no suitable file
            exists.
        """
        valid_files = []

        for file_path in file_paths:
            if file_path.exists() and file_path.stat().st_size > 0:
                valid_files.append(file_path)

        if not valid_files:
            return None

        # Sort by modification time, most recent first
        valid_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return valid_files[0]

    def append_to_files(self, text: str):
        """Append ``text`` to the canonical copy of each instruction file.

        Args:
            text: Content to append, typically newline-delimited instructions.
        """
        files_by_name = self.find_instruction_files()

        for filename, file_paths in files_by_name.items():
            # Find parent file
            parent_file = self._find_parent_file(file_paths)
            if parent_file:
                # Append to parent (will affect all linked files)
                with open(parent_file, "a") as f:
                    f.write(f"\n{text}\n")
                logger.info(f"Appended text to {filename}")

    def search_files(self, pattern: str) -> dict[str, list[str]]:
        """Search for ``pattern`` in each instruction file.

        Args:
            pattern: Substring to look for in the file contents.

        Returns:
            dict[str, list[str]]: Mapping of file name to matching lines with
            location metadata.
        """
        results = {}
        files_by_name = self.find_instruction_files()

        for filename, file_paths in files_by_name.items():
            matches = []
            seen_inodes = set()

            for file_path in file_paths:
                # Skip if we've already seen this inode (hard linked)
                inode = file_path.stat().st_ino
                if inode in seen_inodes:
                    continue
                seen_inodes.add(inode)

                try:
                    with open(file_path) as f:
                        for line_num, line in enumerate(f, 1):
                            if pattern in line:
                                matches.append(f"{file_path}:{line_num}: {line.strip()}")
                except Exception as e:
                    logger.debug(f"Error searching {file_path}: {e}")

            if matches:
                results[filename] = matches

        return results

    def replace_in_files(self, search_text: str, replace_text: str):
        """Replace ``search_text`` with ``replace_text`` in instruction files.

        Args:
            search_text: Substring to be replaced.
            replace_text: Replacement string written back to files.
        """
        files_by_name = self.find_instruction_files()
        seen_inodes = set()

        for _filename, file_paths in files_by_name.items():
            for file_path in file_paths:
                # Skip if we've already processed this inode
                inode = file_path.stat().st_ino
                if inode in seen_inodes:
                    continue
                seen_inodes.add(inode)

                try:
                    with open(file_path) as f:
                        content = f.read()

                    if search_text in content:
                        updated_content = content.replace(search_text, replace_text)
                        with open(file_path, "w") as f:
                            f.write(updated_content)
                        logger.info(f"Replaced text in {file_path}")
                except Exception as e:
                    logger.warning(f"Error replacing in {file_path}: {e}")
