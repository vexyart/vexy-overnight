---
this_file: PLAN.md
---
# Plan — Issue 101: Continuation Customization & Docs

## Scope (Single Sentence)
Enable cross-tool continuation with customizable prompts, notifications, terminal targets, and session cleanup, and add a just-the-docs documentation site.

## Research Notes
- Query: "Python library to launch commands in different terminal applications across macOS, Windows, and Linux" → subprocess remains core API; teletype/xonsh offer higher-level TTYs (Perplexity, 2025-09-21).
- Query: "How to programmatically launch commands in specific terminal apps on macOS, Windows Terminal, and GNOME Terminal from Python" → platform-specific invocations via `open -a Terminal`, `wt`, `gnome-terminal -- bash -c` (Perplexity, 2025-09-21).
- Query: "Cross-platform Python options for playing short notification sounds without external players" → recommends `beepy`, `chime`, `playsound3`, `play_sounds`, `simpleaudio` (Perplexity, 2025-09-21).

## Technical Decisions
- Store continuation preferences in `~/.vexy-overnight/settings.toml` managed by a new `user_settings` helper.
- Add dependencies: `psutil` (cross-platform process termination) and `chime` (simple notification sounds) via pyproject optional extras.
- Modify hook scripts (vocl-go, voco-go) to read settings, kill prior sessions, and launch next tool via platform-specific command templates.
- Extend `vomgr` CLI with `continuation`, `prompt`, `notify`, and `terminal` subcommands for configuration.
- Build docs site under `docs/` using GitHub Pages + just-the-docs remote theme with content synced from CLI features.

## Phase Breakdown

### Completed Phases
- **Phase A — Settings Infrastructure:** Created `src/vexy_overnight/user_settings.py` with dataclass defaults, load/save helpers, and TOML persistence under `~/.vexy-overnight/settings.toml` with backups.
- **Phase B — CLI Extensions:** Added continuation/prompt/notify/terminal subcommands in `cli.py`, delegating to settings helpers while keeping functions concise.

### Phase C — Hook Runtime Enhancements
- Regenerate hook scripts to:
  - Read `settings.toml` for mapping, prompt template, notification text/sound, terminal command, kill-old flag.
  - Collect TODO/PLAN context; substitute `{todo}` `{plan}` `{transcript}` placeholders.
  - Play audio via `chime` when enabled; fall back gracefully if unavailable.
  - Launch target tool using configured terminal command; default to subprocess direct call when not set.
  - Record launched PID into `~/.vexy-overnight/session_state.json` and kill previous PID using `psutil` when flag on.
- Update tests to cover direction mapping, prompt template expansion, and PID cleanup logic (mock `psutil.Process`).

### Phase D — Configuration Manager Alignment
- Extend `ConfigManager` so `install/enable/disable` respect new toggles (skip enabling hooks when continuation disabled).
- Add status reporting to include continuation target, prompt overrides, notification status, terminal selection.

### Phase E — Documentation Site
- Scaffold `docs/` with `_config.yml`, `index.md`, `getting-started.md`, `configuration.md`, `hooks.md`.
- Configure remote theme `just-the-docs/just-the-docs`; add navigation, usage examples, and link to CLI commands.
- Update README to point to docs site (≤200 lines constraint respected).

### Phase F — Testing & Verification
- Unit tests: `tests/test_user_settings.py`, expand `tests/test_cli.py`, `tests/test_hooks.py` for new behaviors.
- Integration tests: simulate enable/disable flows with settings toggled; ensure session-state file updates.
- Run `python -m pytest -xvs` and `python -m pytest --cov=src --cov-report=term-missing` ensuring ≥70% interim coverage.

## Exit Criteria
- CLI commands configure continuation mapping, prompts, notifications, and terminals without manual file editing.
- Hook scripts honour settings, kill old sessions when enabled, and provide audio notification.
- Docs site builds locally (`bundle exec jekyll serve` instructions) and covers new features.
- Tests cover new settings serialization, CLI plumbing, hook logic, and docs anchor existence.
- README updated with docs pointer; CHANGELOG + WORK logs include verification steps.
