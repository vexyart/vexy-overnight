#!/usr/bin/env python3
# this_file: src/vexy_overnight/session_state.py
"""Session state management for PID tracking and continuation control."""

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
    """Information about an active session."""

    tool: str  # claude, codex, or gemini
    pid: int
    start_time: str
    cwd: str

    def to_dict(self) -> dict[str, str | int]:
        """Convert to dictionary for JSON serialization."""
        return {"tool": self.tool, "pid": self.pid, "start_time": self.start_time, "cwd": self.cwd}

    @classmethod
    def from_dict(cls, data: dict[str, str | int]) -> SessionInfo:
        """Create from dictionary."""
        return cls(
            tool=str(data["tool"]),
            pid=int(data["pid"]),
            start_time=str(data["start_time"]),
            cwd=str(data["cwd"]),
        )


class SessionStateManager:
    """Manages session state for continuation hooks."""

    def __init__(self, state_dir: Path | None = None):
        """Initialize session state manager."""
        if state_dir is None:
            state_dir = Path.home() / VEXY_STATE_DIR
        self.state_file = state_dir / SESSION_STATE_FILE
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def read_session(self) -> SessionInfo | None:
        """Read current session info if it exists."""
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
        """Write new session info."""
        session = SessionInfo(
            tool=tool, pid=pid, start_time=datetime.now().isoformat(), cwd=cwd or os.getcwd()
        )

        with open(self.state_file, "w") as f:
            json.dump(session.to_dict(), f, indent=2)

        return session

    def clear_session(self) -> None:
        """Clear the current session state."""
        if self.state_file.exists():
            self.state_file.unlink()

    def kill_old_session(self, session: SessionInfo) -> bool:
        """Kill an old session process if it exists."""
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
        """Rotate to a new session, optionally killing the old one."""
        # Read existing session
        old_session = self.read_session()

        # Kill old session if requested and exists
        if kill_old and old_session:
            self.kill_old_session(old_session)

        # Write new session
        return self.write_session(tool, pid, cwd)
