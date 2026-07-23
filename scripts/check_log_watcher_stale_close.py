"""Quick guard check for stale-fight close behavior in LogWatcher.

Run manually:
  c:/GitHub/TorMeter/.venv/Scripts/python.exe scripts/check_log_watcher_stale_close.py
"""

from __future__ import annotations

import time
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PyQt6.QtCore import QCoreApplication

from app.log_parser import parse_file
from app.log_watcher import LogWatcher


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise RuntimeError(msg)


def main() -> None:
    app = QCoreApplication.instance() or QCoreApplication([])

    log_path = Path("c:/GitHub/TorMeter/data/combatlogs/combat_2026-07-21_21_27_11_225648.txt")
    _assert(log_path.exists(), f"Missing sample log: {log_path}")

    watcher = LogWatcher(log_dir=log_path.parent)
    watcher.stop()  # keep this script deterministic

    events = parse_file(str(log_path))
    _assert(len(events) > 0, "No events parsed from sample log")

    # Ingest progressively and stop at the first point where a live fight is open.
    opened = False
    for i in range(0, len(events), 120):
        watcher._ingest(events[i : i + 120])
        if watcher.current_fight is not None:
            opened = True
            break

    _assert(opened and watcher.current_fight is not None, "Expected an open fight during stream ingest")

    # With improved segmentation, replay may end with no open fight. If it does
    # end open, force stale timing and ensure close guard works.
    if watcher.current_fight is not None:
        watcher._current_fight_last_event_wall = time.monotonic() - 21
        watcher._current_fight_last_damage_wall = time.monotonic() - 21
        watcher._last_event_ts_ms = watcher.current_fight.end_ms
        watcher._poll()

    _assert(watcher.current_fight is None, "Stale guard failed: fight still open")
    _assert(len(watcher.session.fights) >= 1, "Expected at least one closed fight after replay")

    watcher.stop()
    watcher.deleteLater()
    app.processEvents()

    print("PASS: LogWatcher stale-close guard is active.")


if __name__ == "__main__":
    main()
