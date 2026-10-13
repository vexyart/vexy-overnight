# vexy-overnight

`vexy-overnight` starts AI coding assistants (Claude Code, Codex and Gemini CLI) with fixed flags, and can hand a session that has just finished over to the next assistant, so that work continues without you typing the next command. It also keeps the instruction files those tools read (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md` and others) identical across a project.

The package installs five commands:

| Command | Purpose |
| --- | --- |
| `vomgr` | Install the continuation hooks, switch them on and off, set preferences, sync instruction files, update the CLIs |
| `vocl` | Start Claude Code |
| `voco` | Start Codex |
| `voge` | Start Gemini CLI |
| `version-bump` | Tag the next patch version in a git repository and push it |

## How continuation works, in one example

You have run `vomgr install` and `vomgr enable claude`. You start Claude in a project:

```bash
cd ~/work/my-app
vocl
```

When Claude finishes its turn and stops:

1. Claude runs its `Stop` hook, which `vomgr enable claude` pointed at `~/.claude/hooks/vocl-go.py`.
2. `vocl-go.py` reads your preferences from `~/.vexy-overnight/settings.toml`. By default, Claude hands over to Codex.
3. It builds a prompt from the template for Claude, filling in up to five open `- [ ]` items from `~/work/my-app/TODO.md`.
4. It writes the Codex command line, the project directory and some environment variables to `~/.claude/hooks/vocl-new.json`.
5. It runs the terminal command configured for your platform (on macOS, by default, `open -a Terminal …`) and passes it a shell command that runs the helper `vocl-new.py`.
6. The helper reads the JSON file, starts Codex in `~/work/my-app` with the prompt and records the new process in `~/.vexy-overnight/session_state.json`. If `psutil` is installed, it also stops the assistant process recorded there before.

Codex's `notify` hook works the same way and, by default, hands back to Claude.

The details are in [How continuation works](continuation.md).

!!! warning "The assistants run without confirmations"
    `vocl`, `voco`, `voge` and the continuation commands start the assistants with their permission and sandbox checks turned off (`--dangerously-skip-permissions`, `--dangerously-bypass-approvals-and-sandbox --sandbox danger-full-access`, `-y`). The assistant can then run any command and change any file without asking. Use them only in projects and on machines where that is acceptable.

## Where to go next

| If you want to… | Read |
| --- | --- |
| Install the package | [Installation](installation.md) |
| Set up continuation from Claude to Codex | [Quick start](quickstart.md) |
| Look up a `vomgr` command | [vomgr reference](cli.md) |
| Start an assistant directly, or tag a release | [Launchers and version-bump](launchers.md) |
| Understand hooks, helper scripts and session handover | [How continuation works](continuation.md) |
| Change targets, prompts, notifications or terminals | [Configuration](configuration.md) |
| Keep `CLAUDE.md`, `AGENTS.md` and friends in sync | [Instruction files](rules.md) |
| Fix a problem | [Troubleshooting](troubleshooting.md) |
| Work on the code | [Development](development.md) |
