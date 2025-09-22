# this_file: tests/test_version_bump.py
"""Tests for version bump tool."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from vexy_overnight.tools.version_bump import (
    bump_version,
    check_clean_working_tree,
    get_next_version,
    is_git_repo,
)


class TestIsGitRepo:
    """Validate repository detection logic for :func:`is_git_repo`."""

    @patch("pathlib.Path.exists")
    def test_is_git_repo_valid(self, mock_exists):
        """Return ``True`` when ``.git`` directory is present."""
        mock_exists.return_value = True
        assert is_git_repo()

    @patch("pathlib.Path.exists")
    def test_is_git_repo_invalid(self, mock_exists):
        """Return ``False`` when ``.git`` directory does not exist."""
        mock_exists.return_value = False
        assert not is_git_repo()


class TestGetNextVersion:
    """Exercise the logic that chooses the next semantic version tag."""

    @patch("subprocess.run")
    def test_get_next_version_no_tags(self, mock_run):
        """Fallback to ``v1.0.0`` when no tags are discovered."""
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        assert get_next_version() == "v1.0.0"

    @patch("subprocess.run")
    def test_get_next_version_existing_tags(self, mock_run):
        """Increment the highest discovered version by one patch."""
        mock_result = MagicMock()
        mock_result.stdout = "v1.0.0\nv1.0.1\nv1.1.0\n"
        mock_run.return_value = mock_result

        assert get_next_version() == "v1.1.1"

    @patch("subprocess.run")
    def test_get_next_version_single_tag(self, mock_run):
        """Handle a single existing tag by bumping its patch number."""
        mock_result = MagicMock()
        mock_result.stdout = "v2.5.3\n"
        mock_run.return_value = mock_result

        assert get_next_version() == "v2.5.4"

    @patch("subprocess.run")
    def test_get_next_version_malformed_tags(self, mock_run):
        """Ignore malformed tags while deriving the next release number."""
        mock_result = MagicMock()
        mock_result.stdout = "invalid\nv1.0.0\nbadtag\n"
        mock_run.return_value = mock_result

        assert get_next_version() == "v1.0.1"

    @patch("subprocess.run")
    def test_get_next_version_git_error(self, mock_run):
        """Return ``v1.0.0`` when ``git tag`` invocation raises an error."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        assert get_next_version() == "v1.0.0"


class TestCheckCleanWorkingTree:
    """Verify detection of clean versus dirty working trees."""

    @patch("subprocess.run")
    def test_check_clean_working_tree_clean(self, mock_run):
        """Return ``True`` when ``git status`` yields no changes."""
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        assert check_clean_working_tree()

    @patch("subprocess.run")
    def test_check_clean_working_tree_dirty(self, mock_run):
        """Return ``False`` when ``git status`` reports staged or unstaged files."""
        mock_result = MagicMock()
        mock_result.stdout = " M file.txt\n?? new_file.py\n"
        mock_run.return_value = mock_result

        assert not check_clean_working_tree()

    @patch("subprocess.run")
    def test_check_clean_working_tree_git_error(self, mock_run):
        """Return ``False`` if ``git status`` exits with an error."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        assert not check_clean_working_tree()


class TestBumpVersion:
    """Cover success and failure paths through :func:`bump_version`."""

    @patch("vexy_overnight.tools.version_bump.sys.exit")
    @patch("vexy_overnight.tools.version_bump.is_git_repo")
    def test_bump_version_not_git_repo(self, mock_is_git, mock_exit):
        """Abort with ``SystemExit`` when invoked outside a Git repository."""
        mock_is_git.return_value = False

        # Make exit actually stop execution
        mock_exit.side_effect = SystemExit(1)

        with pytest.raises(SystemExit):
            bump_version()

        mock_exit.assert_called_once_with(1)

    @patch("vexy_overnight.tools.version_bump.sys.exit")
    @patch("vexy_overnight.tools.version_bump.check_clean_working_tree")
    @patch("vexy_overnight.tools.version_bump.is_git_repo")
    def test_bump_version_dirty_tree(self, mock_is_git, mock_clean, mock_exit):
        """Abort with ``SystemExit`` when the working tree is dirty."""
        mock_is_git.return_value = True
        mock_clean.return_value = False

        # Make exit actually stop execution
        mock_exit.side_effect = SystemExit(1)

        with pytest.raises(SystemExit):
            bump_version()

        mock_exit.assert_called_once_with(1)

    @patch("vexy_overnight.tools.version_bump.sys.exit")
    @patch("subprocess.run")
    @patch("vexy_overnight.tools.version_bump.check_clean_working_tree")
    @patch("vexy_overnight.tools.version_bump.is_git_repo")
    def test_bump_version_pull_fails(self, mock_is_git, mock_clean, mock_run, mock_exit):
        """Abort with ``SystemExit`` if pulling the latest commits fails."""
        mock_is_git.return_value = True
        mock_clean.return_value = True
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        # Make exit actually stop execution
        mock_exit.side_effect = SystemExit(1)

        with pytest.raises(SystemExit):
            bump_version()

        mock_exit.assert_called_once_with(1)

    @patch("vexy_overnight.tools.version_bump.is_git_repo")
    @patch("vexy_overnight.tools.version_bump.check_clean_working_tree")
    @patch("vexy_overnight.tools.version_bump.get_next_version")
    @patch("subprocess.run")
    @patch("builtins.print")
    def test_bump_version_success(
        self, mock_print, mock_run, mock_get_version, mock_clean, mock_is_git
    ):
        """Successful bump should call the git pipeline and print success."""
        mock_is_git.return_value = True
        mock_clean.return_value = True
        mock_get_version.return_value = "v1.2.3"

        bump_version()

        # Verify git commands were called
        expected_calls = [
            (["git", "pull"],),
            (["git", "tag", "v1.2.3"],),
            (["git", "push"],),
            (["git", "push", "--tags"],),
        ]

        actual_calls = [call[0] for call in mock_run.call_args_list]
        for expected_call in expected_calls:
            assert expected_call in actual_calls

        # Verify success message was printed
        mock_print.assert_any_call("✅ Successfully created and pushed v1.2.3")

    @patch("vexy_overnight.tools.version_bump.is_git_repo")
    @patch("vexy_overnight.tools.version_bump.check_clean_working_tree")
    @patch("vexy_overnight.tools.version_bump.get_next_version")
    @patch("subprocess.run")
    @patch("builtins.print")
    def test_bump_version_verbose(
        self, mock_print, mock_run, mock_get_version, mock_clean, mock_is_git
    ):
        """Verbose mode emits progress messages for each git operation."""
        mock_is_git.return_value = True
        mock_clean.return_value = True
        mock_get_version.return_value = "v1.2.3"

        bump_version(verbose=True)

        # Verify verbose messages were printed
        mock_print.assert_any_call("Pulling latest changes...")
        mock_print.assert_any_call("Creating tag v1.2.3...")
        mock_print.assert_any_call("Pushing commits...")
        mock_print.assert_any_call("Pushing tags...")
