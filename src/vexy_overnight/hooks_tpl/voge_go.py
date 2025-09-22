#!/usr/bin/env python3
# this_file: src/vexy_overnight/hooks_tpl/voge_go.py
"""Placeholder Gemini continuation hook."""

from __future__ import annotations

import sys

MESSAGE = "Gemini continuation not yet implemented. Check for updates."


def main() -> None:
    """Notify the caller that Gemini continuation is pending."""
    sys.stderr.write(MESSAGE + "\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
