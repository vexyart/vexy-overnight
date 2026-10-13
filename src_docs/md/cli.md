# vomgr reference

`vomgr` is built with [Python Fire](https://github.com/google/python-fire) from the `VomgrCLI` class in `src/vexy_overnight/cli.py`. Run `vomgr` with no arguments to list the commands and groups.

## Conventions

- Tool names are `claude`, `codex` and `gemini`, in any letter case. Any other name fails with `tool must be one of claude, codex, gemini`.
- Flag names use underscores, as in the source: `--backup_legacy`, `--self_update`, `--global_mode`. Fire also accepts hyphens (`--dry-run`).
- Boolean flags switch on by name: `--check`. Positional arguments can also be given by name: `vomgr run claude` equals `vomgr run --tool=claude`.
- Commands return text or data; Fire prints it.
- To see a command's flags without running it, write `vomgr <command> -- --help`.

## Setup commands

### install

```bash
vomgr install [--backup_legacy] [--migrate]
```

1. With `--backup_legacy`: back up `~/.claude/settings.json`, `~/.codex/config.toml` and `~/.gemini/config.json` if they exist.
2. Write the hook scripts into `~/.claude/hooks/`, `~/.codex/` and `~/.gemini/`. Existing copies are overwritten.
3. With `--migrate`: replace hook commands that mention `claude4ever.py` or `codex4ever.py` with the new scripts. Without it: create `~/.claude/settings.json` (`{}`) and `~/.codex/config.toml` (empty) if they are missing.

Output: one line per step, ending with `Installation complete`.

### uninstall

```bash
vomgr uninstall
```

Delete the hook scripts and their pending JSON files, then remove the Claude `Stop` hook and the Codex `notify` entry. Output: `Hooks removed` and `Configurations restored to defaults`.

### enable, disable

```bash
vomgr enable claude      # set the Stop hook in ~/.claude/settings.json
vomgr enable codex       # set notify in ~/.codex/config.toml
vomgr disable claude     # remove the Stop hook
vomgr disable codex      # remove notify
```

`enable` replaces the whole `Stop` hook list or `notify` value. `disable` removes them, and also removes the `hooks` table when it becomes empty. For `gemini`, both print `Gemini continuation not yet implemented`.

Each change is written with a backup and a check: the file is copied to `<name>.backup.<YYYYMMDD_HHMMSS>`, the new content is written to `<name>.tmp`, parsed again, and only then moved over the original. If any step fails, the backup is restored.

### status

```bash
vomgr status
```

Whether the Claude and Codex hooks point at the `vexy-overnight` scripts, and whether `claude`, `codex` and `gemini` are found on `PATH`.

### version

```bash
vomgr version
```

Print the package version.

## Running assistants

### run

```bash
vomgr run claude [--cwd=DIR] [--model=NAME] [--prompt=TEXT]
vomgr run codex  [--cwd=DIR] [--profile=NAME] [--prompt=TEXT]
vomgr run gemini [--cwd=DIR] [--prompt=TEXT]
```

Start an assistant in the foreground and wait for it to exit. The commands it builds are the same as for `vocl`, `voco` and `voge`; see [Launchers](launchers.md). `--model` applies to Claude only and `--profile` to Codex only. After the assistant exits, `vomgr` prints `Launched <tool>`.

If the assistant's command is not found, `vomgr` logs an install hint and exits with `1`.

## Instruction files

### rules

```bash
vomgr rules --sync
vomgr rules --append="Always run the tests before committing."
vomgr rules --search="ruff"
vomgr rules --replace='["old text", "new text"]'
vomgr rules --sync --global_mode
```

| Flag | Effect |
| --- | --- |
| `--sync` | Link all copies of each instruction file to the most recently changed one |
| `--append=TEXT` | Append `TEXT` to the most recent copy of each instruction file |
| `--search=TEXT` | Count lines containing `TEXT` in each instruction file |
| `--replace=[OLD, NEW]` | Replace `OLD` with `NEW` in every copy |
| `--global_mode` | Work on the assistants' home directories instead of the current directory |

Flags can be combined; the actions run in the order of the table. With no action flag, the output is `No rules action performed`. See [Instruction files](rules.md) for what each action does to the files.

## Updates

### update

```bash
vomgr update --check
vomgr update --cli [--dry_run] [--skip='["llxprt", "qwen"]']
vomgr update --self_update [--dry_run]
vomgr update --all
```

| Flag | Effect |
| --- | --- |
| `--check` | Print `tool: current -> available` for `claude`, `codex`, `gemini` and `vexy-overnight` |
| `--cli` | Update the assistant CLIs (see below) |
| `--self_update` | Upgrade the `vexy-overnight` package |
| `--all` | `--cli` and `--self_update` |
| `--dry_run` | Log what would run, change nothing |
| `--skip` | List of tool names to leave out of `--cli` |

`--cli` runs `npm install -g` for each of these packages, then `brew update` and `brew upgrade codex`:

| Name | npm package |
| --- | --- |
| `claude` | `@anthropic-ai/claude-code@latest` |
| `gemini` | `@google/gemini-cli@nightly` |
| `llxprt` | `@vybestack/llxprt-code@nightly` |
| `qwen` | `@qwen-code/qwen-code@nightly` |
| `terragon` | `@terragon-labs/cli@latest` |
| `justevery` | `@just-every/code@latest` |

`--self_update` runs `uv pip install --upgrade vexy-overnight` if `uv` is on `PATH`, otherwise `python -m pip install --upgrade vexy-overnight` with the Python that runs `vomgr`.

The before and after versions of an update are appended to `~/.vexy-overnight/update.log`.

`--check` reports `available` as `latest` for Claude and `nightly` for Gemini; it does not look these up. For Codex it asks Homebrew; for `vexy-overnight`, PyPI.

## Preference groups

These groups read and write `~/.vexy-overnight/settings.toml`. See [Configuration](configuration.md) for the file format.

### continuation

```bash
vomgr continuation status
vomgr continuation set claude codex     # when claude stops, start codex
vomgr continuation disable codex        # codex hands over to nobody
```

`set` also switches the source on. Output: `claude continuation now targets codex`.

### prompt

```bash
vomgr prompt show claude
vomgr prompt set claude $'Carry on with:\n{todo}'
```

The shell must pass a real line break: `$'…'` does that in Bash and Zsh. In plain double quotes, `\n` is stored as a backslash and an `n`.

The template for a tool is used when that tool finishes. Placeholders: `{todo}`, `{plan}`, `{target}`, `{source}`; see [How continuation works](continuation.md#4-the-prompt).

### notify

```bash
vomgr notify show
vomgr notify set --message="Handing over to {target}" --enabled=True
vomgr notify sound Glass
```

When enabled, the helper prints `[vomgr] <message>` after it starts the next assistant. `{target}` and `{source}` are filled in. The sound name is stored and passed on in `VOMGR_NOTIFICATION_SOUND`, but nothing plays it in this version.

### terminal

```bash
vomgr terminal show darwin
```

```text
open
-a
Terminal
--args
bash
-lc
{command}; exec bash
```

The command used to open a terminal for the helper, per platform (`darwin`, `linux`, `windows`). `{command}` is replaced by `cd <project> && <python> <helper script>`. `show` fails with `no terminal command configured for <platform>` when there is none.

`vomgr terminal set <platform> <arg> …` stores a new command; the last argument must contain `{command}`. Fire reads any argument that starts with `-` as a flag, so commands such as `bash -lc "{command}"` cannot be entered this way: the call fails. Edit `[terminals.defaults]` in `~/.vexy-overnight/settings.toml` instead; see [Configuration](configuration.md#terminals).
