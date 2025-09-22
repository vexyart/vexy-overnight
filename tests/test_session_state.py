#!/usr/bin/env python3
# this_file: tests/test_session_state.py
"""Tests for session state management."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from vexy_overnight.session_state import SessionInfo, SessionStateManager


class TestSessionInfo:
    """Validate serialisation behaviour for :class:`SessionInfo`."""

    def test_session_info_creation(self):
        """Instantiating :class:`SessionInfo` stores provided field values."""
        info = SessionInfo(
            tool="claude", pid=12345, start_time="2025-09-21T10:00:00", cwd="/home/user/project"
        )
        assert info.tool == "claude"
        assert info.pid == 12345
        assert info.start_time == "2025-09-21T10:00:00"
        assert info.cwd == "/home/user/project"

    def test_to_dict(self):
        """``SessionInfo.to_dict`` produces a JSON-safe mapping."""
        info = SessionInfo(
            tool="codex", pid=54321, start_time="2025-09-21T11:00:00", cwd="/tmp/work"
        )
        result = info.to_dict()
        assert result == {
            "tool": "codex",
            "pid": 54321,
            "start_time": "2025-09-21T11:00:00",
            "cwd": "/tmp/work",
        }

    def test_from_dict(self):
        """:meth:`SessionInfo.from_dict` reconstructs an equivalent instance."""
        data = {
            "tool": "gemini",
            "pid": 99999,
            "start_time": "2025-09-21T12:00:00",
            "cwd": "/opt/app",
        }
        info = SessionInfo.from_dict(data)
        assert info.tool == "gemini"
        assert info.pid == 99999
        assert info.start_time == "2025-09-21T12:00:00"
        assert info.cwd == "/opt/app"


class TestSessionStateManager:
    """Exercise high-level behaviours of :class:`SessionStateManager`."""

    @pytest.fixture
    def temp_state_dir(self, tmp_path):
        """Return a temporary directory emulating the state storage location."""
        state_dir = tmp_path / ".vexy-overnight"
        state_dir.mkdir()
        return state_dir

    @pytest.fixture
    def manager(self, temp_state_dir):
        """Construct a manager instance backed by the temporary directory."""
        return SessionStateManager(state_dir=temp_state_dir)

    def test_init(self, temp_state_dir):
        """Initialisation should derive ``session_state.json`` inside the directory."""
        manager = SessionStateManager(state_dir=temp_state_dir)
        assert manager.state_file == temp_state_dir / "session_state.json"
        assert manager.state_file.parent.exists()

    def test_read_session_no_file(self, manager):
        """Reading without an existing file returns ``None``."""
        result = manager.read_session()
        assert result is None

    def test_write_and_read_session(self, manager):
        """Writing a session should persist it and make it readable."""
        # Write session
        session = manager.write_session("claude", 12345, "/tmp/project")
        assert session.tool == "claude"
        assert session.pid == 12345
        assert session.cwd == "/tmp/project"

        # Read it back
        read_session = manager.read_session()
        assert read_session is not None
        assert read_session.tool == "claude"
        assert read_session.pid == 12345
        assert read_session.cwd == "/tmp/project"

    def test_read_corrupted_file(self, manager):
        """Corrupted JSON should be treated as an absent session."""
        # Write invalid JSON
        manager.state_file.write_text("invalid json")
        result = manager.read_session()
        assert result is None

    def test_clear_session(self, manager):
        """Clearing removes the session file and is idempotent."""
        # Write a session
        manager.write_session("codex", 54321)
        assert manager.state_file.exists()

        # Clear it
        manager.clear_session()
        assert not manager.state_file.exists()

        # Clear when already cleared
        manager.clear_session()  # Should not raise

    @patch("psutil.Process")
    @patch("psutil.pid_exists")
    def test_kill_old_session_success(self, mock_pid_exists, mock_Process, manager):
        """Terminate a matching process and wait for it to exit cleanly."""
        # Setup mock process
        mock_process = MagicMock()
        mock_process.name.return_value = "claude"
        mock_pid_exists.return_value = True
        mock_Process.return_value = mock_process

        session = SessionInfo("claude", 12345, "2025-09-21T10:00:00", "/tmp")
        result = manager.kill_old_session(session)

        assert result is True
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once_with(timeout=5)

    @patch("psutil.pid_exists")
    def test_kill_old_session_no_process(self, mock_pid_exists, manager):
        """Return ``False`` when the recorded PID no longer exists."""
        mock_pid_exists.return_value = False

        session = SessionInfo("claude", 12345, "2025-09-21T10:00:00", "/tmp")
        result = manager.kill_old_session(session)

        assert result is False

    @patch("psutil.Process")
    @patch("psutil.pid_exists")
    def test_kill_old_session_wrong_process(self, mock_pid_exists, mock_Process, manager):
        """Do not touch processes whose names are unrelated to managed CLIs."""
        # Setup mock process with different name
        mock_process = MagicMock()
        mock_process.name.return_value = "notepad"
        mock_pid_exists.return_value = True
        mock_Process.return_value = mock_process

        session = SessionInfo("claude", 12345, "2025-09-21T10:00:00", "/tmp")
        result = manager.kill_old_session(session)

        assert result is False
        mock_process.terminate.assert_not_called()

    @patch("psutil.Process")
    @patch("psutil.pid_exists")
    def test_kill_old_session_timeout(self, mock_pid_exists, mock_Process, manager):
        """Escalate to ``kill`` when terminate waits longer than the timeout."""
        # Import the real psutil to create the exception
        import psutil as real_psutil

        # Setup mock process that times out
        mock_process = MagicMock()
        mock_process.name.return_value = "codex"
        # Use the real TimeoutExpired exception
        mock_process.wait.side_effect = real_psutil.TimeoutExpired(12345, 5)
        mock_pid_exists.return_value = True
        mock_Process.return_value = mock_process

        # Patch TimeoutExpired in the module
        with patch("psutil.TimeoutExpired", real_psutil.TimeoutExpired):
            session = SessionInfo("codex", 12345, "2025-09-21T10:00:00", "/tmp")
            result = manager.kill_old_session(session)

        assert result is True
        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()

    def test_kill_old_session_no_psutil(self, manager):
        """Gracefully return ``False`` if :mod:`psutil` cannot be imported."""
        # Patch the import at the specific location in the module
        import builtins as builtins_mod

        original_import = builtins_mod.__import__

        def mock_import(name, *args, **kwargs):
            if name == "psutil":
                raise ImportError("psutil not available")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            session = SessionInfo("claude", 12345, "2025-09-21T10:00:00", "/tmp")
            result = manager.kill_old_session(session)
            assert result is False

    @patch("psutil.Process")
    @patch("psutil.pid_exists")
    def test_rotate_session(self, mock_pid_exists, mock_Process, manager):
        """Rotating writes new metadata and terminates the previous process."""
        # Setup mock for old process
        mock_process = MagicMock()
        mock_process.name.return_value = "claude"
        mock_pid_exists.return_value = True
        mock_Process.return_value = mock_process

        # Write an old session
        manager.write_session("claude", 11111)

        # Rotate to new session
        new_session = manager.rotate_session("codex", 22222, "/new/path")

        assert new_session.tool == "codex"
        assert new_session.pid == 22222
        assert new_session.cwd == "/new/path"

        # Verify old process was killed
        mock_process.terminate.assert_called_once()

    def test_rotate_session_no_kill(self, manager):
        """Rotation with ``kill_old=False`` preserves the previous process."""
        # Write an old session
        manager.write_session("claude", 11111)

        # Rotate without killing
        new_session = manager.rotate_session("codex", 22222, kill_old=False)

        assert new_session.tool == "codex"
        assert new_session.pid == 22222
