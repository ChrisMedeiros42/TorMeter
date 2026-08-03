"""Rebuild Grudges.json from historical combat logs.

Usage examples:
  c:/GitHub/TorMeter/.venv/Scripts/python.exe scripts/rebuild_grudges.py
  c:/GitHub/TorMeter/.venv/Scripts/python.exe scripts/rebuild_grudges.py --character "Tainted Juice"
  c:/GitHub/TorMeter/.venv/Scripts/python.exe scripts/rebuild_grudges.py --all-characters
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.combat_session import segment_fights
from app.log_parser import parse_file
from app.overlays_grudges.store import GrudgesStore
from app.preferences import Preferences


def _valid_character_name(name: str | None) -> str | None:
    text = (name or "").strip()
    if not text or text.casefold() == "me":
        return None
    return text


def _iter_log_files(log_dir: Path) -> list[Path]:
    return sorted(
        (p for p in log_dir.glob("*.txt") if p.is_file()),
        key=lambda p: (p.stat().st_mtime, p.name.casefold()),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rebuild Grudges.json from combat logs")
    parser.add_argument(
        "--logs-dir",
        default=str(ROOT / "data" / "combatlogs"),
        help="Folder containing SWTOR combat log .txt files",
    )
    parser.add_argument(
        "--character",
        default="",
        help="Only rebuild grudges for this character name",
    )
    parser.add_argument(
        "--all-characters",
        action="store_true",
        help="Rebuild grudges for every player seen in fights",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()

    logs_dir = Path(args.logs_dir).expanduser().resolve()
    if not logs_dir.exists() or not logs_dir.is_dir():
        print(f"ERROR: logs directory not found: {logs_dir}")
        return 1

    prefs = Preferences()
    selected_character = _valid_character_name(args.character) or _valid_character_name(
        prefs.character_name
    )

    if not args.all_characters and selected_character is None:
        print(
            "ERROR: No valid character name available. Set Overlay Master character name "
            "or pass --character."
        )
        return 1

    files = _iter_log_files(logs_dir)
    if not files:
        print(f"ERROR: No .txt log files found in {logs_dir}")
        return 1

    store = GrudgesStore()
    if args.all_characters:
        store.clear_all(persist=False)
    else:
        store.clear_character(selected_character or "", persist=False)

    files_processed = 0
    fights_processed = 0
    fights_recorded = 0

    for log_file in files:
        events = parse_file(str(log_file))
        if not events:
            continue
        files_processed += 1
        session = segment_fights(events)
        if not session.fights:
            continue

        for fight in session.fights:
            fights_processed += 1
            if args.all_characters:
                names = {
                    _valid_character_name(stats.name)
                    for stats in fight.player_stats.values()
                }
                for name in (n for n in names if n):
                    if store.record_fight(name, fight):
                        fights_recorded += 1
            else:
                if store.record_fight(selected_character or "", fight):
                    fights_recorded += 1

    store.save()

    scope = "all characters" if args.all_characters else selected_character
    print("Grudges rebuild complete")
    print(f"Scope: {scope}")
    print(f"Logs scanned: {len(files)}")
    print(f"Logs parsed: {files_processed}")
    print(f"Fights processed: {fights_processed}")
    print(f"Fight records written: {fights_recorded}")
    print(f"Output: {store.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
