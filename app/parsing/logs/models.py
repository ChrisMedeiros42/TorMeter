"""Data models for parsed combat log entities and events."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Entity:
    kind: str
    name: str
    account_id: str | None
    hp_current: int
    hp_max: int


@dataclass(slots=True)
class LogEvent:
    timestamp_ms: int
    source: Entity | None
    target: Entity | None
    ability_name: str
    ability_id: int
    effect_type: str
    effect_type_id: int
    effect_name: str
    effect_name_id: int
    amount: int
    effective_amount: int
    mitigation: int
    amount_type: str
    is_crit: bool
