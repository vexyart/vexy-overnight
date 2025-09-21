# Vexy Overnight Manager (vomgr)

A unified management tool for AI assistant CLIs (Claude, Codex, Gemini), providing streamlined launching, automated continuation workflows, and configuration synchronization.

## Overview

Vexy Overnight Manager (`vomgr`) consolidates and simplifies the management of multiple AI assistant CLIs, replacing a collection of over-engineered legacy tools with a single, maintainable Python package. It handles:

- **Unified Launching**: Start Claude, Codex, or Gemini with consistent interfaces
- **Automated Continuation**: Smart session continuation when tasks complete
- **Configuration Management**: Safe editing of CLI configuration files
- **Rules Synchronization**: Keep instruction files (CLAUDE.md, AGENTS.md, etc.) in sync
- **Tool Updates**: Manage updates for all CLI tools from one place

## Features

### Core Commands

- `vomgr install` - Set up continuation hooks and configurations
- `vomgr enable/disable <tool>` - Toggle continuation automation
- `vomgr run <tool>` - Launch AI assistants with proper settings
- `vomgr rules` - Synchronize instruction files across projects
- `vomgr update` - Update CLI tools and the package itself
- `vomgr status` - View current configuration state

### Simplified Launchers

- `vocl` - Launch Claude with optimized settings
- `voco` - Launch Codex with profile management
- `voge` - Launch Gemini with appropriate flags

### Continuation Tools

- `vocl-go` - Auto-continue Claude sessions (replaces 1500+ line claude4ever.py)
- `voco-go` - Auto-continue Codex sessions (replaces complex codex4ever.py)
- `voge-go` - Gemini continuation (when API available)

## Installation

```bash
# Install from PyPI
pip install vexy-overnight

# Or with uv (recommended)
uv add vexy-overnight

# Install and configure
vomgr install
```

## Quick Start

```bash
# Enable continuation for Claude
vomgr enable claude

# Launch Claude with continuation enabled
vocl
# Or
vomgr run claude

# Sync instruction files in current project
vomgr rules sync

# Update all CLI tools
vomgr update --cli

# Check status
vomgr status
```

## Usage Examples

### Managing Continuation Hooks

```bash
# Enable auto-continuation for Claude and Codex
vomgr enable claude
vomgr enable codex

# Disable continuation for specific tool
vomgr disable claude

# Check what's enabled
vomgr status
```

### Instruction File Management

```bash
# Sync instruction files (CLAUDE.md, AGENTS.md, etc.) in current directory
vomgr rules sync

# Append text to all instruction files
vomgr rules append "Additional instructions here"

# Search in instruction files
vomgr rules search "pattern"

# Replace text across instruction files
vomgr rules replace "old text" "new text"

# Manage global instruction files in home directory
vomgr rules --global sync
```

### Launching AI Assistants

```bash
# Direct launchers (installed as console scripts)
vocl                    # Launch Claude
voco -m gpt5           # Launch Codex with gpt5 profile
voge                    # Launch Gemini

# Via vomgr
vomgr run claude --cwd /path/to/project
vomgr run codex --profile o3
vomgr run gemini
```

### Updates and Maintenance

```bash
# Check for updates
vomgr update --check

# Update CLI tools (claude, codex, gemini)
vomgr update --cli

# Update vexy-overnight itself
vomgr update --self

# Update everything
vomgr update --all

# Dry run (show what would be updated)
vomgr update --cli --dry-run
```

## Architecture

### Simplified Design

Unlike the legacy tools with 1500+ lines of complex async code, vexy-overnight:

- **No iTerm2 dependency**: Uses standard subprocess calls
- **No TTS**: Simple logging instead of speech synthesis
- **No state machines**: Straightforward procedural flow
- **Minimal dependencies**: Just essential packages
- **Testable**: Every component is unit-testable
- **Maintainable**: Clear, simple code under 200 lines per file

### Configuration Safety

- Creates backups before any config modification
- Validates changes after editing
- Provides rollback on errors
- Preserves all existing user settings
- Uses proper JSON/TOML libraries (no regex hacks)

## Migration from Legacy Tools

If you're using the old tools (claude4ever.py, codex4ever.py, etc.):

```bash
# Back up existing configurations
vomgr install --backup-legacy

# Migration automatically preserves your settings
vomgr install --migrate

# Old tools remain available until you're ready
# Both can coexist during transition
```

## Development

This project uses modern Python packaging with [uv](https://github.com/astral-sh/uv):

```bash
# Clone repository
git clone https://github.com/vexyart/vexy-overnight
cd vexy-overnight

# Set up development environment
uv venv --python 3.12
uv sync

# Run tests
python -m pytest -xvs

# Run with coverage
python -m pytest --cov=src --cov-report=term-missing

# Type checking
uvx mypy src/

# Format code
uvx ruff format src/ tests/
```

## Requirements

- Python 3.12+
- One or more AI CLI tools installed:
  - Claude Code (`npm install -g @anthropic-ai/claude-code`)
  - Codex (`brew install codex` or from source)
  - Gemini CLI (`npm install -g @google/gemini-cli`)

## License

MIT License

## Contributing

Contributions welcome! Please ensure:
- All tests pass
- 80%+ code coverage
- Type hints on all functions
- No functions over 20 lines
- No files over 200 lines 