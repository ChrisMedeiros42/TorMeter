# ◢▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧◣
# ▧ - Lunar Edge Games                                        ▧
# ▧ - Tor Meter                                               ▧
# ▧▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▧
# ▧ - Module: Main                                            ▧
# ▧ - Component: Session Loader                               ▧
# ◥▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧◤

"""
session_loader.py — Discover and lazily parse previous SWTOR combat log files.

Scans the configured log directory for all .txt combat log files, orders them
by modification time (newest last = highest session number), and parses each
on first access.  The current (live) log file is always excluded so it never
conflicts with the live LogWatcher session.

Usage
-----
    loader = SessionLoader()
    loader.set_log_dir(path, current_file=watcher_file)
    loader.sessions_changed.connect(my_slot)

    for entry in loader.entries:
        print(entry.label, entry.session.fight_count)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

from app.combat_session import CombatSession, segment_fights
from app.log_parser import parse_file


@dataclass
class SessionEntry:
    """
    One historical log file → parsed CombatSession (lazy).
    """

    label: str  # e.g. "Session 3 — 2026-06-01"
    path: Path
    _session: CombatSession | None = field(default=None, repr=False)

    @property
    def session(self) -> CombatSession:
        if self._session is None:
            try:
                events = parse_file(str(self.path))
                self._session = segment_fights(events)
            except Exception:  # noqa: BLE001
                self._session = CombatSession()
        return self._session


class SessionLoader(QObject):
    """
    Discovers all historical log files and exposes them as SessionEntry objects.

    Call ``set_log_dir`` whenever the log directory changes (or when the active
    file changes) to refresh the entry list.  ``sessions_changed`` is emitted
    whenever the list is rebuilt.
    """

    sessions_changed: pyqtSignal = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._entries: list[SessionEntry] = []
        self._log_dir: Path | None = None
        self._current_file: Path | None = None

    # ── public API ────────────────────────────────────────────────────────────

    @property
    def entries(self) -> list[SessionEntry]:
        """
        Ordered list of historical sessions, newest first (index 0 = most recent).
        """
        return list(self._entries)

    def set_log_dir(
        self, log_dir: Path | None, current_file: Path | None = None
    ) -> None:
        """
        Scan ``log_dir`` and rebuild the entry list.

        Parameters
        ----------
        log_dir:
            Directory that contains SWTOR combat log .txt files.
        current_file:
            The file currently being tailed by the live LogWatcher.  It is
            excluded from the historical list.
        """
        self._log_dir = log_dir
        self._current_file = current_file
        self._rebuild()

    def refresh(self, current_file: Path | None = None) -> None:
        """
        Re-scan the directory (e.g. after a new log file appears).
        """
        if current_file is not None:
            self._current_file = current_file
        self._rebuild()

    # ── internal ─────────────────────────────────────────────────────────────

    def _rebuild(self) -> None:
        self._entries = []
        if not self._log_dir or not self._log_dir.is_dir():
            self.sessions_changed.emit()
            return

        candidates = sorted(
            self._log_dir.glob("*.txt"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,  # newest first
        )
        # Exclude the currently-watched file
        historical = [
            p
            for p in candidates
            if self._current_file is None or p.resolve() != self._current_file.resolve()
        ]

        from datetime import datetime

        _MAX_BYTES = 100 * 1024 * 1024  # 100 MB total
        total_bytes = 0
        session_num = 1
        for path in historical:
            file_size = path.stat().st_size
            if total_bytes + file_size > _MAX_BYTES:
                break
            # Parse eagerly so we can skip empty logs
            try:
                events = parse_file(str(path))
                session = segment_fights(events)
            except Exception:  # noqa: BLE001
                continue
            if session.fight_count == 0:
                continue
            total_bytes += file_size
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
            label = f"Prev Session {session_num} — {mtime.strftime('%Y-%m-%d')}"
            entry = SessionEntry(label=label, path=path)
            entry._session = session  # already parsed, skip lazy load
            self._entries.append(entry)
            session_num += 1

        self.sessions_changed.emit()
