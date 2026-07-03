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
    EVENT,
    ENTER_COMBAT,
    EXIT_COMBAT,
    LogEvent,
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
        self._debug_worker: QThread | None = None

        # Track the most recent log timestamp and when it was seen in wall time.
        # This lets us advance live fight duration even during short line gaps.
        self._last_event_ts_ms: int | None = None
        self._last_event_wall: float | None = None

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)

        if log_dir:
            self.set_log_dir(log_dir)
        else:
            for d in _DEFAULT_LOG_DIRS:
                if d.is_dir():
                    self.set_log_dir(d)
                    break

    # ── public API ────────────────────────────────────────────────────────────

    def set_log_dir(self, path: Path) -> None:
        self._log_dir = Path(path)
        self._pick_newest_file()
        interval = _POLL_ACTIVE_MS if self._file else _POLL_IDLE_MS
        self._timer.start(interval)

    def start(self) -> None:
        """Start polling (called automatically by set_log_dir; also usable standalone)."""
        if not self._timer.isActive():
            self._timer.start(_POLL_IDLE_MS)

    def stop(self) -> None:
        self._timer.stop()

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
                    else:
                        self.fight_updated.emit(self._current_fight)
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

            # ── Open new fight ────────────────────────────────────────────────
            if is_enter:
                aid = event.source.account_id or event.source.name
                if self._current_fight is None:
                    self._current_fight = Fight(
                        index=len(self._session.fights) + 1,
                        start_ms=event.timestamp_ms,
                        end_ms=event.timestamp_ms,
                    )
                    self.fight_opened.emit(self._current_fight)
                self._open_players[aid] = event.source

            # ── Collect event ─────────────────────────────────────────────────
            if self._current_fight is not None:
                self._current_fight.set_temp_end_ms(event.timestamp_ms)
                self._current_fight.events.append(event)
                _accumulate_stats(self._current_fight, event)

            # ── Exit combat ───────────────────────────────────────────────────
            if is_exit and self._current_fight is not None:
                aid = event.source.account_id or event.source.name
                self._open_players.pop(aid, None)
                if not self._open_players:
                    self._current_fight.end_ms = event.timestamp_ms
                    self._grace_end_ms = event.timestamp_ms + _GRACE_MS

        # Emit update for current live fight after processing the batch
        if self._current_fight is not None:
            self.fight_updated.emit(self._current_fight)
