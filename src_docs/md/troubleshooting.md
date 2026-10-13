# Troubleshooting

Start with:

```bash
vomgr status                 # are the hooks registered? are the CLIs on PATH?
vomgr continuation status    # which tool hands over to which?
ls ~/.claude/hooks ~/.codex  # are the hook scripts there?
```

## Nothing happens when the assistant stops

Work through the chain in [How continuation works](continuation.md) from the top.

1. **Hook registered?** `vomgr status` must say `enabled` for the tool. If not, run `vomgr enable <tool>`.
2. **Hook scripts present?** `~/.claude/hooks/vocl-go.py` and `vocl-new.py`, or `~/.codex/voco-go.py` and `voco-new.py`. If not, run `vomgr install`.
3. **Continuation on?** `vomgr continuation status` must show `"enabled": true` for the tool that stopped. If it is off, the hook exits silently.
4. **Can the hook import the package?** Run the same Python the hook uses:

    ```bash
    python3 -c "import vexy_overnight.hook_runtime"
    ```

    A `ModuleNotFoundError` means the package is installed in a different environment, for example with `uv tool install`. Install it for this `python3`; see [Installation](installation.md#install-the-package).

5. **Does the hook run at all?** Run it by hand, with the terminal step turned off:

    ```bash
    cd ~/work/my-app
    CLAUDE_PROJECT_DIR="$PWD" VOMGR_HOOK_FORCE_DIRECT=1 ~/.claude/hooks/vocl-go.py < /dev/null
    ```

    This starts the next assistant in the current terminal. Errors are printed.

6. **Job file written?** After the hook runs, `~/.claude/hooks/vocl-new.json` (or `~/.codex/voco-new.json`) should hold the command. Check the `command` and `cwd` fields.

## A terminal window opens, but the assistant does not start

The terminal command did not run the helper. On macOS the default is `open -a Terminal --args bash -lc "{command}; exec bash"`. Test the helper on its own:

```bash
python3 ~/.claude/hooks/vocl-new.py
```

If that works, change the terminal command in `~/.vexy-overnight/settings.toml`; see [Configuration](configuration.md#terminals). Remove the entry for your platform from `[terminals.defaults]` to use the `osascript` fallback, which runs the command in a new window of the app named in `$VOMGR_TERMINAL_APP` (default `Terminal`).

## Helper script … is missing. Re-run vomgr install.

The hook found no helper next to it. Run `vomgr install`.

## The next assistant starts in the wrong directory

The hook uses `$CLAUDE_PROJECT_DIR` (Claude) or the payload and the latest Codex session file (Codex) to find the project, and falls back to `$PWD`. See [How continuation works](continuation.md#2-the-hook-finds-the-project-directory). Check the `cwd` field in the job file.

## The prompt says `No open TODO items.`

`{todo}` reads `TODO.md` in the project directory and keeps only lines that start with `- [ ]` (leading spaces are ignored). Lines such as `* [ ] task` or `- [x] task` do not count. Only the first five are used.

## The previous assistant keeps running

Stopping the previous session needs `psutil`:

```bash
python3 -m pip install --user psutil
```

It also needs `kill_old_sessions = true` in the preferences, and a process name that contains `claude`, `codex` or `gemini`.

## My other Claude Stop hooks are gone

`vomgr enable claude` replaces the whole `hooks.Stop` list in `~/.claude/settings.json`, and `vomgr disable claude` removes it. Restore the earlier version from `~/.claude/settings.json.backup.<timestamp>` and add the `vocl-go.py` entry by hand next to your other hooks. The same applies to `notify` in `~/.codex/config.toml`.

## tool must be one of claude, codex, gemini

A command got a tool name it does not know. Use `claude`, `codex` or `gemini`.

## vomgr terminal set fails

Fire reads arguments that start with `-` as its own flags. Edit `[terminals.defaults]` in `~/.vexy-overnight/settings.toml` instead.

## vomgr update --check shows `unknown` for vexy-overnight

The version check for the package itself fails in this version and reports `unknown`. Use `vomgr version` and compare it with PyPI yourself.

## Gemini continuation not yet implemented

That is the current state. Gemini can be a target, but it cannot hand over to another tool.

## A `vocl` argument is treated as a prompt

`vocl` and `voge` turn all their arguments into the prompt; they have no options. `vocl --help` starts Claude with the prompt `--help`. Use `vomgr run claude --model=…` to pass a model.
