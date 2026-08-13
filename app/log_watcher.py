# ◢▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧◣
# ▧ - Lunar Edge Games                                          ▧
# ▧ - Tor Meter                                                 ▧
# ▧▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▧
# ▧ - Module: App                                               ▧
# ▧ - Sub-Module: Log Watcher                                   ▧
# ◥▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧◤

"""log_watcher.py — Tail the latest SWTOR combat log and drive live session state.

Watches the combatlogs directory for the newest .txt file.  Every poll tick
it reads any new lines, parses them, and feeds them into the live
CombatSession.  Emits Qt signals so overlay windows can refresh.

Signals
-------
  events_parsed(list[LogEvent])  — new events appended this tick
  fight_opened(Fight)            — a new fight has started
  fight_updated(Fight)           — live stats changed mid-fight
  fight_closed(Fight)            — the current fight just closed
  session_reset()                — a new log file was picked up
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal

from app.combat_session import (
    CombatSession,
    Fight,
    _accumulate_stats,
    _GRACE_MS,
    segment_fights,
)
from app.constants import DEBUG
from app.log_parser import (
    APPLY_EFFECT,
    EVENT,
    ENTER_COMBAT,
    EXIT_COMBAT,
    DAMAGE,
    HEAL,
    LogEvent,
    is_friendly_companion,
    is_friendly_player,
    parse_line,
)

# Where SWTOR writes its logs on a typical Windows install and common Steam path.
# The user can override via set_log_dir().
_DEFAULT_LOG_DIRS: list[Path] = [
    Path.home() / "Documents" / "Star Wars - The Old Republic" / "CombatLogs",
    Path("C:/Program Files (x86)/Steam/steamapps/common/swtor/swtor/CombatLogs"),
    Path("C:/Program Files/Electronic Arts/Star Wars - The Old Republic/CombatLogs"),
]

# How often (ms) to poll for new lines while no active file is set.
_POLL_IDLE_MS = 2000
# How often (ms) to poll while a file is being actively tailed.
_POLL_ACTIVE_MS = 250

# After this many ms with no new log lines, consider a player "gone".
PLAYER_TIMEOUT_MS = 240_000

# After this many ms with no new events in an open fight, force-close it.
# Prevents ghost fights (e.g. opened by a late post-combat DoT tick) from
# keeping the fight alive and causing DPS to count down indefinitely.
_FIGHT_IDLE_CLOSE_MS = 5_000

# Additional guard: close an "open" fight if no damage activity is seen for
# too long, even if heal/proc log noise is still arriving.
_FIGHT_NO_DAMAGE_CLOSE_MS = 8_000

# When a fresh EnterCombat arrives after at least this damage gap, split into
# a new fight even if stale open-player state remains.
_ENTER_SPLIT_GAP_MS = 2_200


class LogWatcher(QObject):
    """Polls the newest combat log file and emits signals on parsed events."""

    events_parsed: pyqtSignal = pyqtSignal(list)  # list[LogEvent]
    fight_opened: pyqtSignal = pyqtSignal(object)  # Fight
    fight_updated: pyqtSignal = pyqtSignal(object)  # Fight
    fight_closed: pyqtSignal = pyqtSignal(object)  # Fight
    session_reset: pyqtSignal = pyqtSignal()

    def __init__(self, log_dir: Path | None = None, parent: QObject | None = None):
        super().__init__(parent)
        self._log_dir: Path | None = None
        self._file: Path | None = None
        self._pos: int = 0  # byte offset in the current file

        # Live session state (mirrors segment_fights logic but incremental)
        self._session = CombatSession()
        self._current_fight: Fight | None = None
        self._open_players: dict[str, object] = {}  # account_id → Entity
        self._grace_end_ms: int = 0

        # Per-player last-seen wall-clock time (for timeout tracking)
        self._player_last_seen: dict[str, float] = {}  # account_id → time.monotonic()

        # Wall-clock time of the most recent ExitCombat event seen.  Used to
        # suppress implicit fight-opens caused by late post-combat events (e.g.
        # DoT ticks that arrive after grace has expired).
        self._last_exit_wall: float = 0.0

        # Wall-clock time when the last event was added to _current_fight.
        # Used to detect and close idle fights even while new log lines arrive.
        self._current_fight_last_event_wall: float = 0.0
        self._current_fight_last_damage_wall: float = 0.0
        self._current_fight_last_damage_ts_ms: int | None = None
        self._debug_worker: QThread | None = None

        # Track the most recent log timestamp and when it was seen in wall time.
        # This lets us advance live fight duration even during short line gaps.
        self._last_event_ts_ms: int | None = None
        self._last_event_wall: float | None = None
        self._last_autodetect_scan_wall: float = 0.0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)

        if log_dir:
            self.set_log_dir(log_dir)
        else:
            self._try_auto_detect_log_dir()

    def _candidate_log_dirs(self) -> list[Path]:
        """Return likely SWTOR combat-log directories on Windows."""
        candidates: list[Path] = list(_DEFAULT_LOG_DIRS)

        home = Path.home()
        userprofile = Path(os.environ.get("USERPROFILE", str(home)))

        doc_roots = {
            home / "Documents",
            userprofile / "Documents",
        }

        for key in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
            v = os.environ.get(key)
            if v:
                doc_roots.add(Path(v) / "Documents")

        for od in home.glob("OneDrive*"):
            doc_roots.add(od / "Documents")

        # Common SWTOR location under user document libraries.
        for d in doc_roots:
            candidates.append(d / "Star Wars - The Old Republic" / "CombatLogs")

        # Some installs/write locations use AppData paths.
        local_app_data = os.environ.get("LOCALAPPDATA")
        app_data = os.environ.get("APPDATA")
        if local_app_data:
            candidates.append(
                Path(local_app_data) / "SWTOR" / "swtor" / "settings" / "CombatLogs"
            )
        if app_data:
            candidates.append(
                Path(app_data) / "SWTOR" / "swtor" / "settings" / "CombatLogs"
            )

        # Fallback scan for non-standard nesting (e.g., localized/renamed roots).
        # Throttle this expensive scan to once every ~15 seconds.
        now = time.monotonic()
        if now - self._last_autodetect_scan_wall >= 15:
            self._last_autodetect_scan_wall = now
            for d in doc_roots:
                if not d.is_dir():
                    continue
                try:
                    for found in d.rglob("CombatLogs"):
                        if found.is_dir():
                            candidates.append(found)
                    for found in d.rglob("combatlogs"):
                        if found.is_dir():
                            candidates.append(found)
                except OSError:
                    continue

        # Deduplicate while preserving order.
        unique: list[Path] = []
        seen: set[str] = set()
        for c in candidates:
            key = str(c).lower()
            if key not in seen:
                seen.add(key)
                unique.append(c)
        return unique

    def _try_auto_detect_log_dir(self) -> bool:
        """Try to bind to a known SWTOR combat-log directory.

        Returns True when a valid directory was found.
        """
        existing = [d for d in self._candidate_log_dirs() if d.is_dir()]
        if not existing:
            return False

        def _latest_log_mtime(dir_path: Path) -> float:
            latest = 0.0
            try:
                for f in dir_path.glob("*.txt"):
                    try:
                        latest = max(latest, f.stat().st_mtime)
                    except OSError:
                        continue
            except OSError:
                return 0.0
            return latest

        best = max(existing, key=_latest_log_mtime)
        if self._log_dir != best:
            self.set_log_dir(best)
        return True

    # ── public API ────────────────────────────────────────────────────────────

    def set_log_dir(self, path: Path) -> None:
        self._log_dir = Path(path)
        self._pick_newest_file()
        interval = _POLL_ACTIVE_MS if self._file else _POLL_IDLE_MS
        self._timer.start(interval)

    def start(self) -> None:
        """Start polling (called automatically by set_log_dir; also usable standalone)."""
        if self._log_dir is None:
            self._try_auto_detect_log_dir()
        if not self._timer.isActive():
            interval = _POLL_ACTIVE_MS if self._file else _POLL_IDLE_MS
            self._timer.start(interval)

    def stop(self) -> None:
        self._timer.stop()

    def is_running(self) -> bool:
        return self._timer.isActive()

    def pause_overlay_processing(self) -> bool:
        was_running = self._timer.isActive()
        if was_running:
            self._timer.stop()
        return was_running

    def resume_overlay_processing(self) -> None:
        self.start()

    @property
    def session(self) -> CombatSession:
        return self._session

    @property
    def log_dir(self) -> Path | None:
        return self._log_dir

    @property
    def current_file(self) -> Path | None:
        return self._file

    @property
    def current_fight(self) -> Fight | None:
        return self._current_fight

    @property
    def active_players(self) -> set[str]:
        """account_ids that have had a log event within PLAYER_TIMEOUT_MS."""
        now = time.monotonic()
        return {
            aid
            for aid, ts in self._player_last_seen.items()
            if (now - ts) * 1000 < PLAYER_TIMEOUT_MS
        }

    @property
    def player_last_seen(self) -> dict[str, float]:
        """Read-only view of account_id → monotonic timestamp of last real log event."""
        return self._player_last_seen

    # ── internal polling ──────────────────────────────────────────────────────

    def _pick_newest_file(self) -> bool:
        """Find the most-recently modified .txt in the log dir.  Returns True on change."""
        if not self._log_dir or not self._log_dir.is_dir():
            return False
        candidates = sorted(
            self._log_dir.glob("*.txt"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        newest = candidates[0] if candidates else None
        if newest != self._file:
            self._file = newest
            # Seek to EOF so we only tail *new* lines — the SessionLoader handles
            # historical content.  Reading the whole file on startup blocks the
            # Qt main thread and prevents hotkeys / UI from responding.
            try:
                self._pos = newest.stat().st_size if newest else 0
            except OSError:
                self._pos = 0
            self._session = CombatSession()
            self._current_fight = None
            self._open_players = {}
            self._grace_end_ms = 0
            self._player_last_seen = {}
            self._last_event_ts_ms = None
            self._last_event_wall = None
            self._last_exit_wall = 0.0
            self._current_fight_last_event_wall = 0.0
            self._current_fight_last_damage_wall = 0.0
            self._current_fight_last_damage_ts_ms = None
            self.session_reset.emit()
            if DEBUG and self._file:
                self._emit_last_fight_async(self._file)
            return True
        return False

    def _emit_last_fight_async(self, path: Path) -> None:
        """In DEBUG mode: parse the full log in a background thread and emit
        fight_updated for the most recent completed fight so overlays show data."""
        watcher = self

        class _Worker(QThread):
            def run(self):
                try:
                    from app.log_parser import parse_file
                    events = parse_file(str(path))
                    session = segment_fights(events)
                except Exception:
                    return
                if session.fights:
                    last = session.fights[-1]
                    watcher.fight_updated.emit(last)

        self._debug_worker = _Worker(self)  # keep reference alive
        self._debug_worker.start()

    def _poll(self) -> None:
        # If no directory is configured yet, keep trying auto-detection.
        if self._log_dir is None:
            if not self._try_auto_detect_log_dir():
                return

        # Recover when the configured directory disappears.
        if self._log_dir is not None and not self._log_dir.is_dir():
            self._log_dir = None
            self._file = None
            self._pos = 0
            if not self._try_auto_detect_log_dir():
                return

        # Check whether a newer file has appeared
        changed = self._pick_newest_file()
        if changed:
            self._timer.setInterval(_POLL_ACTIVE_MS if self._file else _POLL_IDLE_MS)

        if not self._file or not self._file.exists():
            return

        try:
            with self._file.open("r", encoding="utf-8", errors="replace") as fh:
                fh.seek(self._pos)
                raw_lines = fh.readlines()
                self._pos = fh.tell()
        except OSError:
            return

        # Force-close any fight that has been idle for too long, regardless of
        # whether new log lines are arriving (e.g. auto-attacks or DoTs keeping
        # the fight alive but the player is actually idle/AFK).
        if self._current_fight is not None and self._current_fight_last_event_wall > 0.0:
            now = time.monotonic()
            idle_ms = int((now - self._current_fight_last_event_wall) * 1000)
            no_dmg_ms = (
                int((now - self._current_fight_last_damage_wall) * 1000)
                if self._current_fight_last_damage_wall > 0.0
                else 0
            )
            if idle_ms > _FIGHT_IDLE_CLOSE_MS:
                self._last_exit_wall = now
                self._current_fight.end_ms = self._last_event_ts_ms or self._current_fight.end_ms
                self._session.fights.append(self._current_fight)
                self.fight_closed.emit(self._current_fight)
                self._current_fight = None
                self._open_players = {}
                self._grace_end_ms = 0
                self._current_fight_last_event_wall = 0.0
                self._current_fight_last_damage_wall = 0.0
                self._current_fight_last_damage_ts_ms = None
            elif no_dmg_ms > _FIGHT_NO_DAMAGE_CLOSE_MS:
                self._last_exit_wall = now
                self._current_fight.end_ms = self._last_event_ts_ms or self._current_fight.end_ms
                self._session.fights.append(self._current_fight)
                self.fight_closed.emit(self._current_fight)
                self._current_fight = None
                self._open_players = {}
                self._grace_end_ms = 0
                self._current_fight_last_event_wall = 0.0
                self._current_fight_last_damage_wall = 0.0
                self._current_fight_last_damage_ts_ms = None

        if not raw_lines:
            # No fresh lines this tick.
            # Keep live averages moving for the current open fight, and
            # finalize fights that passed grace with no trailing events.
            if self._current_fight is not None and self._last_event_wall is not None:
                now = time.monotonic()
                elapsed_ms = int((now - self._last_event_wall) * 1000)
                if elapsed_ms > 0 and self._last_event_ts_ms is not None:
                    projected_ts = self._last_event_ts_ms + elapsed_ms
                    self._current_fight.set_temp_end_ms(projected_ts)

                if not self._open_players:
                    # Fight already exited; close it once grace has elapsed.
                    if elapsed_ms > _GRACE_MS:
                        self._session.fights.append(self._current_fight)
                        self.fight_closed.emit(self._current_fight)
                        self._current_fight = None
                        self._open_players = {}
                        self._grace_end_ms = 0
                        self._current_fight_last_event_wall = 0.0
                        self._current_fight_last_damage_wall = 0.0
                        self._current_fight_last_damage_ts_ms = None
                    else:
                        self.fight_updated.emit(self._current_fight)
                elif elapsed_ms > _FIGHT_IDLE_CLOSE_MS:
                    # Fight still "open" (open_players not empty) but no new
                    # events for too long — force-close to prevent indefinite
                    # DPS countdown (e.g. ghost fight opened by a late DoT tick).
                    self._current_fight.end_ms = self._last_event_ts_ms or self._current_fight.end_ms
                    self._session.fights.append(self._current_fight)
                    self.fight_closed.emit(self._current_fight)
                    self._current_fight = None
                    self._open_players = {}
                    self._grace_end_ms = 0
                    self._current_fight_last_event_wall = 0.0
                    self._current_fight_last_damage_wall = 0.0
                    self._current_fight_last_damage_ts_ms = None
                else:
                    self.fight_updated.emit(self._current_fight)
            return

        new_events: list[LogEvent] = []
        for line in raw_lines:
            ev = parse_line(line)
            if ev is not None:
                new_events.append(ev)

        if not new_events:
            return

        self.events_parsed.emit(new_events)
        self._ingest(new_events)

    def _ingest(self, events: list[LogEvent]) -> None:
        """Update live session state for a batch of new events."""

        def _aid(entity) -> str | None:
            if entity is None or not is_friendly_player(entity):
                return None
            return entity.account_id or entity.name

        def _is_open_participant_event(ev: LogEvent) -> bool:
            """True when event involves currently open players or companions."""
            src_aid = _aid(ev.source)
            tgt_aid = _aid(ev.target)
            if src_aid in self._open_players or tgt_aid in self._open_players:
                return True

            # Companion events should count while any player is still marked in combat.
            if is_friendly_companion(ev.source) or is_friendly_companion(ev.target):
                return True

            return False

        def _is_fight_activity(ev: LogEvent) -> bool:
            """True when an event should keep an open fight alive."""
            if (
                ev.effect_type == EVENT
                and ev.effect_name in (ENTER_COMBAT, EXIT_COMBAT)
                and is_friendly_player(ev.source)
            ):
                return True
            if (
                ev.effect_type == APPLY_EFFECT
                and ev.effect_name in (DAMAGE, HEAL)
            ):
                if not (
                    is_friendly_player(ev.source)
                    or is_friendly_player(ev.target)
                    or is_friendly_companion(ev.source)
                    or is_friendly_companion(ev.target)
                ):
                    return False

                # While players are actively in combat, only accept events tied
                # to those open participants (or companions).
                if self._open_players:
                    return _is_open_participant_event(ev)

                # After all exits, only keep short trailing effects in grace.
                if self._current_fight is not None:
                    return ev.timestamp_ms <= self._grace_end_ms

                return False
            return False

        def _is_stat_relevant(ev: LogEvent) -> bool:
            """True when event should be collected into current fight stats/history."""
            if (
                ev.effect_type == EVENT
                and ev.effect_name in (ENTER_COMBAT, EXIT_COMBAT)
                and is_friendly_player(ev.source)
            ):
                return True
            if (
                ev.effect_type == EVENT
                and ev.effect_name == "Death"
                and (
                    is_friendly_player(ev.source)
                    or is_friendly_player(ev.target)
                    or is_friendly_companion(ev.source)
                    or is_friendly_companion(ev.target)
                )
            ):
                return True
            if (
                ev.effect_type == APPLY_EFFECT
                and ev.effect_name in (DAMAGE, HEAL)
                and (
                    is_friendly_player(ev.source)
                    or is_friendly_player(ev.target)
                    or is_friendly_companion(ev.source)
                    or is_friendly_companion(ev.target)
                )
            ):
                return True
            return False

        for event in events:
            self._last_event_ts_ms = event.timestamp_ms
            self._last_event_wall = time.monotonic()

            # Track per-player last-seen time
            if is_friendly_player(event.source):
                aid = event.source.account_id or event.source.name
                self._player_last_seen[aid] = time.monotonic()
            if is_friendly_player(event.target):
                aid = event.target.account_id or event.target.name
                self._player_last_seen[aid] = time.monotonic()

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

            # ── Grace window flush ────────────────────────────────────────────
            if self._current_fight is not None and not self._open_players:
                if is_enter or event.timestamp_ms > self._grace_end_ms:
                    self._session.fights.append(self._current_fight)
                    self.fight_closed.emit(self._current_fight)
                    self._current_fight = None
                    self._open_players = {}
                    self._current_fight_last_event_wall = 0.0

            # ── Open new fight ────────────────────────────────────────────────
            if is_enter:
                aid = event.source.account_id or event.source.name
                # If an EnterCombat arrives after a real damage lull, split the
                # previous fight even if stale open-player state remains.
                if (
                    self._current_fight is not None
                    and self._current_fight_last_damage_ts_ms is not None
                    and (event.timestamp_ms - self._current_fight_last_damage_ts_ms) > _ENTER_SPLIT_GAP_MS
                ):
                    self._session.fights.append(self._current_fight)
                    self.fight_closed.emit(self._current_fight)
                    self._current_fight = None
                    self._open_players = {}
                    self._grace_end_ms = 0
                    self._current_fight_last_event_wall = 0.0
                    self._current_fight_last_damage_wall = 0.0
                    self._current_fight_last_damage_ts_ms = None

                if self._current_fight is None:
                    self._current_fight = Fight(
                        index=len(self._session.fights) + 1,
                        start_ms=event.timestamp_ms,
                        end_ms=event.timestamp_ms,
                    )
                    self._current_fight_last_event_wall = time.monotonic()
                    self._current_fight_last_damage_wall = time.monotonic()
                    self._current_fight_last_damage_ts_ms = event.timestamp_ms
                    self.fight_opened.emit(self._current_fight)
                self._open_players[aid] = event.source

            # ── Implicit fight open (mid-combat start) ────────────────────────
            # If TorMeter missed the EnterCombat event (started while player was
            # already in combat), auto-open a fight on the first combat activity
            # so stats are not silently dropped.
            # Guard heal-only implicit opens briefly after ExitCombat to avoid
            # ghost fights from trailing HoTs/procs, but allow damage to reopen
            # immediately so real pulls are not dropped.
            _IMPLICIT_HEAL_COOLDOWN_S = 0.2
            if (
                self._current_fight is None
                and is_friendly_player(event.source)
                and event.effect_type == APPLY_EFFECT
                and event.effect_name in (DAMAGE, HEAL)
                and (
                    event.effect_name == DAMAGE
                    or (time.monotonic() - self._last_exit_wall) > _IMPLICIT_HEAL_COOLDOWN_S
                )
            ):
                self._current_fight = Fight(
                    index=len(self._session.fights) + 1,
                    start_ms=event.timestamp_ms,
                    end_ms=event.timestamp_ms,
                )
                aid = event.source.account_id or event.source.name
                self._open_players[aid] = event.source
                self._current_fight_last_event_wall = time.monotonic()
                self._current_fight_last_damage_wall = time.monotonic()
                self._current_fight_last_damage_ts_ms = event.timestamp_ms
                self.fight_opened.emit(self._current_fight)

            # ── Collect event ─────────────────────────────────────────────────
            if self._current_fight is not None:
                if _is_stat_relevant(event):
                    # When a friendly player contributes damage, treat them as
                    # an active participant even if EnterCombat was missed.
                    if event.effect_type == APPLY_EFFECT and event.effect_name == DAMAGE:
                        src_aid = _aid(event.source)
                        tgt_aid = _aid(event.target)
                        if src_aid is not None:
                            self._open_players.setdefault(src_aid, event.source)
                        if tgt_aid is not None:
                            self._open_players.setdefault(tgt_aid, event.target)

                    self._current_fight.set_temp_end_ms(event.timestamp_ms)
                    self._current_fight.events.append(event)
                    _accumulate_stats(self._current_fight, event)

                if _is_fight_activity(event):
                    self._current_fight_last_event_wall = time.monotonic()
                    if event.effect_type == APPLY_EFFECT and event.effect_name == DAMAGE:
                        self._current_fight_last_damage_wall = time.monotonic()
                        self._current_fight_last_damage_ts_ms = event.timestamp_ms

            # ── Exit combat ───────────────────────────────────────────────────
            if is_exit and self._current_fight is not None:
                self._last_exit_wall = time.monotonic()
                aid = event.source.account_id or event.source.name
                self._open_players.pop(aid, None)
                if not self._open_players:
                    self._current_fight.end_ms = event.timestamp_ms
                    self._grace_end_ms = event.timestamp_ms + _GRACE_MS
            elif is_exit:
                # ExitCombat with no open fight — still record the wall time so
                # the implicit-open cooldown is respected.
                self._last_exit_wall = time.monotonic()

        # Emit update for current live fight after processing the batch
        if self._current_fight is not None:
            self.fight_updated.emit(self._current_fight)
