# Development

## Repository layout

| Path | Content |
| --- | --- |
| `src/vexy_overnight/cli.py` | `VomgrCLI` and the preference groups behind `vomgr` |
| `src/vexy_overnight/config.py` | `ConfigManager`: edits `~/.claude/settings.json` and `~/.codex/config.toml` with backup and rollback |
| `src/vexy_overnight/hooks.py` | `HookManager`: renders the hook templates into the home directory |
| `src/vexy_overnight/hooks_tpl/` | Templates for `vocl-go.py`, `vocl-new.py`, `voco-go.py`, `voco-new.py`, `voge-go.py` |
| `src/vexy_overnight/hook_runtime.py` | Code shared by the rendered hooks: prompt, command, terminal, launch |
| `src/vexy_overnight/user_settings.py` | Reads and writes `~/.vexy-overnight/settings.toml` |
| `src/vexy_overnight/session_state.py` | Records and stops assistant sessions |
| `src/vexy_overnight/launchers.py` | `LauncherManager`, `vocl`, `voco`, `voge` |
| `src/vexy_overnight/rules.py` | `RulesManager` for instruction files |
| `src/vexy_overnight/updater.py` | `UpdateManager` for `vomgr update` |
| `src/vexy_overnight/tools/version_bump.py` | `version-bump` |
| `src/vexy_overnight/vexy_overnight.py` | `Config`, `Summary` and `process_data`, kept for compatibility with early releases |
| `tests/` | pytest suite |
| `src_docs/` | Documentation source (this site) |

The hook templates are rendered with Python's `str.format`. Literal braces in a template must be doubled, which is why the templates write `dict()` instead of `{}`.

## Set up an environment

```bash
git clone https://github.com/vexyart/vexy-overnight.git
cd vexy-overnight
uv sync --extra test
```

## Run the tests

```bash
uv run --extra test python -m pytest -q -o addopts=""
```

The tests that touch the home directory replace `HOME` with a temporary directory, and the hook tests use stub `claude` and `codex` executables, so no real assistant is started.

On the current main branch, with `psutil` added (`uv run --extra test --with psutil …`), 91 tests passed and two failed: `test_vocl_go_when_todo_items_present_then_prompt_includes_unfinished` and `test_voco_go_when_context_string_then_uses_context_directory`; in both, the stub assistant did not record its arguments. Without `psutil`, five more tests in `tests/test_session_state.py` fail on the missing module.

## Lint and format

```bash
uvx ruff check src tests
uvx ruff format --respect-gitignore src tests
```

## Versioning

The version comes from git tags (`vX.Y.Z`) through `hatch-vcs`. At build time it is written to `src/vexy_overnight/__version__.py`, which is not tracked in git. Between tags the version looks like `1.1.3.dev0+gffd58a9cc`. In a source checkout that was never built or installed, `vexy_overnight.__version__` falls back to the installed distribution's metadata, then to `0.0.0`.

## Build

```bash
./build.sh            # docs and package
./build.sh docs       # src_docs/ → docs/
./build.sh package    # dist/*.whl and dist/*.tar.gz, checked with twine
```

The wheel contains the package, including `py.typed` and the `hooks_tpl/` templates. The source distribution adds `tests/`, `README.md`, `CHANGELOG.md`, `DEPENDENCIES.md`, `LICENSE` and `pyproject.toml`.

## Documentation

```bash
src_docs/build.sh          # strict build into docs/
src_docs/build.sh serve    # live preview on http://127.0.0.1:8000
```

Sources are in `src_docs/md/`, the configuration in `src_docs/mkdocs.yml`. The `Docs` workflow rebuilds `docs/` on each push to `main` that touches `src_docs/`.

## Release

1. Export a PyPI token for `uv publish`, for example `UV_PUBLISH_TOKEN`.
2. Run:

    ```bash
    ./publish.sh
    ```

    `gitnextver` commits pending changes, tags the next `vX.Y.Z` and pushes. The script then builds from that tag and uploads with `uv publish`.

The pushed tag also triggers the `Release` workflow, which builds the package, uploads it to PyPI with `skip-existing` and creates a GitHub release.
