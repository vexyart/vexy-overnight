# this_file: src/vexy_overnight/hooks_tpl/__init__.py
"""Namespace package exposing continuation hook templates.

The package only exports module names so :func:`importlib.resources` can locate
the embedded files.  Nothing is executed at import time because the contents
are treated as string templates.
"""

from __future__ import annotations

__all__ = [
    "vocl_go",
    "vocl_new",
    "voco_go",
    "voco_new",
    "voge_go",
]
