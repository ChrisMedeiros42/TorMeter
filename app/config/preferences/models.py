"""Preference data model types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Expand = Literal["up", "down"]
Anchor = Literal["top-left", "top-right", "bottom-left", "bottom-right"]


@dataclass
class WindowPrefs:
    x: int
    y: int
    default_x: int
    default_y: int
    expand: Expand
    anchor: Anchor
    visible: bool = True
