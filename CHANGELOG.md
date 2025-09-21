---
this_file: CHANGELOG.md
---
## 2025-09-21 - /report Verification Sweep
- Re-ran `python -m pytest -xvs` (61 passed) to confirm workspace health before starting new Phase C tasks.
- Cleared completed Phase A/B objectives from `TODO.md` and documented remaining backlog explicitly.
- Updated `PLAN.md` to record accomplished phases and keep focus on hook/runtime enhancements next.

## 2025-09-21 - CLI migrated to Fire
- Replaced Typer-based command handling with a Fire component hierarchy and nested continuation/prompt/notify/terminal subcommands.
- Updated CLI unit tests to call Fire commands directly and widened coverage to new settings helpers.
- Added `fire` dependency and removed `typer` from project metadata and lockfile.

## 2025-09-21 - Reporting & Cleanup
- Ran `python -m pytest -xvs` (41 passed) to verify current workspace; noted provisional 37% coverage pending remaining modules.
- Flattened TODO backlog to phase-tagged bullet list and removed completed Phase 1 items.
- Trimmed PLAN.md upcoming focus to Phases 2-8 and reiterated hook-first priority.
- Logged latest test execution in WORK.md to preserve verification trail.

## 2025-09-21 - Phase 1: vomgr CLI Foundation
- Created `vomgr` CLI tool as main entry point for unified AI assistant management
- Implemented 8 core commands: install, uninstall, enable, disable, run, rules, update, status
- Created simplified continuation hooks (vocl-go, voco-go, voge-go) replacing 1500+ line legacy scripts
- Added configuration management for Claude (settings.json) and Codex (config.toml)
- Implemented tool launchers (vocl, voco, voge) as console script entry points
- Added instruction file synchronization with hard link support
- Created update manager for NPM and Brew packages
- Removed dependencies on iTerm2, pyttsx3, asyncio
- Added comprehensive test suite with 22 tests covering all CLI commands
- Updated dependencies: added typer, rich, tomli, tomli-w for CLI and config management

## 2025-09-21
- Added explicit package exports and wired version metadata for successful imports.
- Implemented deterministic `process_data` summary with loguru debug logs and updated `main()` demo.
- Expanded test coverage for `process_data` scenarios and configured pytest to discover the src layout.
- Enforced non-sequence input rejection, covered the CLI `main()` logging path, and shipped a `py.typed` marker for packaging.
- Validated `Config.options`, deep-copied nested option data in summaries, and introduced a shared `Summary` type for callers.
- Enforced string-only `Config.options` keys and rejected non-`Config` objects when calling `process_data`.
- Added a resilient copy fallback so summary options handle `MappingProxyType` inputs without mutation leaks.
- Revalidated the full pytest suite and coverage (100%) to confirm the configuration changes remain stable.
- Executed 14-test regression sweep with coverage for reporting checkpoint maintenance.
- Layered safe option cloning (deepcopy → copy → repr) with regression coverage for custom objects that break deep copying.
- Expanded test matrix to cover tuple/deque inputs and locked in focused mypy runs for `src/` + `tests/` only.
- Completed closing verification run (`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -xvs`) and aligned documentation for the reporting milestone.

## 2025-09-21 - Phase 2: Hook Regression Coverage
- Added `tests/test_hooks.py` to exercise generated vocl-go and voco-go scripts using sandboxed HOME/PATH environments.
- Taught Codex hook generator to parse stringified JSON context payloads and plain path fallbacks while preserving minimal subprocess usage.
- Confirmed full suite success via `python -m pytest -xvs`, ensuring new hook tests run alongside existing CLI coverage.
