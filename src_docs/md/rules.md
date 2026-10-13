# Instruction files

Each AI assistant reads its own instruction file: Claude Code reads `CLAUDE.md`, Codex reads `AGENTS.md`, Gemini CLI reads `GEMINI.md`, and so on. When a project keeps several of them, they drift apart. `vomgr rules` finds them, links them together and edits them in one go.

## Which files

`vomgr rules` works on files with these exact names:

- `CLAUDE.md`
- `AGENTS.md`
- `GEMINI.md`
- `QWEN.md`
- `LLXPRT.md`
- `.cursorrules`

## Where it looks

| Mode | Searched recursively |
| --- | --- |
| Default | The current directory |
| `--global_mode` | `~/.claude`, `~/.codex`, `~/.gemini`, `~/.qwen`, `~/.llxprt`, `~/.cursor` (those that exist) |

When `fd` is installed, the search runs `fd -t f <name> <dir>`. `fd` skips hidden files and directories and anything listed in `.gitignore`, so `.cursorrules` is not found in that case. It also reads the name as a regular expression, so a file such as `OLD_CLAUDE.md` matches `CLAUDE.md` too. Without `fd`, the search uses Python's recursive glob, which matches the exact name, including hidden files.

Files are grouped by name: all `CLAUDE.md` files in one group, all `AGENTS.md` files in another.

## --sync

```bash
vomgr rules --sync
```

For each name with two or more copies:

1. Pick the "parent": the non-empty copy with the most recent modification time.
2. Replace every other copy with a hard link to the parent. If a hard link fails (for example across file systems), use a symbolic link.

After syncing, editing any copy edits all of them.

!!! warning
    `--sync` deletes the other copies before linking them. Their content is lost unless it is in version control. It links files of the same name only: `CLAUDE.md` files are linked to each other, not to `AGENTS.md`.

Example: a repository with `CLAUDE.md` at the root and an older `docs/CLAUDE.md`:

```text
./CLAUDE.md        modified today       ← parent
./docs/CLAUDE.md   modified last week   → replaced by a link to ./CLAUDE.md
```

## --append

```bash
vomgr rules --append="Run the tests before every commit."
```

For each name, append a blank line, the text and a newline to the parent copy. Copies that are linked to it show the change too; copies that are not linked do not change.

## --search

```bash
vomgr rules --search="pytest"
```

```text
CLAUDE.md: 3 match(es)
AGENTS.md: 3 match(es)
```

Counts lines that contain the text, exactly as typed (case-sensitive, no patterns). Linked copies are counted once. With no match: `No matches found`.

## --replace

```bash
vomgr rules --replace='["uvx hatch test", "uv run pytest"]'
```

Replace every occurrence of the first string with the second, in every copy. Linked copies are written once. The value must be a list of exactly two strings, otherwise: `replace expects two values: search and replace`.

## Combining actions

Several flags can be given in one call. They run in this order: sync, append, search, replace.

```bash
vomgr rules --sync --append="See TODO.md for open work."
```
