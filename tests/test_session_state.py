#!/usr/bin/env python3
# this_file: tests/test_session_state.py
"""Tests for session state helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from vexy_overnight import session_state


@pytest.fixture()
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provide isolated HOME directory for session state tests."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


def test_load_session_state_when_missing_then_returns_empty(fake_home: Path) -> None:
    """Loading before the file exists should yield an empty mapping."""
    state = session_state.load_session_state()

    assert state == {}


def test_write_session_state_when_data_provided_then_round_trips(fake_home: Path) -> None:
    """Persisted state should be readable on the next load."""
    data = {"codex": {"pid": 1234}}

    session_state.write_session_state(data)
    loaded = session_state.load_session_state()

    assert loaded == data
