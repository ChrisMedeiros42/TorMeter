"""Default values for TorMeter preferences."""

from __future__ import annotations

DEFAULT_WINDOW_PREFS: dict = {
    "x": 50,
    "y": 50,
    "default_x": 100,
    "default_y": 100,
    "expand": "down",
    "anchor": "top-left",
}

DEFAULT_ENABLE_HOTKEY = "Ctrl+Shift+F7"

DEFAULT_KEYBINDS: dict = {
    "toggle_click_through": "Ctrl+Shift+F7",
    "restore_menu": "Ctrl+Shift+F8",
    "quit": "Ctrl+Shift+F9",
    "force_foreground": "Ctrl+Shift+F2",
}

WINDOW_NAMES = [
    "Default Overlay",
    "Overlay Master",
    "TorMeter Menu",
    "Summary",
    "DPS",
    "Defense",
    "Heal",
    "Combat History",
    "Charts",
    "Nihilus' Book of Grudges",
]
