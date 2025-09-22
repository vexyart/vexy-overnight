"""Public package interface for `vexy_overnight` utilities.

This module exposes the primary entry points that consumers import when
interacting with the Vexy Overnight Manager (``vomgr``).  Exports are grouped
into two families:

* Historical data helpers (``Config``, ``Summary``, ``process_data``) that are
  maintained for backward compatibility with earlier releases of the package.
* Modern management components (``ConfigManager`` and friends) that power the
  consolidated CLI experience.

The lazy import/``try`` block ensures older environments without the newer
modules remain functional while we migrate all consumers to the streamlined
tooling.
"""
# this_file: src/vexy_overnight/__init__.py

from .__version__ import __version__
from .vexy_overnight import Config, Summary, process_data

# Import new vomgr components
try:
    from .config import ConfigManager
    from .hooks import HookManager
    from .launchers import LauncherManager, vocl, voco, voge
    from .rules import RulesManager
    from .updater import UpdateManager
except ImportError:
    # Allow graceful degradation if new modules not available yet
    ConfigManager = None
    HookManager = None
    LauncherManager = None
    RulesManager = None
    UpdateManager = None
    vocl = None
    voco = None
    voge = None

__all__ = [
    "__version__",
    "Config",
    "Summary",
    "process_data",
    "ConfigManager",
    "HookManager",
    "LauncherManager",
    "RulesManager",
    "UpdateManager",
    "vocl",
    "voco",
    "voge",
]
