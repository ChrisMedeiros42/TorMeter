"""SWTOR combat log parsing package."""

from .constants import (
    APPLY_EFFECT,
    COMPANION,
    DAMAGE,
    ENTER_COMBAT,
    EVENT,
    EXIT_COMBAT,
    HEAL,
    NPC,
    PLAYER,
    REMOVE_EFFECT,
    SPEND,
)
from .models import Entity, LogEvent
from .parser import (
    is_friendly_companion,
    is_friendly_player,
    parse_file,
    parse_line,
)

__all__ = [
    "APPLY_EFFECT",
    "COMPANION",
    "DAMAGE",
    "ENTER_COMBAT",
    "EVENT",
    "EXIT_COMBAT",
    "HEAL",
    "NPC",
    "PLAYER",
    "REMOVE_EFFECT",
    "SPEND",
    "Entity",
    "LogEvent",
    "parse_line",
    "parse_file",
    "is_friendly_player",
    "is_friendly_companion",
]
