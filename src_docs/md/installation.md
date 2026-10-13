# Installation

## Requirements

- Python 3.10 or newer (`requires-python = ">=3.10"`).
- macOS or Linux. The hooks call `which`, and the default terminal commands use Terminal.app on macOS and `gnome-terminal` on Linux. A Windows terminal command is defined but untested here.
- At least one of the assistants you want to drive:
    - Claude Code: `npm install -g @anthropic-ai/claude-code`
    - Codex: `brew install codex`
    - Gemini CLI: `npm install -g @google/gemini-cli`

The Python dependencies are `loguru`, `fire`, `rich`, `tomli` and `tomli-w`. `psutil` is optional: without it, the previous assistant process is not stopped when a new one takes over.

## Install the package

The hook scripts that `vomgr install` writes run with `#!/usr/bin/env python3` and import `vexy_overnight`. The one requirement is that the `python3` on your `PATH` can import the package. The commands below are common ways to get there; they were not tested for this page, and on a Python managed by Homebrew or the operating system, `pip install --user` and `uv pip install --system` can refuse with an `externally-managed-environment` error (PEP 668). In that case use a Python you control, for example one installed with `uv python install` or `pyenv`, and put it first on your `PATH`.

=== "pip (user install)"

    ```bash
    python3 -m pip install --user vexy-overnight
    ```

=== "uv into the system Python"

    ```bash
    uv pip install --system vexy-overnight
    ```

=== "uv tool (commands only)"

    ```bash
    uv tool install vexy-overnight
    ```

    This puts `vomgr`, `vocl`, `voco`, `voge` and `version-bump` on your `PATH`, but in an isolated environment. The hook scripts then cannot import `vexy_overnight` unless that environment's Python is the `python3` on your `PATH`. Use one of the other two methods if you want continuation.

Check the installation:

```bash
vomgr version
python3 -c "import vexy_overnight; print(vexy_overnight.__version__)"
```

Both commands print the same version, for example `1.1.2`.

## Install the hooks

```bash
vomgr install
```

This writes the hook scripts and makes sure the assistants' config files exist:

| File | Content |
| --- | --- |
| `~/.claude/hooks/vocl-go.py` | Claude `Stop` hook |
| `~/.claude/hooks/vocl-new.py` | Helper that starts the next assistant |
| `~/.codex/voco-go.py` | Codex `notify` hook |
| `~/.codex/voco-new.py` | Helper that starts the next assistant |
| `~/.gemini/voge-go.py` | Placeholder that prints `Gemini continuation not yet implemented. Check for updates.` |
| `~/.claude/settings.json` | Created as `{}` if missing |
| `~/.codex/config.toml` | Created empty if missing |

`vomgr install` does not switch continuation on. That is `vomgr enable`; see [Quick start](quickstart.md).

Options:

- `--backup_legacy` copies `~/.claude/settings.json`, `~/.codex/config.toml` and `~/.gemini/config.json` to `<name>.backup.<YYYYMMDD_HHMMSS>` first.
- `--migrate` rewrites hooks that point at the older `claude4ever.py` and `codex4ever.py` scripts so they point at `vocl-go.py` and `voco-go.py`, instead of creating empty config files.

## Uninstall

1. Remove the hooks and the hook entries from the assistants' configs:

    ```bash
    vomgr uninstall
    ```

    This deletes the files in the table above (except `settings.json` and `config.toml`), removes the `Stop` hook from `~/.claude/settings.json` and the `notify` entry from `~/.codex/config.toml`.

2. Remove the package with the tool you installed it with, for example `python3 -m pip uninstall vexy-overnight`.

3. Optionally delete `~/.vexy-overnight/`, which holds your preferences, the session record and the update log.
