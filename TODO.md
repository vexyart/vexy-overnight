---
this_file: TODO.md
---

# TODO — Active Items

## Issue 101 · Continuation Runtime
- [ ] Regenerate continuation hooks to honour settings (prompt templates, notifications, terminal command, PID tracking).
- [ ] Extend hook tests for mapping, template substitution, PID rotation, and failure fallbacks.

## Issue 101 · Config Alignment
- [ ] Update ConfigManager install/enable flows to respect continuation toggles.
- [ ] Extend `vomgr status` output with continuation prompt/terminal/notification details.

## Issue 101 · Documentation
- [ ] Scaffold just-the-docs site under `docs/` with required pages.
- [ ] Refresh `README.md` with docs link and continuation summary.

## Issue 101 · Verification
- [ ] Expand CLI and hook tests to cover new settings commands and behaviours.
- [ ] Run `python -m pytest -xvs` and `python -m pytest --cov=src --cov-report=term-missing` (target ≥70% coverage).

## Issue 102 · Version-Bump Validation
- [ ] Perform/document cross-platform smoke checks for the simplified version-bump CLI or record limitations.
