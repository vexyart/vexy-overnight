---
this_file: WORK.md
---
## Active Focus — 2025-09-21

1. **Issue 101 · Continuation Enhancements**
   - Rebuild generated hooks around `settings.toml`, prompt templates, notifications, and PID rotation.
   - Update ConfigManager/status reporting so continuation toggles propagate through CLI workflows.
   - Expand regression tests for hooks and CLI; keep coverage ≥70%.
   - Document new behaviour in just-the-docs site and README.

2. **Issue 102 · Version-Bump Validation**
   - Capture cross-platform smoke results or documented limitations for the simplified version-bump CLI.

## Upcoming Test Runs
- `python -m pytest -xvs`
- `python -m pytest --cov=src --cov-report=term-missing`

## 2025-09-22
- Implemented Issue 106 hook templating with launcher scripts and terminal spawn fallbacks.
- Fixed `SessionStateManager.kill_old_session` handling for missing `psutil` to satisfy tests.
- Tests: `python -m pytest -xvs` ✅
- Verification sweep: python -m pytest -xvs ✅ (91 passed); python -m pytest --cov=. --cov-report=term-missing ✅ (91 passed, 60% overall coverage).
