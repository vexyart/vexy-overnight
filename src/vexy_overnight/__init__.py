"""Top-level package exports for vexy_overnight."""
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
