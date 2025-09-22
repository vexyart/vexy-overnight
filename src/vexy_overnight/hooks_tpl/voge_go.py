#!/usr/bin/env python3
# this_file: src/vexy_overnight/hooks_tpl/voge_go.py
"""Placeholder Gemini continuation hook rendered during installation.

The script prints a friendly message so users know the Gemini workflow is not
yet available.  It keeps the template footprint consistent across tools.
"""

from __future__ import annotations

import sys

MESSAGE = "Gemini continuation not yet implemented. Check for updates."


def main() -> None:
    """Emit a notice indicating the Gemini continuation is not implemented."""
    sys.stderr.write(MESSAGE + "\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
