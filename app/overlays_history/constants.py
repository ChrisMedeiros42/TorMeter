"""Constants and styles for the combat history overlay."""

from PyQt6.QtGui import QColor

_HEADER_STYLE = (
    "color: white; font-size: 9px; font-weight: bold; background: transparent;"
)
_LABEL_STYLE = "color: rgba(255,255,255,200); font-size: 8px; background: transparent;"
_VALUE_STYLE = "color: white; font-size: 8px; background: transparent;"
_SELECTED_BG = QColor(30, 144, 255, 40)
_FIGHT_BG = QColor(255, 255, 255, 8)

_MAX_LIST_H = 420

_COMBO_STYLE = (
    "QComboBox { color: white; background: rgba(255,255,255,20);"
    " border: 1px solid rgba(255,255,255,60); border-radius: 3px;"
    " font-size: 8px; padding: 1px 4px; }"
    "QComboBox::drop-down { width: 14px; border: none; }"
    "QComboBox QAbstractItemView { background: rgba(20,20,30,240);"
    " color: white; selection-background-color: rgba(30,144,255,180);"
    " border: 1px solid rgba(255,255,255,60); font-size: 8px; }"
)
_SCOPE_LIVE = "? Live Session"
