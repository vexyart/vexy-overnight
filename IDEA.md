---
this_file: IDEA.md
---

# Vexy Overnight

## Files

### General files

.cursorrules
.pre-commit-config.yaml
CLAUDE.md
IDEA.md
LICENSE
README.md
dist/
dist/.gitkeep

### Legacy files

external/
external/claude/
external/claude/hooks/
external/claude/hooks/claude4ever.py
external/claude/settings.json
external/codex/
external/codex/claude-codex.md
external/codex/codex4ever.py
external/codex/config.toml
external/utils/
external/utils/vorules.py
external/utils/vocl
external/utils/voco
external/utils/voge
external/utils/llmgrade

### New files

package.toml
pyproject.toml
src/
src/vexy_overnight/
src/vexy_overnight/__version__.py
src/vexy_overnight/vexy_overnight.py
tests/
tests/test_package.py

## Project

<TASK>
- Read @IDEA.md 
- Analyze all the Legacy files 
- Into the YOUR ANSWER HERE section of @IDEA.md write your detailed understanding of what the Legacy files currently do 
- Further write how they could all be aggregated into a handy 'vomgr' (vexy overnight manager) tool for managing, and handy launchers for codex ('voco'), claude ('vocl') and gemini ('voge'), and continuation tools 'vocl-go', 'voco-go' and 'voge-go'. (For gemini, we don’t yet have a hook/notify mechanism but you could try researching it.)

Note: The @external/claude/hooks/claude4ever.py and @external/codex/codex4ever.py tools are over-engineered. Their modern counterparts (vocl-go and voco-go) should be simpler, more robust and rely on the vexy-overnight package. vomgr be an easy way to "turn them on" and "turn them off" (by editing the appropriate config files in the official $HOME/.claude/ and $HOME/.codex/ locations). 

The vomgr tool also needs an "install" command, a "rules" command that manages the rules files (based on @external/utils/vorules.py but better ), and a "run" command that runs 'claude', or 'codex', or 'gemini' (that command would be aliased to 'vocl', 'voco' and 'voge' respectively). 

The vomgr tool also needs an "update" command that updates the vexy-overnight package and the CLI tools (codex, claude, gemini) to the latest versions. This would be based on the @external/utils/llmgrade tool.


</TASK>

### YOUR ANSWER HERE

**Legacy Components**
- Hook automation (`external/claude/hooks/claude4ever.py`, `external/codex/codex4ever.py`): twin asyncio+iTerm2 orchestrators that launch new tabs, kill stale processes, speak via `pyttsx3`, and maintain sprawling state machines that duplicate code and hinge on macOS-only dependencies.
- Claude settings (`external/claude/settings.json`): Claude Code configuration that injects the Stop hook, stretches shell timeouts, and assumes the hook path lives in `$HOME/.claude/hooks/claude4ever.py`.
- Codex configuration (`external/codex/config.toml`, `external/codex/claude-codex.md`): oversized TOML with many model profiles, inline API keys, and a `notify` hook for `codex4ever.py`, backed by documentation that mirrors the Claude hook instructions.
- Launcher shims (`external/utils/vocl`, `external/utils/voco`, `external/utils/voge`): bash wrappers that call each CLI with different argument conventions, hardcoded paths, and no shared validation or logging.
- Instruction sync (`external/utils/vorules.py`): async Fire-based command that links CLAUDE/AGENTS/GEMINI/QWEN files together, offering append/search/replace features but pulling in `aiofiles`, semaphores, and `fd` heuristics.
- Updater (`external/utils/llmgrade`): bash script that prints versions, runs global `npm` installs and `brew upgrade codex`, then prints versions again without error trapping, rollback, or package selection.

**Observed Pain Points**
- Hook scripts embed identical infrastructure twice and depend on heavyweight optional packages (`iterm2`, `psutil`, `pyttsx3`, `fire`, `rich`) instead of a slim core tied to this repo.
- Configuration toggles live in user dotfiles with hand-edited paths, so enabling/disabling hooks requires manual JSON/TOML surgery.
- Launcher scripts (`vocl`, `voco`, `voge`) disagree on argument shapes and environment handling, which makes it hard to reason about behaviour.
- Utility commands (`vorules.py`, `llmgrade`) pull in extra dependencies and mix concerns that should sit inside the `vexy_overnight` package with testable functions.

**vomgr Aggregation Plan**
- Build `vomgr` as a Typer-style (or stdlib `argparse` if we want zero deps) CLI exposed by the `vexy_overnight` package so every command shares the same logging, config paths, and error handling.
- `install` verifies required CLIs exist, writes minimal Claude/Codex config fragments (via safe JSON/TOML editing) to toggle hook `notify` entries, and installs console scripts (`vomgr`, `vocl`, `voco`, `voge`, `vocl-go`, `voco-go`, `voge-go`) using the project packaging instead of ad-hoc shell copies.
- `rules` reuses the core ideas from `vorules` but pared down: detect parent instruction file, mirror via hardlinks or symlinks, support `--append/--search/--replace`, and offer `--global` to operate on `$HOME` dotfolders—implemented with `pathlib`, no asyncio, and fully unit-tested.
- `run` orchestrates launching the selected CLI (claude, codex, gemini) with consistent environment prep, optional `--cwd`, `--profile`, `--prompt` flags, and natively underpins the `vocl`/`voco`/`voge` entry points.
- `update` wraps the `llmgrade` intent with guarded subprocess calls (`npm` upgrades, `brew upgrade codex`, optional `uv pip install --upgrade vexy-overnight`), surfaces dry-run/report modes, and logs version deltas using the shared logger.
- `*-go` wrappers call `vomgr run <tool> --mode continue` (or similar) so hooks just invoke the shared Python entry; `vomgr` will expose helper APIs to toggle Claude/Codex hook activation and, once the Gemini CLI exposes a hook/notify API, we drop in the same mechanism (for now we document the research path and leave `voge-go` as a no-op notifier).

**Verification Strategy**
- Unit-test config editors to ensure `install` and `rules` never corrupt JSON/TOML or lose existing user settings.
- Add CLI smoke tests via `pytest`'s `CliRunner` (or `subprocess`) covering `run`, `rules`, and `update` dry runs with temporary directories.
- Introduce integration tests that simulate Claude/Codex home directories in a temp workspace so `vomgr install --enable` and `--disable` can be validated deterministically.
- Provide documentation snippets in `README.md` describing how to flip hooks on/off and how `vocl-go` replaces `claude4ever.py`, keeping maintenance discoverable.

Ideot wants an auto-updating daemon that watches CLI releases; Critin vetoes the creep and keeps `vomgr update` as an explicit command with optional cron instructions. Decision: embrace the lean command-driven flow, measure before we automate. Critin also pushes to drop `pyttsx3` and the bespoke process orchestration; Ideot agrees once `vomgr run` can show simple Rich prompts or stdout logs instead of speech.
