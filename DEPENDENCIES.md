---
this_file: DEPENDENCIES.md
---
## Core Dependencies
- **loguru>=0.7,<1.0** — Centralised logging for CLI operations and hook installers.
- **fire>=0.6.0** — Provides the Fire-based command surface exposed in `cli.py`.
- **rich>=13.0.0** — Reserved for upcoming formatted status output; currently installed but not yet imported.
- **tomli>=2.0.0** — Loads TOML configuration for Codex hooks and user settings.
- **tomli-w>=1.0.0** — Persists updated TOML configuration back to disk.

## Tooling & Development
- **uv>=0.5.8** — Package management and script runner for repeatable environments.
- **hatch>=1.12.0** — Build backend helper invoked through Hatchling metadata.
- **pre-commit>=4.1.0** — Manages repository lint/test hooks.
- **ruff>=0.9.7** — Linting/formatting (configured via `pyproject.toml`).
- **mypy>=1.15** — Static typing checks for `src/` and `tests/` packages.
- **pytest>=8.3.4** — Primary test runner (see `tests/`).
- **pytest-cov>=6.0.0** — Coverage reporting to track ≥70% interim target.
- **pytest-xdist>=3.6.1** — Optional parallelisation for expensive suites.
- **pytest-benchmark[histogram]>=5.1.0** — Benchmark support enabled via pytest plugin list.
- **pytest-asyncio>=0.25.3** — Async test support required by configured plugins.
- **coverage[toml]>=7.6.12** — Command-line coverage tooling aligned with pytest-cov output.

## Documentation
- **sphinx>=7.2.6** — Generates full documentation site when Phase E scaffolding begins.
- **sphinx-rtd-theme>=2.0.0** — Theme dependency for Sphinx builds.
- **sphinx-autodoc-typehints>=2.0.0** — Ensures type hints render in generated docs.
- **myst-parser>=3.0.0** — Enables CommonMark/Markdown content inside Sphinx.

## Legacy Dependencies Removed
The following were used in legacy tools but eliminated for simplicity:
- **asyncio** — Replaced with synchronous code
- **typer** — Superseded by Fire-based command surface
- **pyttsx3** — Text-to-speech removed, using simple logging
- **iterm2** — macOS-specific, replaced with subprocess
- **psutil** — Process management simplified
