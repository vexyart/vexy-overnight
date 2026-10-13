# Configuration

## Where things are stored

| Path | Written by | Content |
| --- | --- | --- |
| `~/.vexy-overnight/settings.toml` | `vomgr continuation`, `prompt`, `notify`, `terminal`; created with defaults by the first command or hook that reads it | Your preferences |
| `~/.vexy-overnight/settings.toml.backup.<timestamp>` | every save of the preferences | The previous version |
| `~/.vexy-overnight/session_state.json` | the helper scripts | The assistant process started last |
| `~/.vexy-overnight/update.log` | `vomgr update` | Versions before and after updates |
| `~/.claude/settings.json` | `vomgr enable/disable claude`, `install`, `uninstall` | Claude Code settings, including the `Stop` hook |
| `~/.codex/config.toml` | `vomgr enable/disable codex`, `install`, `uninstall` | Codex settings, including `notify` |
| `<file>.backup.<YYYYMMDD_HHMMSS>` | every change to the two files above | The previous version |

Backups are never deleted by `vomgr`. Remove old ones by hand.

## settings.toml

Every key is optional. Missing keys take the defaults shown here, which is also what a new file contains:

```toml
kill_old_sessions = true

[continuations.claude]
enabled = true
target = "codex"

[continuations.codex]
enabled = true
target = "claude"

[continuations.gemini]
enabled = false
target = "claude"

[prompts]
claude = "Continue work in the next tool. Outstanding tasks:\n{todo}"
codex = "Pick up the session with these TODOs:\n{todo}"
gemini = "Continue assisting with current plan:\n{plan}"

[notifications]
enabled = true
message = "Continuing on {target}"
sound = "success"

[terminals.defaults]
darwin = ["open", "-a", "Terminal", "--args", "bash", "-lc", "{command}; exec bash"]
windows = ["wt", "powershell", "-NoExit", "-Command", "{command}"]
linux = ["gnome-terminal", "--", "bash", "-lc", "{command}; exec bash"]

[terminals.per_tool]
```

When the file is read, a `target` that is not `claude`, `codex` or `gemini`, or a `kill_old_sessions` that is not a boolean, raises an error. The `vomgr` command then fails; a hook falls back to the built-in defaults.

### continuations

One table per tool that can stop. `enabled` switches handover on for that tool; `target` names the tool to start next. A tool can target itself.

Commands: `vomgr continuation set <source> <target>`, `vomgr continuation disable <source>`, `vomgr continuation status`.

Turning a tool off here leaves its hook registered with the assistant. The hook still runs, sees the setting and exits. To unregister the hook, use `vomgr disable <tool>`.

### prompts

One template per tool. The template of the tool that stopped is used. Placeholders are `{todo}`, `{plan}`, `{target}` and `{source}`; see [How continuation works](continuation.md#4-the-prompt).

Commands: `vomgr prompt set <tool> <template>`, `vomgr prompt show <tool>`.

### notifications

`enabled` and `message` control the line `[vomgr] <message>` that the helper prints after it starts the next assistant; `{target}` and `{source}` are filled in. `sound` is stored and passed to the next assistant in `VOMGR_NOTIFICATION_SOUND`; nothing plays it in this version.

Commands: `vomgr notify set --message=… --enabled=…`, `vomgr notify sound <name>`, `vomgr notify show`.

### terminals

The command that opens a terminal for the helper. `{command}` is replaced by `cd <project> && <python> <helper script>`, with each part shell-quoted. The platform key is `platform.system()` in lower case: `darwin`, `linux` or `windows`.

`terminals.per_tool` lets one target tool use a different terminal. Its keys are tool names, and each holds platform keys:

```toml
[terminals.per_tool.codex]
linux = ["xterm", "-e", "bash", "-lc", "{command}; exec bash"]
```

Look-up order: `per_tool.<target>.<platform>`, then `defaults.<platform>`, then the built-in fallback described in [How continuation works](continuation.md#7-the-terminal).

Edit this section of the file directly. `vomgr terminal set` cannot store commands with arguments that start with `-`; see [vomgr reference](cli.md#terminal).

### kill_old_sessions

With `true`, the helper stops the previously recorded assistant process after it starts the new one. This needs `psutil`.

## Environment variables

These are read by the hook scripts:

| Variable | Effect |
| --- | --- |
| `VOMGR_HOOK_FORCE_DIRECT` | `1` runs the helper in the hook's process instead of a new terminal. Useful for debugging. |
| `VOMGR_TERMINAL_APP` | macOS application used by the `osascript` fallback when no terminal command is configured. Default `Terminal`. |
| `CLAUDE_PROJECT_DIR` | Set by Claude Code; the Claude hook uses it as the project directory. |
| `PWD` | Last-resort project directory for both hooks. |

The helpers set these for the next assistant: `VOMGR_TARGET_TOOL`, `VOMGR_SOURCE_TOOL`, `VOMGR_PROMPT`, `VOMGR_PROJECT_DIR`, `VOMGR_NOTIFICATION_ENABLED`, `VOMGR_NOTIFICATION_MESSAGE`, `VOMGR_NOTIFICATION_SOUND`, `VOMGR_KILL_OLD`.
