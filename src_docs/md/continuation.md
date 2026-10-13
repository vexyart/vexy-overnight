# How continuation works

Continuation is a chain of small steps, each in its own file. Knowing the chain makes it easy to see where something stopped.

```text
assistant stops
  → its hook runs           (~/.claude/hooks/vocl-go.py or ~/.codex/voco-go.py)
  → hook writes a job file  (vocl-new.json or voco-new.json, next to the hook)
  → hook opens a terminal   (command from settings.toml)
  → helper runs             (vocl-new.py or voco-new.py)
  → helper starts the next assistant and records it
```

## 1. The assistant calls the hook

`vomgr enable` registers the hooks:

| Assistant | Where | What is registered |
| --- | --- | --- |
| Claude Code | `~/.claude/settings.json`, `hooks.Stop` | `"~/.claude/hooks/vocl-go.py" "$CLAUDE_PROJECT_DIR"` |
| Codex | `~/.codex/config.toml`, `notify` | `~/.codex/voco-go.py` |

Claude runs its `Stop` hook when it finishes responding. Codex runs its `notify` program on its notification events.

The hook scripts start with `#!/usr/bin/env python3` and import `vexy_overnight.hook_runtime`, so the `python3` on `PATH` must have the package installed.

## 2. The hook finds the project directory

The Claude hook takes the first of these that exists:

1. The directory in `$CLAUDE_PROJECT_DIR`.
2. `project_dir` or `cwd` from the JSON that Claude sends on standard input.
3. `$PWD`, or the current directory.

The Codex hook takes the first of these that exists:

1. `cwd` or `working_directory` from the `context` field of the JSON payload.
2. `cwd` from the payload.
3. The `cwd` recorded in the most recently changed `~/.codex/sessions/*.jsonl` file.
4. `$PWD`, or the current directory.

## 3. The hook reads the preferences

From `~/.vexy-overnight/settings.toml` (created with defaults if missing; see [Configuration](configuration.md)):

- If continuation is off for the tool that just stopped, the hook deletes any pending job file and exits. Nothing else happens.
- Otherwise it reads the target tool. A target other than `claude`, `codex` or `gemini` is treated as `claude`.

## 4. The prompt

The hook takes the prompt template of the tool that just stopped and fills in:

| Placeholder | Value |
| --- | --- |
| `{todo}` | Up to five lines of `<project>/TODO.md` that start with `- [ ]`, or `No open TODO items.` |
| `{plan}` | The first five non-empty lines of `<project>/PLAN.md`, or `No plan summary available.` |
| `{target}` | The tool that will start next |
| `{source}` | The tool that just stopped |

If the template contains another `{…}` placeholder, the template is used as it is, without any substitution.

Example: with the template `Carry on with:\n{todo}` and this `TODO.md`:

```markdown
- [ ] First task
- [x] Done task
- [ ] Second task
```

the prompt is:

```text
Carry on with:
- [ ] First task
- [ ] Second task
```

## 5. The command for the next assistant

| Target | Command |
| --- | --- |
| `claude` | `claude --continue --dangerously-skip-permissions --prompt "<prompt>"` |
| `codex` | `codex --cd=<project> -m gpt5 --dangerously-bypass-approvals-and-sandbox --sandbox danger-full-access "<prompt>"` |
| `gemini` | `gemini -c -y "<prompt>"` |

The executable is resolved with `which`; if that fails, the bare name is used.

## 6. The job file

The hook writes the command, the project directory and a set of environment variables to a JSON file next to itself: `~/.claude/hooks/vocl-new.json` or `~/.codex/voco-new.json`. A real example, with paths shortened:

```json
{
  "command": [
    "…/bin/codex",
    "--cd=…/proj",
    "-m",
    "gpt5",
    "--dangerously-bypass-approvals-and-sandbox",
    "--sandbox",
    "danger-full-access",
    "Carry on with:\n- [ ] First task\n- [ ] Second task"
  ],
  "cwd": "…/proj",
  "env": {
    "VOMGR_TARGET_TOOL": "codex",
    "VOMGR_SOURCE_TOOL": "claude",
    "VOMGR_PROMPT": "Carry on with:\n- [ ] First task\n- [ ] Second task",
    "VOMGR_PROJECT_DIR": "…/proj",
    "VOMGR_NOTIFICATION_ENABLED": "1",
    "VOMGR_NOTIFICATION_MESSAGE": "Handing over to codex",
    "VOMGR_NOTIFICATION_SOUND": "Glass",
    "VOMGR_KILL_OLD": "1"
  }
}
```

The next assistant gets these variables in its environment.

## 7. The terminal

The hook then starts the helper script (`vocl-new.py` or `voco-new.py`) in a new terminal:

1. If `VOMGR_HOOK_FORCE_DIRECT=1` is set, it runs the helper directly in the hook's own process and skips the terminal.
2. Otherwise it takes the terminal command for the target tool and platform from the preferences (`terminals.per_tool`, then `terminals.defaults`), replaces `{command}` with `cd <project> && <python> <helper>` and starts it without waiting.
3. If no command is configured for the platform: on macOS it asks the application named in `$VOMGR_TERMINAL_APP` (default `Terminal`) to run the command through `osascript`; on Windows it opens `cmd.exe`; elsewhere it runs the helper directly.

If the helper script is missing, the hook prints `Helper script … is missing. Re-run vomgr install.` and exits with `1`.

## 8. The helper starts the next assistant

The helper:

1. Reads the job file. If it is missing or invalid, it prints a message and stops.
2. Starts the command in the project directory, with the variables from `env` added to its environment.
3. If `VOMGR_KILL_OLD` is `1` and `~/.vexy-overnight/session_state.json` records an earlier session, stops that process: it sends a terminate signal, waits up to five seconds, then kills it. It only does this when `psutil` is installed and the process name contains `claude`, `codex` or `gemini`.
4. Records the new process in `~/.vexy-overnight/session_state.json`:

    ```json
    {
      "tool": "codex",
      "pid": 51976,
      "start_time": "2026-10-12T23:06:51.040162",
      "cwd": "…/proj"
    }
    ```

5. If notifications are on, prints `[vomgr] <message>`.
6. Waits for the assistant to exit.

## Gemini

`~/.gemini/voge-go.py` is a placeholder. It prints `Gemini continuation not yet implemented. Check for updates.` and exits. `vomgr enable gemini` registers nothing. Gemini can still be a target: another tool can hand over to it.
