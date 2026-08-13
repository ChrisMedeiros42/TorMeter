# ◢▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧◣
# ▧ - Lunar Edge Games                                          ▧
# ▧ - Tor Meter                                                 ▧
# ▧▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▧
# ▧ - Module: Main                                              ▧
# ▧ - Sub-Module: Handlers                                      ▧
# ▧ - Component: Operations                                     ▧
# ▧ - Sub-Component: Init                                       ▧
# ◥▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧◤

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from app.charts_overlay import ChartsOverlay
from app.combat_history_overlay import CombatHistoryOverlay
from app.constants import DEBUG
from app.grudges_overlay import NihilusBookOfGrudgesOverlay
from app.log_watcher import LogWatcher
from app.menu import TorMeterMenu
from app.observable import ObservableValue
from app.overlays import (
    DefenseWindow,
    DpsWindow,
    HealWindow,
    OverlayMasterWindow,
    SummaryWindow,
)
from app.preferences import Preferences
from app.session_loader import SessionLoader
from app.window import OverlayWindow


def main():
    app = QApplication(sys.argv)
    prefs = Preferences()

    # ── Observable visibility state — single source of truth ────────────────
    _vis_names = [
        "Overlay Master", "Summary", "DPS", "Defense",
        "Heal", "Combat History", "Charts", "Nihilus' Book of Grudges",
    ]
    vis_obs: dict[str, ObservableValue] = {
        name: ObservableValue(prefs.get(name).visible)
        for name in _vis_names
    }
    if DEBUG:
        vis_obs["Default Overlay"] = ObservableValue(prefs.get("Default Overlay").visible)

    windows: dict[str, OverlayWindow] = {
        "Overlay Master": OverlayMasterWindow(prefs, vis_obs),
        "Summary": SummaryWindow(prefs),
        "DPS": DpsWindow(prefs),
        "Defense": DefenseWindow(prefs),
        "Heal": HealWindow(prefs),
        "Combat History": CombatHistoryOverlay(prefs),
        "Charts": ChartsOverlay(prefs),
        "Nihilus' Book of Grudges": NihilusBookOfGrudgesOverlay(prefs),
    }

    if DEBUG:
        windows["Default Overlay"] = OverlayWindow(prefs)

    # Bind each window to its observable (sets initial visibility, wires show/hide)
    for name, win in windows.items():
        if name in vis_obs:
            win.bind_visible(vis_obs[name])

    windows["Overlay Master"].link_overlays(
        windows["Summary"],
        windows["DPS"],
        windows["Defense"],
        windows["Heal"],
        windows["Combat History"],
        windows["Charts"],
        windows["Nihilus' Book of Grudges"],
        vis_obs=vis_obs,
    )

    # ── Start log watcher and connect to all overlays ────────────────────────
    watcher = LogWatcher()
    for name in (
        "Overlay Master",
        "Summary",
        "DPS",
        "Defense",
        "Heal",
        "Combat History",
        "Charts",
        "Nihilus' Book of Grudges",
    ):
        win = windows[name]
        if hasattr(win, "receive_watcher"):
            win.receive_watcher(watcher)

    # ── Session loader (provides historical log files to History/Charts) ──────
    session_loader = SessionLoader()

    def _refresh_loader():
        session_loader.set_log_dir(watcher.log_dir, watcher.current_file)

    watcher.session_reset.connect(_refresh_loader)

    for name in ("Combat History", "Charts"):
        win = windows[name]
        if hasattr(win, "receive_session_loader"):
            win.receive_session_loader(session_loader)

    # Apply saved log folder if the user has set one explicitly
    if prefs.log_folder:

        watcher.set_log_dir(Path(prefs.log_folder))
    else:
        watcher.start()  # auto-discover default dirs

    # Initial loader scan (after watcher has resolved its log dir)
    _refresh_loader()

    menu = TorMeterMenu(prefs, vis_obs)
    for name, win in windows.items():
        menu.register_overlay(name, win)

    exit_code = 0
    try:
        exit_code = app.exec()
    except KeyboardInterrupt:
        # Allow Ctrl+C to close the app cleanly without a traceback.
        watcher.stop()
        exit_code = 0

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
