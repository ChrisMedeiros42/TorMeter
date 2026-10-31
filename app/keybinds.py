# ◢▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧◣
# ▧ - Lunar Edge Games                                          ▧
# ▧ - Tor Meter                                                 ▧
# ▧▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▧
# ▧ - Module: App                                               ▧
# ▧ - Sub-Module: Keybinds                                      ▧
# ◥▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧◤

"""Shared definitions and helpers for TorMeter's configurable global hotkeys."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent

from app.constants import MOD_ALT, MOD_CONTROL, MOD_SHIFT, VK_F1

# Action identifiers, in display order, and their human-readable labels.
ACTION_ORDER = ["toggle_click_through", "restore_menu", "quit", "force_foreground"]

ACTION_LABELS: dict[str, str] = {
    "toggle_click_through": "Toggle Click-Through",
    "restore_menu": "Restore Menu",
    "quit": "Quit TorMeter",
    "force_foreground": "Force Foreground",
}

DEFAULT_KEYBINDS: dict[str, str] = {
    "toggle_click_through": "Ctrl+Shift+F7",
    "restore_menu": "Ctrl+Shift+F8",
    "quit": "Ctrl+Shift+F9",
    "force_foreground": "Ctrl+Shift+F2",
}

# Windows VK codes for F1-F12 are contiguous starting at VK_F1; Qt's F-key
# codes are also contiguous, but with different numeric values, so an
# explicit map is needed to translate between the two.
_VK_TO_NAME: dict[int, str] = {VK_F1 + i: f"F{i + 1}" for i in range(12)}
_QT_KEY_TO_VK: dict[int, int] = {
    getattr(Qt.Key, f"Key_F{i + 1}"): VK_F1 + i for i in range(12)
}
for _c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
    # Qt.Key and Win32 VK codes are numerically identical for letters/digits.
    _VK_TO_NAME[ord(_c)] = _c
_NAME_TO_VK: dict[str, int] = {name: vk for vk, name in _VK_TO_NAME.items()}

_MOD_ORDER = (
    (Qt.KeyboardModifier.ControlModifier, MOD_CONTROL, "Ctrl"),
    (Qt.KeyboardModifier.AltModifier, MOD_ALT, "Alt"),
    (Qt.KeyboardModifier.ShiftModifier, MOD_SHIFT, "Shift"),
)


def combo_to_string(mod: int, vk: int) -> str:
    """Render a (MOD_* bitmask, VK_* code) pair as e.g. 'Ctrl+Shift+F2'."""
    parts = [name for _, flag, name in _MOD_ORDER if mod & flag]
    parts.append(_VK_TO_NAME.get(vk, f"VK{vk:#x}"))
    return "+".join(parts)


def string_to_combo(text: str) -> "tuple[int, int] | None":
    """Parse e.g. 'Ctrl+Shift+F2' into (mod, vk). Returns None if invalid."""
    tokens = [t.strip() for t in text.split("+") if t.strip()]
    if not tokens:
        return None
    mod = 0
    key_tokens = []
    for token in tokens:
        for _, flag, name in _MOD_ORDER:
            if token.lower() == name.lower():
                mod |= flag
                break
        else:
            key_tokens.append(token)
    if len(key_tokens) != 1 or mod == 0:
        return None
    vk = _NAME_TO_VK.get(key_tokens[0].upper())
    if vk is None:
        return None
    return mod, vk


def qt_event_to_combo(event: QKeyEvent) -> "tuple[int, int] | None":
    """Convert a key press event into (mod, vk), or None if not bindable."""
    key = event.key()
    if key in (
        Qt.Key.Key_Control,
        Qt.Key.Key_Shift,
        Qt.Key.Key_Alt,
        Qt.Key.Key_Meta,
        Qt.Key.Key_unknown,
    ):
        return None
    vk = _QT_KEY_TO_VK.get(key)
    if vk is None and (
        Qt.Key.Key_A <= key <= Qt.Key.Key_Z or Qt.Key.Key_0 <= key <= Qt.Key.Key_9
    ):
        vk = key
    if vk is None:
        return None
    mods = event.modifiers()
    mod = 0
    for qt_flag, flag, _ in _MOD_ORDER:
        if mods & qt_flag:
            mod |= flag
    if mod == 0:
        return None
    return mod, vk
