#!/usr/bin/env python3
# this_file: src/vexy_overnight/tools/version_bump.py
"""Simple version bumping tool for Git repositories."""

import subprocess
import sys
from pathlib import Path


def is_git_repo() -> bool:
    """Check if current directory is a git repository."""
    return (Path.cwd() / ".git").exists()


def get_next_version() -> str:
    """Get next patch version based on existing tags."""
    try:
        result = subprocess.run(
            ["git", "tag", "-l", "v*.*.*"], capture_output=True, text=True, check=True
        )
        tags = [t.strip() for t in result.stdout.split() if t.strip()]

        if not tags:
            return "v1.0.0"

        # Find highest version
        def version_key(tag: str) -> tuple[int, int, int]:
            try:
                return tuple(map(int, tag[1:].split(".")))
            except (ValueError, IndexError):
                return (0, 0, 0)

        latest = max(tags, key=version_key)
        major, minor, patch = version_key(latest)
        return f"v{major}.{minor}.{patch + 1}"
    except (subprocess.CalledProcessError, ValueError):
        return "v1.0.0"


def check_clean_working_tree() -> bool:
    """Ensure working tree is clean."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, check=True
        )
        return not result.stdout.strip()
    except subprocess.CalledProcessError:
        return False


def bump_version(verbose: bool = False) -> None:
    """Main version bumping function."""
    if not is_git_repo():
        print("Error: Not a git repository")
        sys.exit(1)

    if not check_clean_working_tree():
        print("Error: Working tree not clean. Please commit changes first.")
        sys.exit(1)

    # Pull latest changes
    if verbose:
        print("Pulling latest changes...")
    try:
        subprocess.run(["git", "pull"], check=True, capture_output=not verbose)
    except subprocess.CalledProcessError:
        print("Error: Failed to pull from remote")
        sys.exit(1)

    # Calculate next version
    version = get_next_version()
    print(f"Creating version: {version}")

    # Create tag and push
    try:
        if verbose:
            print(f"Creating tag {version}...")
        subprocess.run(["git", "tag", version], check=True)

        if verbose:
            print("Pushing commits...")
        subprocess.run(["git", "push"], check=True, capture_output=not verbose)

        if verbose:
            print("Pushing tags...")
        subprocess.run(["git", "push", "--tags"], check=True, capture_output=not verbose)

        print(f"✅ Successfully created and pushed {version}")
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to create/push tag: {e}")
        sys.exit(1)


def main() -> None:
    """CLI entry point for version bump tool."""
    import argparse

    parser = argparse.ArgumentParser(description="Bump semantic version and create git tag")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()
    bump_version(verbose=args.verbose)


if __name__ == "__main__":
    main()
