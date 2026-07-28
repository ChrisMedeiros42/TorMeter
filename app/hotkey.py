# ◢▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧◣
# ▧ - Lunar Edge Games                                        ▧
# ▧ - Tor Meter                                               ▧
# ▧▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▧
# ▧ - Module: Main                                            ▧
# ▧ - Component: Hotkey                                       ▧
# ◥▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧◤

import ctypes
from ctypes import wintypes

from PyQt6.QtCore import QAbstractNativeEventFilter

from app.constants import WM_HOTKEY, HOTKEY_ID


class HotkeyFilter(QAbstractNativeEventFilter):
    """
    Native event filter that fires callbacks when registered hotkeys are pressed.

    Pass a single (callback, hotkey_id) for one hotkey, or a dict mapping
    hotkey_id → callback to handle multiple hotkeys with one filter instance.
    """

    def __init__(self, callback_or_map, hotkey_id: int = HOTKEY_ID):
        super().__init__()
        if isinstance(callback_or_map, dict):
            self._map: dict[int, object] = callback_or_map
        else:
            self._map = {hotkey_id: callback_or_map}

    def nativeEventFilter(self, eventType, message):
        if eventType == b"windows_generic_MSG":
            msg = ctypes.cast(int(message), ctypes.POINTER(wintypes.MSG)).contents
            if msg.message == WM_HOTKEY:
                cb = self._map.get(msg.wParam)
                if cb is not None:
                    cb()
                    return True, 0
        return False, 0
