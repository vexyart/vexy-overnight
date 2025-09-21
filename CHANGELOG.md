---
this_file: CHANGELOG.md
---

## 2025-09-21 - Session State Management & Testing Progress (Issues 101 & 102)

### Phase C Progress (Issue 101)
- **Session State Management**: Created `src/vexy_overnight/session_state.py` module
  - `SessionInfo` dataclass for tracking tool, PID, start time, and working directory
  - `SessionStateManager` for reading/writing/rotating sessions
  - PID termination support with psutil (optional dependency)
  - Comprehensive tests with 95% coverage
- **Test Coverage**: Created comprehensive tests for session_state module
  - 15 test cases covering all functionality
  - Mock-based testing for process termination
  - Edge case handling (corrupted files, missing processes)

### Testing Infrastructure
- **Test Coverage Progress**: Reached 56% overall coverage (approaching 70% target)
- **Modules with High Coverage**:
  - `session_state.py`: 95% coverage
  - `user_settings.py`: 96% coverage
  - `version_bump.py`: 90% coverage
  - `cli.py`: 83% coverage
  - `vexy_overnight.py`: 100% coverage

### Remaining Work (Issue 101)
- Phase C: Regenerate hooks to read settings and use session state
- Phase D: Update ConfigManager for continuation toggles
- Phase E: Documentation site scaffolding
- Phase F: Final test coverage improvements to reach 70%

## 2025-09-21 - Version Bump Tool Integration (Issue 102)
- **Added simplified version-bump tool**: Created `src/vexy_overnight/tools/version_bump.py` (80 lines vs 448 original)
- **Zero external dependencies**: Replaced GitPython/Rich/Fire/Loguru with stdlib subprocess calls
- **Comprehensive test coverage**: 15 test cases covering all functions with 90% line coverage
- **CLI integration**: Added `version-bump` entry point in pyproject.toml
- **Documentation**: Updated README.md with usage examples and requirements
- **Performance improvement**: <2s execution time vs complex original implementation
- **Simplified error handling**: Basic try/catch with clear error messages
- **Migration path**: Analyzed and documented transition from 448-line external script

### Technical Details
- `is_git_repo()`: Simple .git directory check
- `get_next_version()`: Parse git tags, increment patch version (v1.2.3 → v1.2.4)
- `check_clean_working_tree()`: Verify no uncommitted changes
- `bump_version()`: Main workflow (pull, tag, push)
- All git operations via subprocess.run() for reliability

### Files Added
- `src/vexy_overnight/tools/__init__.py`
- `src/vexy_overnight/tools/version_bump.py`
- `tests/test_version_bump.py`
- `PLAN-102.md` (detailed implementation plan)
- `TODO-102.md` (task breakdown)

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
