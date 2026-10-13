# Launchers and version-bump

## vocl, voco, voge

The three launchers find the assistant's executable, build a fixed command line and run it in the foreground. They are thin wrappers: they do not read `~/.vexy-overnight/settings.toml`, and they do not install or check hooks.

The executable is looked up with `which`, then in `/usr/local/bin`, `~/.local/bin` and `/opt/homebrew/bin`. If it is not found, the launcher logs an install hint and exits with `1`:

| Launcher | Hint |
| --- | --- |
| `vocl` | `npm install -g @anthropic-ai/claude-code` |
| `voco` | `brew install codex` |
| `voge` | `npm install -g @google/gemini-cli` |

!!! warning
    All three launchers turn off the assistant's permission or sandbox checks. Review the command lines below before you use them.

### vocl

```bash
vocl [WORDS…]
```

Runs:

```text
claude --dangerously-skip-permissions --model claude-sonnet-4 [--prompt "WORDS…"]
```

All arguments are joined with spaces into one prompt. `vocl` has no options of its own; something like `vocl --help` becomes the prompt `--help`.

`vomgr run claude --model=NAME` replaces `claude-sonnet-4` with `NAME`. `vomgr run claude --cwd=DIR` changes to `DIR` first.

### voco

```bash
voco [-m NAME] [-p | -e] [WORDS…]
```

Runs:

```text
codex -m NAME [-p -e] --dangerously-bypass-approvals-and-sandbox --sandbox danger-full-access [WORDS…]
```

| Argument | Effect |
| --- | --- |
| `-m NAME` | Passed to `codex` as `-m NAME`. Default: `gpt5`. |
| `-p` or `-e` | Adds `-p -e` to the `codex` command line |
| anything else | Joined with spaces into the prompt, passed as the last argument |

`vomgr run codex --cwd=DIR --profile=NAME` passes `--cd=DIR` and `-m NAME`.

### voge

```bash
voge [WORDS…]
```

Runs:

```text
gemini -c -y [WORDS…]
```

All arguments are joined into one prompt. `vomgr run gemini --cwd=DIR` changes to `DIR` first.

## version-bump

`version-bump` tags the next patch version of the git repository in the current directory and pushes it.

```bash
version-bump [-v | --verbose]
```

It does this, in order, and stops with exit code `1` at the first failure:

1. Checks that `.git` exists in the current directory. Otherwise: `Error: Not a git repository`.
2. Checks that `git status --porcelain` is empty. Otherwise: `Error: Working tree not clean. Please commit changes first.`
3. Runs `git pull`.
4. Lists tags matching `v*.*.*`, takes the highest by number and adds one to the patch number. With no such tags, the version is `v1.0.0`.
5. Prints `Creating version: vX.Y.Z` and runs `git tag vX.Y.Z`.
6. Runs `git push` and `git push --tags`.
7. Prints `✅ Successfully created and pushed vX.Y.Z`.

Example: with tags `v1.0.9` and `v1.0.10`, the next tag is `v1.0.11`, because the comparison is numeric.

`--verbose` prints each step and shows the output of the `git` commands.

!!! note
    `version-bump` only creates and pushes a tag. It does not change any file, build a package or upload anything. In this repository, pushing a `v*` tag starts the release workflow.
