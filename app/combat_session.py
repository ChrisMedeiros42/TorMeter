# ◢▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧◣
# ▧ - Lunar Edge Games                                        ▧
# ▧ - Tor Meter                                               ▧
# ▧▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▧
# ▧ - Module: Main                                            ▧
# ▧ - Component: Combat Session                               ▧
# ◥▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧◤

"""combat_session.py — Fight segmentation and per-fight stat aggregation.

Segments a flat list of LogEvents (from log_parser) into individual Fight
instances, then computes per-player statistics for each fight.

Fight boundaries
----------------
- A fight opens when a friendly player fires an EnterCombat event and no fight
  is currently open.
- A fight closes when all players who entered combat have fired ExitCombat.
- After closing, a short grace window (default 1 s) extends the event
  collection to capture trailing effects (e.g. a final shot or companion heal
  that fires at or just after the ExitCombat line). Events in the grace window
  are included in the fight; a new EnterCombat will correctly start the next
  fight regardless of the grace window.

PlayerFightStats fields
-----------------------
  damage_out   — effective damage dealt TO enemies (non-players, non-companions)
  damage_in    — effective damage received FROM enemies
  heal_out     — effective healing done BY this player (net, excl. overheal)
  heal_in      — effective healing received BY this player
  hit_count    — number of damage-dealing events (amount > 0)
  crit_count   — number of those that were critical hits
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.log_parser import (
    APPLY_EFFECT,
    COMPANION,
    DAMAGE,
    ENTER_COMBAT,
    EVENT,
    EXIT_COMBAT,
    HEAL,
    PLAYER,
    Entity,
    LogEvent,
    is_friendly_companion,
    is_friendly_player,
)

# How long after the last ExitCombat to keep collecting events into the fight.
# Must be shorter than the shortest observed inter-fight gap (~1.1 s).
_GRACE_MS: int = 900


# ── per-player stats for a single fight ──────────────────────────────────────


@dataclass
class PlayerFightStats:
    name: str
    account_id: str
    damage_out: int = 0  # effective damage dealt to non-player targets
    damage_in: int = 0  # effective damage received from non-player sources
    heal_out: int = 0  # net effective healing done (amount - overheal)
    heal_in: int = 0  # effective healing received
    hit_count: int = 0  # damage events where effective_amount > 0
    crit_count: int = 0  # of those, how many were crits

    @property
    def crit_rate(self) -> float:
        return self.crit_count / self.hit_count if self.hit_count else 0.0

    def dps(self, duration_s: float) -> float:
        return self.damage_out / duration_s if duration_s > 0 else 0.0
        # return self.damage_out / duration_s if duration_s > 1 else 0.0

    def hps(self, duration_s: float) -> float:
        return self.heal_out / duration_s if duration_s > 0 else 0.0
        # return self.heal_out / duration_s if duration_s > 1 else 0.0

    def dtps(self, duration_s: float) -> float:
        return self.damage_in / duration_s if duration_s > 0 else 0.0
        # return self.damage_in / duration_s if duration_s > 1 else 0.0


# ── single fight ─────────────────────────────────────────────────────────────


@dataclass
class Fight:
    index: int  # 1-based within the session
    start_ms: int  # first EnterCombat timestamp
    end_ms: int  # last ExitCombat timestamp
    events: list[LogEvent] = field(default_factory=list)
    player_stats: dict[str, PlayerFightStats] = field(default_factory=dict)
    # key: account_id

    @property
    def duration_s(self) -> float:
        """
        Fight length in seconds. Minimum 0.001 to avoid divide-by-zero.
        """
        return max((self.end_ms - self.start_ms) / 1000.0, 0.001)
    
    def set_temp_end_ms(self, timestamp_ms: int) -> None:
        """
        Temporarily set the fight's end_ms to a later timestamp (e.g. for
        calculating live DPS during an ongoing fight). Does not modify the
        actual end_ms field, so the original fight duration can still be used
        for final DPS calculations after the fight ends.
        """
        self.end_ms = max(self.end_ms, timestamp_ms)

    companion_stats: dict[str, PlayerFightStats] = field(default_factory=dict)
    # key: companion name (companions have no account_id)

    def get_or_create_stats(self, entity: Entity) -> PlayerFightStats:
        aid = entity.account_id or entity.name
        if aid not in self.player_stats:
            self.player_stats[aid] = PlayerFightStats(name=entity.name, account_id=aid)
        return self.player_stats[aid]

    def get_or_create_companion_stats(self, entity: Entity) -> PlayerFightStats:
        key = entity.name
        if key not in self.companion_stats:
            self.companion_stats[key] = PlayerFightStats(
                name=entity.name, account_id=key
            )
        return self.companion_stats[key]


# ── session ───────────────────────────────────────────────────────────────────


@dataclass
class CombatSession:
    fights: list[Fight] = field(default_factory=list)

    @property
    def fight_count(self) -> int:
        return len(self.fights)

    def all_player_ids(self) -> set[str]:
        ids: set[str] = set()
        for f in self.fights:
            ids.update(f.player_stats.keys())
        return ids

    def aggregate_player_stats(self, account_id: str) -> PlayerFightStats | None:
        """
        Sum stats for one player across all fights. Returns None if unknown.
        """
        fights_with_player = [f for f in self.fights if account_id in f.player_stats]
        if not fights_with_player:
            return None
        first = fights_with_player[0].player_stats[account_id]
        agg = PlayerFightStats(name=first.name, account_id=account_id)
        for f in fights_with_player:
            s = f.player_stats[account_id]
            agg.damage_out += s.damage_out
            agg.damage_in += s.damage_in
            agg.heal_out += s.heal_out
            agg.heal_in += s.heal_in
            agg.hit_count += s.hit_count
            agg.crit_count += s.crit_count
        return agg


# ── internal helpers ──────────────────────────────────────────────────────────


def _accumulate_stats(fight: Fight, event: LogEvent) -> None:
    """
    Update per-player stats in-place for a single event.
    """
    if event.effect_type != APPLY_EFFECT:
        return

    src = event.source
    tgt = event.target


    event.timestamp_ms

    if event.effect_name == DAMAGE:
        # Damage out: player → non-player target
        if is_friendly_player(src) and tgt is not None and tgt.kind != PLAYER:
            s = fight.get_or_create_stats(src)
            s.damage_out += event.effective_amount
            if event.effective_amount > 0:
                s.hit_count += 1
                if event.is_crit:
                    s.crit_count += 1

        # Damage in: non-player source → player target
        if is_friendly_player(tgt) and (src is None or src.kind != PLAYER):
            s = fight.get_or_create_stats(tgt)
            s.damage_in += event.effective_amount

        # Companion damage out: companion → non-player, non-companion target
        if (
            is_friendly_companion(src)
            and tgt is not None
            and tgt.kind not in (PLAYER, COMPANION)
        ):
            s = fight.get_or_create_companion_stats(src)
            s.damage_out += event.effective_amount
            if event.effective_amount > 0:
                s.hit_count += 1
                if event.is_crit:
                    s.crit_count += 1

        # Companion damage in: non-player/non-companion source → companion target
        if is_friendly_companion(tgt) and (
            src is None or src.kind not in (PLAYER, COMPANION)
        ):
            s = fight.get_or_create_companion_stats(tgt)
            s.damage_in += event.effective_amount

    elif event.effect_name == HEAL:
        # Heal out: player source
        if is_friendly_player(src):
            # effective heal = amount - overheal (mitigation holds overheal)
            net = max(event.amount - event.mitigation, 0)
            s = fight.get_or_create_stats(src)
            s.heal_out += net

        # Heal in: player target
        if is_friendly_player(tgt) and tgt is not src:
            net = max(event.amount - event.mitigation, 0)
            s = fight.get_or_create_stats(tgt)
            s.heal_in += net

        # Companion heal out: companion source
        if is_friendly_companion(src):
            net = max(event.amount - event.mitigation, 0)
            s = fight.get_or_create_companion_stats(src)
            s.heal_out += net

        # Companion heal in: companion target
        if is_friendly_companion(tgt) and tgt is not src:
            net = max(event.amount - event.mitigation, 0)
            s = fight.get_or_create_companion_stats(tgt)
            s.heal_in += net


# ── public API ────────────────────────────────────────────────────────────────


def segment_fights(
    events: list[LogEvent],
    grace_ms: int = _GRACE_MS,
) -> CombatSession:
    """
    Segment a flat event list into fights and return a CombatSession.

    Parameters
    ----------
    events:
        Ordered list of LogEvent objects (from log_parser.parse_file or
        parse_line).
    grace_ms:
        Milliseconds after the last ExitCombat to keep collecting trailing
        events into the closing fight. Default 900 ms.
    """
    session = CombatSession()

    # Players currently in combat (key: account_id, value: entity)
    open_players: dict[str, Entity] = {}
    current: Fight | None = None
    grace_end_ms: int = 0  # only valid when current is not None and open is empty

    for event in events:
        is_enter = (
            event.effect_type == EVENT
            and event.effect_name == ENTER_COMBAT
            and is_friendly_player(event.source)
        )
        is_exit = (
            event.effect_type == EVENT
            and event.effect_name == EXIT_COMBAT
            and is_friendly_player(event.source)
        )

        # ── Check whether we need to close/flush the grace window ────────────
        if current is not None and not open_players:
            # Grace window is active. Close the fight if:
            # (a) a new EnterCombat fires (always start fresh), or
            # (b) the event is past the grace window
            if is_enter or event.timestamp_ms > grace_end_ms:
                session.fights.append(current)
                current = None
                open_players = {}

        # ── Open a new fight ─────────────────────────────────────────────────
        if is_enter:
            aid = event.source.account_id or event.source.name
            if current is None:
                current = Fight(
                    index=len(session.fights) + 1,
                    start_ms=event.timestamp_ms,
                    end_ms=event.timestamp_ms,
                )
            open_players[aid] = event.source

        # ── Collect event into the current fight ──────────────────────────────
        if current is not None:
            current.events.append(event)
            _accumulate_stats(current, event)

        # ── Handle ExitCombat ────────────────────────────────────────────────
        if is_exit and current is not None:
            aid = event.source.account_id or event.source.name
            open_players.pop(aid, None)
            if not open_players:
                current.end_ms = event.timestamp_ms
                grace_end_ms = event.timestamp_ms + grace_ms

    # Flush any fight still open at end of file
    if current is not None:
        if not open_players:
            # Fight was properly closed — keep it
            pass
        else:
            # File ended mid-combat; close at last event's timestamp
            current.end_ms = events[-1].timestamp_ms if events else current.start_ms
        session.fights.append(current)

    return session
