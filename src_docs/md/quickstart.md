# Quick start

This page sets up continuation from Claude Code to Codex and back, checks the setup, and starts a session.

## Prerequisites

- `vexy-overnight` is installed so that `python3` can import it. See [Installation](installation.md).
- `claude` and `codex` are installed and logged in.
- You have read the warning on the [home page](index.md): the assistants run without permission prompts.

## 1. Install the hooks

```bash
vomgr install
```

```text
Continuation hooks installed
Configuration files set up
Installation complete
```

The hook scripts are now in `~/.claude/hooks/` and `~/.codex/`. Nothing calls them yet.

## 2. Connect the hooks to the assistants

```bash
vomgr enable claude
vomgr enable codex
```

```text
claude continuation enabled
codex continuation enabled
```

What changed:

- `~/.claude/settings.json` now has a `Stop` hook that runs `"~/.claude/hooks/vocl-go.py" "$CLAUDE_PROJECT_DIR"`. Any other `Stop` hooks in that file are replaced.
- `~/.codex/config.toml` now has `notify = ["~/.codex/voco-go.py"]` (with your real home path). Any previous `notify` value is replaced.

Before each change, the file is copied to `<name>.backup.<YYYYMMDD_HHMMSS>` next to it.

## 3. Check the status

```bash
vomgr status
```

```text
vomgr status
Claude: enabled (installed=True)
Codex: enabled (installed=True)
Gemini installed=True
```

`installed` tells whether the command is found on your `PATH`.

## 4. Check where each tool hands over

```bash
vomgr continuation status
```

The first time you run a command that reads preferences, `~/.vexy-overnight/settings.toml` is created with the defaults: Claude hands over to Codex, Codex hands over to Claude, Gemini does not hand over.

```text
claude: {"enabled": true, "target": "codex"}
codex:  {"enabled": true, "target": "claude"}
gemini: {"enabled": false, "target": "claude"}
```

To make Claude continue in Claude instead:

```bash
vomgr continuation set claude claude
```

## 5. Give the next session something to do

The prompt for the next assistant is built from the template for the tool that just finished. The default Claude template is:

```text
Continue work in the next tool. Outstanding tasks:
{todo}
```

`{todo}` becomes the first five lines of `TODO.md` in the project directory that start with `- [ ]`, or `No open TODO items.` if there are none. Keep a `TODO.md` with open items:

```markdown
- [ ] Add input validation to the upload form
- [ ] Write tests for the CSV exporter
```

## 6. Start working

```bash
cd ~/work/my-app
vocl
```

`vocl` starts Claude with `--dangerously-skip-permissions --model claude-sonnet-4`. When Claude stops, the `Stop` hook prepares the Codex command and opens a terminal that runs it. When Codex finishes, its `notify` hook does the same in the other direction.

## Stop the loop

To stop handing over without removing anything:

```bash
vomgr continuation disable claude
vomgr continuation disable codex
```

The hooks still run, but they exit at once and delete their pending `vocl-new.json` or `voco-new.json`.

To disconnect the hooks from the assistants completely:

```bash
vomgr disable claude
vomgr disable codex
```
