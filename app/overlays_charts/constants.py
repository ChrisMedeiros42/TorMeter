"""Constants and styles for the charts overlay."""

from PyQt6.QtGui import QColor

_LABEL_STYLE = "color: rgba(255,255,255,180); font-size: 8px; background: transparent;"
_COMBO_STYLE = (
    "QComboBox { color: white; background: rgba(255,255,255,20);"
    " border: 1px solid rgba(255,255,255,60); border-radius: 3px;"
    " font-size: 8px; padding: 1px 4px; }"
    "QComboBox::drop-down { width: 14px; border: none; }"
    "QComboBox QAbstractItemView { background: rgba(20,20,30,240);"
    " color: white; selection-background-color: rgba(30,144,255,180);"
    " border: 1px solid rgba(255,255,255,60); font-size: 8px; }"
)

_STAT_LABELS = ["DPS", "HPS", "DTPS", "Damage Out", "Damage In", "Heal Out"]
_CHART_TYPES = ["Bar", "Line", "Pie"]
_BAR_H = 18
_BAR_SPACING = 3
_NAME_W = 80
_VAL_W = 40
_ME_FG = QColor("#1E90FF")
_OTHER_FG = QColor(120, 120, 180, 180)

_SCOPE_SESSION = "Session"
_SCOPE_LIVE = "Live"
_FIGHT_ALL = "All Fights"

_LINE_COLORS = [
    QColor(255, 99, 71),
    QColor(50, 205, 50),
    QColor(255, 215, 0),
    QColor(148, 0, 211),
    QColor(255, 165, 0),
    QColor(0, 206, 209),
    QColor(255, 20, 147),
    QColor(144, 238, 144),
]
