# ◢▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧◣
# ▧ - Lunar Edge Games                                          ▧
# ▧ - Tor Meter                                                 ▧
# ▧▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▧
# ▧ - Module: App                                               ▧
# ▧ - Sub-Module: Screen Geometry                               ▧
# ◥▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧◤

"""Helpers for keeping window positions within a visible screen's viewport."""

from __future__ import annotations

from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QGuiApplication


def clamp_to_screen(x: int, y: int, width: int, height: int) -> tuple[int, int]:
    """
    Clamp a window's top-left (x, y) so its full width/height rect stays within
    the available geometry of whichever screen currently contains (x, y),
    falling back to the primary screen if that point isn't on any screen.
    """
    screen = QGuiApplication.screenAt(QPoint(x, y))
    if screen is None:
        screen = QGuiApplication.primaryScreen()
    if screen is None:
        return x, y

    area = screen.availableGeometry()
    # Guard against a window larger than the screen so the range doesn't invert.
    max_x = max(area.left(), area.right() - width + 1)
    max_y = max(area.top(), area.bottom() - height + 1)
    clamped_x = min(max(x, area.left()), max_x)
    clamped_y = min(max(y, area.top()), max_y)
    return clamped_x, clamped_y
