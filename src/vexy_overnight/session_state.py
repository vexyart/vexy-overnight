#!/usr/bin/env python3
# this_file: src/vexy_overnight/session_state.py
"""Persist and manage session state for continuation helpers."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

VEXY_STATE_DIR = ".vexy-overnight"
SESSION_STATE_FILE = "session_state.json"


@dataclass
class SessionInfo:
    """Serialisable representation of a single CLI session."""

    tool: str  # claude, codex, or gemini
    pid: int
    start_time: str
    cwd: str

    def to_dict(self) -> dict[str, str | int]:
        """Serialise the session information into a JSON-safe dictionary.

        Returns:
            dict[str, str | int]: Mapping with primitive values ready for JSON.
        """
        return {"tool": self.tool, "pid": self.pid, "start_time": self.start_time, "cwd": self.cwd}

    @classmethod
    def from_dict(cls, data: dict[str, str | int]) -> SessionInfo:
        """Create a :class:`SessionInfo` instance from a JSON payload.

        Args:
            data: Mapping produced by :meth:`to_dict`.

        Returns:
            SessionInfo: Reconstructed dataclass instance.
        """
        return cls(
            tool=str(data["tool"]),
            pid=int(data["pid"]),
            start_time=str(data["start_time"]),
            cwd=str(data["cwd"]),
        )


class SessionStateManager:
    """Persist session metadata so continuation hooks can coordinate state."""

    def __init__(self, state_dir: Path | None = None):
        """Create a manager storing state under ``state_dir`` if provided.

        Args:
            state_dir: Optional directory override for the session file.
        """
        if state_dir is None:
            state_dir = Path.home() / VEXY_STATE_DIR
        self.state_file = state_dir / SESSION_STATE_FILE
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def read_session(self) -> SessionInfo | None:
        """Return the persisted session information, if available.

        Returns:
            SessionInfo | None: Current session metadata or ``None`` when the
            state file is missing or invalid.
        """
        if not self.state_file.exists():
            return None

        try:
            with open(self.state_file) as f:
                data = json.load(f)
                return SessionInfo.from_dict(data)
        except (json.JSONDecodeError, KeyError, ValueError):
            # Invalid or corrupted file
            return None

    def write_session(self, tool: str, pid: int, cwd: str | None = None) -> SessionInfo:
        """Persist metadata for the currently running session.

        Args:
            tool: Name of the CLI tool (``claude``, ``codex``, ``gemini``).
            pid: Process identifier for the launched CLI.
            cwd: Optional working directory override.

        Returns:
            SessionInfo: The serialised session data that was written.
        """
        session = SessionInfo(
            tool=tool, pid=pid, start_time=datetime.now().isoformat(), cwd=cwd or os.getcwd()
        )

        with open(self.state_file, "w") as f:
            json.dump(session.to_dict(), f, indent=2)

        return session

    def clear_session(self) -> None:
        """Delete the persisted session file when present."""
        if self.state_file.exists():
            self.state_file.unlink()

    def kill_old_session(self, session: SessionInfo) -> bool:
        """Terminate the process described by ``session`` if it is still alive.

        Args:
            session: Session metadata describing the process to terminate.

        Returns:
            bool: ``True`` if a matching process was terminated.
        """
        try:
            import psutil
        except ImportError:
            return False

        try:
            if not psutil.pid_exists(session.pid):
                return False

            process = psutil.Process(session.pid)
            process_name = process.name().lower()

            if not any(tool in process_name for tool in ["claude", "codex", "gemini"]):
                return False

            process.terminate()

            try:
                process.wait(timeout=5)
            except psutil.TimeoutExpired:
                process.kill()

            return True

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    def rotate_session(
        self, tool: str, pid: int, cwd: str | None = None, kill_old: bool = True
    ) -> SessionInfo:
        """Persist a new session and optionally terminate the previous one.

        Args:
            tool: Tool name for the new session.
            pid: Process identifier for the new session.
            cwd: Optional working directory override.
            kill_old: When ``True`` attempt to terminate the previous session.

        Returns:
            SessionInfo: Metadata describing the newly written session state.
        """
        # Read existing session
        old_session = self.read_session()

        # Kill old session if requested and exists
        if kill_old and old_session:
            self.kill_old_session(old_session)

        # Write new session
        return self.write_session(tool, pid, cwd)
