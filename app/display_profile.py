# ◢▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧◣
# ▧ - Lunar Edge Games                                          ▧
# ▧ - Tor Meter                                                 ▧
# ▧▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▧
# ▧ - Module: App                                               ▧
# ▧ - Sub-Module: Display Profile                               ▧
# ◥▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧◤

"""Detects a key identifying the current display resolution/scale environment.

Used to select per-environment window-default profiles, since a window layout
tuned for a 1920x1080 @ 100% display won't necessarily fit a 4K @ 150% one.
"""

from __future__ import annotations

from PyQt6.QtGui import QGuiApplication


def detect_profile_key() -> str:
    """Return e.g. '1920x1080@125' for the primary screen's size and scale."""
    screen = QGuiApplication.primaryScreen()
    if screen is None:
        return "unknown"
    size = screen.size()
    scale_pct = round(screen.devicePixelRatio() * 100)
    return f"{size.width()}x{size.height()}@{scale_pct}"


def format_profile_label(profile_key: str) -> str:
    """Render a profile key as a friendly label, e.g. '1920x1080@125' -> '1920×1080 @ 125%'."""
    if "@" not in profile_key:
        return profile_key
    resolution, scale = profile_key.split("@", 1)
    return f"{resolution.replace('x', '×')} @ {scale}%"
