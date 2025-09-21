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
