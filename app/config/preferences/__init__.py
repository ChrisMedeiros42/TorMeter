"""Preferences configuration package."""

from .defaults import DEFAULT_ENABLE_HOTKEY, DEFAULT_WINDOW_PREFS, WINDOW_NAMES
from .manager import Preferences
from .models import Anchor, Expand, WindowPrefs

__all__ = [
    "Preferences",
    "WindowPrefs",
    "Expand",
    "Anchor",
    "DEFAULT_WINDOW_PREFS",
    "DEFAULT_ENABLE_HOTKEY",
    "WINDOW_NAMES",
]
