#!/usr/bin/env python3
# this_file: src/vexy_overnight/hooks.py
"""Continuation hook handlers for vomgr."""

from pathlib import Path

from loguru import logger


class HookManager:
    """Manages continuation hooks for Claude, Codex, and Gemini."""

    def __init__(self):
        """Initialize hook manager."""
        self.claude_hook_path = Path.home() / ".claude" / "hooks" / "vocl-go.py"
        self.codex_hook_path = Path.home() / ".codex" / "voco-go.py"
        self.gemini_hook_path = Path.home() / ".gemini" / "voge-go.py"

    def install_hooks(self):
        """Install all continuation hooks."""
        self._install_claude_hook()
        self._install_codex_hook()
        self._install_gemini_hook()

    def uninstall_hooks(self):
        """Remove all continuation hooks."""
        for hook_path in [self.claude_hook_path, self.codex_hook_path, self.gemini_hook_path]:
            if hook_path.exists():
                hook_path.unlink()
                logger.debug(f"Removed hook: {hook_path}")

    def _install_claude_hook(self):
        """Install simplified Claude continuation hook."""
        hook_content = '''#!/usr/bin/env python3
"""Simplified Claude continuation hook - vocl-go."""

import json
import os
import subprocess
import sys
from pathlib import Path


def main():
    """Handle Claude Stop hook continuation."""
    # Parse JSON input from stdin
    try:
        payload = json.load(sys.stdin)
        session_id = payload.get("session_id", "")
        transcript_path = payload.get("transcript_path", "")
    except Exception:
        # Fallback to basic continuation
        session_id = ""
        transcript_path = ""

    # Get project directory
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

    # Generate continuation prompt from TODO.md/PLAN.md if they exist
    prompt_parts = []
    todo_path = Path(project_dir) / "TODO.md"
    plan_path = Path(project_dir) / "PLAN.md"

    if todo_path.exists():
        with open(todo_path, "r") as f:
            content = f.read()
            uncompleted = [line for line in content.split("\\n") if line.startswith("- [ ]")]
            if uncompleted:
                prompt_parts.append(f"Continue with TODO items:\\n" + "\\n".join(uncompleted[:5]))

    if plan_path.exists() and not prompt_parts:
        with open(plan_path, "r") as f:
            content = f.read()
            prompt_parts.append("Continue with the plan in PLAN.md")

    if not prompt_parts:
        prompt_parts.append("Continue working on the current task")

    prompt = " ".join(prompt_parts)

    # Launch new Claude session
    cmd = ["claude", "--continue", "--dangerously-skip-permissions"]

    if prompt:
        cmd.extend(["--prompt", prompt])

    try:
        subprocess.run(cmd, cwd=project_dir)
    except Exception as e:
        print(f"Failed to launch Claude: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
'''
        self.claude_hook_path.parent.mkdir(parents=True, exist_ok=True)
        self.claude_hook_path.write_text(hook_content)
        self.claude_hook_path.chmod(0o755)
        logger.debug(f"Installed Claude hook: {self.claude_hook_path}")

    def _install_codex_hook(self):
        """Install simplified Codex continuation hook."""
        hook_content = '''#!/usr/bin/env python3
"""Simplified Codex continuation hook - voco-go."""

import json
import os
import subprocess
import sys
from pathlib import Path


def find_working_directory(payload):
    """Extract working directory from Codex context."""
    # Try to get from context payload
    context = payload.get("context", {})
    if isinstance(context, str):
        text = context.strip()
        if text:
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                return text
            else:
                if isinstance(parsed, dict):
                    context = parsed
                else:
                    return text
        else:
            context = {}
    if isinstance(context, dict):
        cwd = context.get("cwd") or context.get("working_directory")
        if cwd:
            return cwd

    # Try to find from session logs
    sessions_dir = Path.home() / ".codex" / "sessions"
    if sessions_dir.exists():
        # Find most recent session file
        session_files = sorted(sessions_dir.glob("*.jsonl"), key=lambda x: x.stat().st_mtime, reverse=True)
        if session_files:
            try:
                with open(session_files[0], "r") as f:
                    for line in f:
                        entry = json.loads(line)
                        if "cwd" in entry:
                            return entry["cwd"]
            except Exception:
                pass

    # Fallback to environment or current directory
    return os.environ.get("PWD", os.getcwd())


def main():
    """Handle Codex notify hook continuation."""
    # Parse JSON input from stdin
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}

    # Find working directory
    project_dir = find_working_directory(payload)

    # Generate continuation prompt from TODO.md/PLAN.md
    prompt_parts = []
    todo_path = Path(project_dir) / "TODO.md"
    plan_path = Path(project_dir) / "PLAN.md"

    if todo_path.exists():
        with open(todo_path, "r") as f:
            content = f.read()
            uncompleted = [line for line in content.split("\\n") if line.startswith("- [ ]")]
            if uncompleted:
                prompt_parts.append(f"Continue with TODO items:\\n" + "\\n".join(uncompleted[:5]))

    if plan_path.exists() and not prompt_parts:
        with open(plan_path, "r") as f:
            prompt_parts.append("Continue with the plan in PLAN.md")

    if not prompt_parts:
        prompt_parts.append("Continue working on the current task")

    prompt = " ".join(prompt_parts)

    # Launch Codex with continuation
    cmd = [
        "codex",
        f"--cd={project_dir}",
        "--dangerously-bypass-approvals-and-sandbox",
        "--sandbox", "danger-full-access",
        prompt
    ]

    try:
        subprocess.run(cmd)
    except Exception as e:
        print(f"Failed to launch Codex: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
'''
        self.codex_hook_path.parent.mkdir(parents=True, exist_ok=True)
        self.codex_hook_path.write_text(hook_content)
        self.codex_hook_path.chmod(0o755)
        logger.debug(f"Installed Codex hook: {self.codex_hook_path}")

    def _install_gemini_hook(self):
        """Install placeholder Gemini continuation hook."""
        hook_content = '''#!/usr/bin/env python3
"""Placeholder Gemini continuation hook - voge-go."""

import sys
from loguru import logger


def main():
    """Placeholder for Gemini continuation - not yet implemented."""
    logger.info("Gemini continuation hook called but not yet implemented")
    print("Gemini continuation not yet implemented. Check for updates.", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
'''
        self.gemini_hook_path.parent.mkdir(parents=True, exist_ok=True)
        self.gemini_hook_path.write_text(hook_content)
        self.gemini_hook_path.chmod(0o755)
        logger.debug(f"Installed Gemini hook: {self.gemini_hook_path}")
