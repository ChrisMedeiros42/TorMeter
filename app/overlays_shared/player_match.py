"""Helpers for matching the configured local player against combat stats entries."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.combat_session import PlayerFightStats


def _norm(value: str | None) -> str:
    return (value or "").strip().casefold()


def _variants(value: str | None) -> set[str]:
    n = _norm(value)
    if not n:
        return set()
    out = {n}
    # SWTOR names/ids may include account/server suffixes.
    for sep in ("@", "#", ":"):
        if sep in n:
            left, right = n.split(sep, 1)
            if left:
                out.add(left)
            if right:
                out.add(right)
    return out


def player_name_matches(selected_name: str | None, candidate_name: str | None) -> bool:
    selected = _variants(selected_name)
    if not selected:
        return False
    candidate = _variants(candidate_name)
    return bool(selected & candidate)


def player_stats_matches(selected_name: str | None, stats: "PlayerFightStats") -> bool:
    return (
        player_name_matches(selected_name, stats.name)
        or player_name_matches(selected_name, stats.account_id)
    )
