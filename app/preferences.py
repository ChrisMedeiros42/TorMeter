"""Compatibility shim for the refactored preferences package."""

from app.config.preferences import (
    Anchor,
    DEFAULT_ENABLE_HOTKEY,
    DEFAULT_WINDOW_PREFS,
    Expand,
    Preferences,
    WINDOW_NAMES,
    WindowPrefs,
)

__all__ = [
    "Preferences",
    "WindowPrefs",
    "Expand",
    "Anchor",
    "DEFAULT_WINDOW_PREFS",
    "DEFAULT_ENABLE_HOTKEY",
    "WINDOW_NAMES",
]
