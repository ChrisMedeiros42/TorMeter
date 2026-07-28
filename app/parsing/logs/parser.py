"""Public parsing API for SWTOR combat log lines and files."""

from __future__ import annotations

from .constants import COMPANION, NPC, PLAYER
from .models import Entity, LogEvent
from .patterns import (
    ABILITY_RE,
    COMPANION_RE,
    EFFECT_RE,
    LINE_RE,
    NPC_RE,
    PLAYER_RE,
    VAL_MITIG_RE,
    VAL_MITIG_TYPE_RE,
    VAL_NUM_RE,
    VAL_TYPE_RE,
)


def _parse_timestamp(ts: str) -> int:
    h, m, rest = ts.split(":")
    s, ms = rest.split(".")
    return (int(h) * 3600 + int(m) * 60 + int(s)) * 1000 + int(ms)


def _parse_entity(raw: str) -> Entity | None:
    raw = raw.strip()
    if not raw:
        return None

    m = PLAYER_RE.match(raw)
    if m:
        return Entity(
            kind=PLAYER,
            name=m.group(1),
            account_id=m.group(2),
            hp_current=int(m.group(3)),
            hp_max=int(m.group(4)),
        )

    m = COMPANION_RE.match(raw)
    if m:
        return Entity(
            kind=COMPANION,
            name=m.group(1),
            account_id=None,
            hp_current=int(m.group(2)),
            hp_max=int(m.group(3)),
        )

    m = NPC_RE.match(raw)
    if m:
        return Entity(
            kind=NPC,
            name=m.group(1),
            account_id=None,
            hp_current=int(m.group(2)),
            hp_max=int(m.group(3)),
        )

    return None


def _parse_ability(raw: str) -> tuple[str, int]:
    raw = raw.strip()
    if not raw:
        return "", 0
    m = ABILITY_RE.match(raw)
    if m:
        return m.group(1).strip(), int(m.group(2))
    return raw, 0


def _parse_effect(raw: str) -> tuple[str, int, str, int]:
    raw = raw.strip()
    if not raw:
        return "", 0, "", 0
    m = EFFECT_RE.match(raw)
    if m:
        return m.group(1).strip(), int(m.group(2)), m.group(3).strip(), int(m.group(4))
    return raw, 0, "", 0


def _parse_value(
    val_str: str | None, eff_str: str | None
) -> tuple[int, int, int, str, bool]:
    if not val_str:
        return 0, 0, 0, "", False

    val_str = val_str.strip()

    def _eff() -> int | None:
        return int(float(eff_str)) if eff_str else None

    m = VAL_MITIG_TYPE_RE.match(val_str)
    if m:
        amount = int(m.group(1))
        is_crit = m.group(2) == "*"
        mitigation = int(m.group(3))
        amount_type = m.group(4)
        effective = _eff() if _eff() is not None else amount
        return amount, effective, mitigation, amount_type, is_crit

    m = VAL_MITIG_RE.match(val_str)
    if m:
        amount = int(m.group(1))
        is_crit = m.group(2) == "*"
        mitigation = int(m.group(3))
        effective = _eff() if _eff() is not None else amount
        return amount, effective, mitigation, "", is_crit

    m = VAL_TYPE_RE.match(val_str)
    if m:
        amount = int(m.group(1))
        is_crit = m.group(2) == "*"
        amount_type = m.group(3)
        effective = _eff() if _eff() is not None else amount
        return amount, effective, 0, amount_type, is_crit

    m = VAL_NUM_RE.match(val_str)
    if m:
        amount = int(float(m.group(1)))
        effective = _eff() if _eff() is not None else amount
        return amount, effective, 0, "", False

    return 0, 0, 0, "", False


def parse_line(line: str) -> LogEvent | None:
    m = LINE_RE.match(line.strip())
    if not m:
        return None

    ts_str, src_str, tgt_str, abl_str, eff_str, val_str, eff_val_str = m.groups()

    source = _parse_entity(src_str)
    target = source if tgt_str.strip() == "=" else _parse_entity(tgt_str)
    ability_name, ability_id = _parse_ability(abl_str)
    effect_type, effect_type_id, effect_name, effect_name_id = _parse_effect(eff_str)
    amount, effective_amount, mitigation, amount_type, is_crit = _parse_value(
        val_str, eff_val_str
    )

    return LogEvent(
        timestamp_ms=_parse_timestamp(ts_str),
        source=source,
        target=target,
        ability_name=ability_name,
        ability_id=ability_id,
        effect_type=effect_type,
        effect_type_id=effect_type_id,
        effect_name=effect_name,
        effect_name_id=effect_name_id,
        amount=amount,
        effective_amount=effective_amount,
        mitigation=mitigation,
        amount_type=amount_type,
        is_crit=is_crit,
    )


def is_friendly_player(entity: Entity | None) -> bool:
    return entity is not None and entity.kind == PLAYER


def is_friendly_companion(entity: Entity | None) -> bool:
    return entity is not None and entity.kind == COMPANION


def parse_file(path: str) -> list[LogEvent]:
    events: list[LogEvent] = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            event = parse_line(line)
            if event is not None:
                events.append(event)
    return events
