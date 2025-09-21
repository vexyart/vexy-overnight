---
this_file: PLAN.md
---
# Plan — Continuation Hooks & Version Tool Follow-Up (Issues 101 & 102)

## Scope (Single Sentence)
Deliver configurable continuation hooks with documentation while validating the simplified version-bump tool across supported platforms.

## Current Objectives
- Finish continuation runtime work so hooks honour user settings for prompts, notifications, terminals, and session cleanup.
- Align manager/status flows and docs with the continuation feature set.
- Close the remaining verification gap for the version-bump utility.

## Task Breakdown

### Issue 101 · Continuation Runtime Enhancements
- Regenerate `vocl-go`/`voco-go`/`voge-go` to read `settings.toml`, apply prompt templates, trigger optional audio notifications, and record PIDs in `session_state.json`.
- Extend hook tests to cover mapping, template substitution, PID rotation, and failure fallbacks (mock `psutil`, settings, notification behaviour).

### Issue 101 · Config Manager & CLI Alignment
- Update `ConfigManager` so `install`/`enable` respect continuation toggles and skip hook installation when disabled.
- Extend `vomgr status` output to surface continuation destination, prompt override, notification flag, and terminal selection.

### Issue 101 · Documentation Site
- Scaffold `docs/` with just-the-docs remote theme and create `index.md`, `getting-started.md`, `configuration.md`, and `hooks.md` covering continuation usage.
- Refresh `README.md` with a concise docs link and summary of continuation customization features.

### Issue 101 · Verification
- Broaden CLI and hook test suites to exercise new commands/behaviour (`tests/test_cli.py`, `tests/test_hooks.py`).
- Run `python -m pytest -xvs` and `python -m pytest --cov=src --cov-report=term-missing` ensuring ≥70% coverage after new work.

### Issue 102 · Version-Bump Validation
- Perform manual cross-platform smoke tests (macOS + one additional OS via CI or documentation review) or document limitations if testing environments are unavailable.

## Exit Criteria
- Hooks honour user settings end-to-end, terminate old sessions when requested, and handle prompt templating plus notifications gracefully.
- Manager commands fully reflect continuation configuration, and status output reports all relevant toggles.
- Docs site builds locally, highlights continuation workflows, and README points to it within the 200-line limit.
- Test suite covers new logic with the required coverage, and version-bump cross-platform expectations are recorded.
