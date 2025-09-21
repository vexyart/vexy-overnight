#!/usr/bin/env python3
# this_file: tests/test_session_state.py
"""Tests for session state management."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from vexy_overnight.session_state import SessionInfo, SessionStateManager


class TestSessionInfo:
    """Tests for SessionInfo dataclass."""

    def test_session_info_creation(self):
        """Test creating a SessionInfo."""
        info = SessionInfo(
            tool="claude", pid=12345, start_time="2025-09-21T10:00:00", cwd="/home/user/project"
        )
        assert info.tool == "claude"
        assert info.pid == 12345
        assert info.start_time == "2025-09-21T10:00:00"
        assert info.cwd == "/home/user/project"

    def test_to_dict(self):
        """Test converting SessionInfo to dictionary."""
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
        """Test creating SessionInfo from dictionary."""
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
    """Tests for SessionStateManager."""

    @pytest.fixture
    def temp_state_dir(self, tmp_path):
        """Create a temporary state directory."""
        state_dir = tmp_path / ".vexy-overnight"
        state_dir.mkdir()
        return state_dir

    @pytest.fixture
    def manager(self, temp_state_dir):
        """Create a SessionStateManager with temp directory."""
        return SessionStateManager(state_dir=temp_state_dir)

    def test_init(self, temp_state_dir):
        """Test SessionStateManager initialization."""
        manager = SessionStateManager(state_dir=temp_state_dir)
        assert manager.state_file == temp_state_dir / "session_state.json"
        assert manager.state_file.parent.exists()

    def test_read_session_no_file(self, manager):
        """Test reading session when no file exists."""
        result = manager.read_session()
        assert result is None

    def test_write_and_read_session(self, manager):
        """Test writing and reading a session."""
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
        """Test reading a corrupted session file."""
        # Write invalid JSON
        manager.state_file.write_text("invalid json")
        result = manager.read_session()
        assert result is None

    def test_clear_session(self, manager):
        """Test clearing session state."""
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
        """Test successfully killing an old session."""
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
        """Test killing when process doesn't exist."""
        mock_pid_exists.return_value = False

        session = SessionInfo("claude", 12345, "2025-09-21T10:00:00", "/tmp")
        result = manager.kill_old_session(session)

        assert result is False

    @patch("psutil.Process")
    @patch("psutil.pid_exists")
    def test_kill_old_session_wrong_process(self, mock_pid_exists, mock_Process, manager):
        """Test not killing unrelated process."""
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
        """Test force kill on timeout."""
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
        """Test handling when psutil is not available."""
        # Patch the import at the specific location in the module
        original_import = __builtins__.__import__

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
        """Test rotating sessions."""
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
        """Test rotating without killing old session."""
        # Write an old session
        manager.write_session("claude", 11111)

        # Rotate without killing
        new_session = manager.rotate_session("codex", 22222, kill_old=False)

        assert new_session.tool == "codex"
        assert new_session.pid == 22222
