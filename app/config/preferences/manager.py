# ◢▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧◣
# ▧ - Lunar Edge Games                                        ▧
# ▧ - Tor Meter                                               ▧
# ▧▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▧
# ▧ - Module: Main                                            ▧
# ▧ - Component: Preferences                                  ▧
# ◥▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧◤

import sys
import json
from dataclasses import asdict
from pathlib import Path
from app.config.preferences.defaults import (
    DEFAULT_ENABLE_HOTKEY,
    DEFAULT_WINDOW_PREFS,
    WINDOW_NAMES,
)
from app.config.preferences.models import WindowPrefs

# When frozen (PyInstaller onefile), place UserPreferences.json next to the exe
# so users can edit it directly.  In development, keep it in data/ as before.
if getattr(sys, "frozen", False):
    _PREFS_PATH = Path(sys.executable).parent / "UserPreferences.json"
else:
    _PREFS_PATH = Path(__file__).parent.parent / "data" / "UserPreferences.json"

class Preferences:
    def __init__(self):
        self._data: dict[str, WindowPrefs] = {}
        self.enable_hotkey: str = DEFAULT_ENABLE_HOTKEY
        # ── Overlay Master settings ──────────────────────────────────────────
        self.character_name: str = ""
        self.log_folder: str = ""
        self.sum_name_size: int = 12
        self.sum_dps_size: int = 12
        self.sum_dps_show: bool = True
        self.sum_def_size: int = 12
        self.sum_def_show: bool = True
        self.sum_heal_size: int = 12
        self.sum_heal_show: bool = True
        self.dps_dps_size: int = 12
        self.dps_dps_show: bool = True
        self.dps_name_size: int = 12
        self.def_def_size: int = 12
        self.def_def_show: bool = True
        self.def_name_size: int = 12
        self.heal_heal_size: int = 12
        self.heal_heal_show: bool = True
        self.heal_name_size: int = 12
        # ── Overlay Master colors ────────────────────────────────────────────
        self.sum_name_color: str = "#FFFFFF"
        self.sum_dps_color: str = "#FF8C00"
        self.sum_def_color: str = "#4169E1"
        self.sum_heal_color: str = "#32CD32"
        self.dps_name_color: str = "#FFFFFF"
        self.dps_dps_color: str = "#FF8C00"
        self.def_name_color: str = "#FFFFFF"
        self.def_def_color: str = "#4169E1"
        self.heal_name_color: str = "#FFFFFF"
        self.heal_heal_color: str = "#32CD32"
        # Window control (base width + name column background)
        self.sum_win_width: int = 300
        self.sum_name_col_color: str = "transparent"
        self.sum_win_bg_alpha: int = 0
        self.sum_win_bg_color: str = "#000000"
        self.dps_win_width: int = 300
        self.dps_name_col_color: str = "transparent"
        self.dps_win_bg_alpha: int = 0
        self.dps_win_bg_color: str = "#000000"
        self.def_win_width: int = 300
        self.def_name_col_color: str = "transparent"
        self.def_win_bg_alpha: int = 0
        self.def_win_bg_color: str = "#000000"
        self.heal_win_width: int = 300
        self.heal_name_col_color: str = "transparent"
        self.heal_win_bg_alpha: int = 0
        self.heal_win_bg_color: str = "#000000"
        # ── Per-group: avg / total / bar border / score ──────────────────────
        self.sum_avg_show: bool = True
        self.sum_total_show: bool = True
        self.sum_bar_border_show: bool = True
        self.sum_bar_border_size: int = 1
        self.sum_bar_border_color: str = "#FFFFFF"
        self.sum_bar_bg_show: bool = True
        self.sum_bar_bg_size: int = 12
        self.sum_bar_bg_color: str = "#FFFFFF"
        self.sum_dps_bar_fg_show: bool = True
        self.sum_dps_bar_fg_size: int = 71
        self.sum_dps_bar_fg_color: str = "#7A2020"
        self.sum_def_bar_fg_show: bool = True
        self.sum_def_bar_fg_size: int = 71
        self.sum_def_bar_fg_color: str = "#1E3A7A"
        self.sum_heal_bar_fg_show: bool = True
        self.sum_heal_bar_fg_size: int = 71
        self.sum_heal_bar_fg_color: str = "#1E6B1E"
        self.sum_score_show: bool = True
        self.sum_score_size: int = 12
        self.sum_score_color: str = "#FFD700"
        self.sum_show_companions: bool = False
        self.sum_row_height: int = 24
        self.sum_outline_show: bool = True
        self.sum_outline_size: int = 1
        self.sum_outline_color: str = "#000000"
        self.dps_avg_show: bool = True
        self.dps_total_show: bool = True
        self.dps_bar_border_show: bool = True
        self.dps_bar_border_size: int = 1
        self.dps_bar_border_color: str = "#FFFFFF"
        self.dps_bar_bg_show: bool = True
        self.dps_bar_bg_size: int = 12
        self.dps_bar_bg_color: str = "#FFFFFF"
        self.dps_bar_fg_show: bool = True
        self.dps_bar_fg_size: int = 71
        self.dps_bar_fg_color: str = "#7A2020"
        self.dps_score_show: bool = True
        self.dps_score_size: int = 12
        self.dps_score_color: str = "#FFD700"
        self.dps_show_companions: bool = False
        self.dps_row_height: int = 24
        self.dps_outline_show: bool = True
        self.dps_outline_size: int = 1
        self.dps_outline_color: str = "#000000"
        self.def_avg_show: bool = True
        self.def_total_show: bool = True
        self.def_bar_border_show: bool = True
        self.def_bar_border_size: int = 1
        self.def_bar_border_color: str = "#FFFFFF"
        self.def_bar_bg_show: bool = True
        self.def_bar_bg_size: int = 12
        self.def_bar_bg_color: str = "#FFFFFF"
        self.def_bar_fg_show: bool = True
        self.def_bar_fg_size: int = 71
        self.def_bar_fg_color: str = "#1E3A7A"
        self.def_score_show: bool = True
        self.def_score_size: int = 12
        self.def_score_color: str = "#FFD700"
        self.def_show_companions: bool = False
        self.def_row_height: int = 24
        self.def_outline_show: bool = True
        self.def_outline_size: int = 1
        self.def_outline_color: str = "#000000"
        self.heal_avg_show: bool = True
        self.heal_total_show: bool = True
        self.heal_bar_border_show: bool = True
        self.heal_bar_border_size: int = 1
        self.heal_bar_border_color: str = "#FFFFFF"
        self.heal_bar_bg_show: bool = True
        self.heal_bar_bg_size: int = 12
        self.heal_bar_bg_color: str = "#FFFFFF"
        self.heal_bar_fg_show: bool = True
        self.heal_bar_fg_size: int = 71
        self.heal_bar_fg_color: str = "#1E6B1E"
        self.heal_score_show: bool = True
        self.heal_score_size: int = 12
        self.heal_score_color: str = "#FFD700"
        self.heal_show_companions: bool = False
        self.heal_row_height: int = 24
        self.heal_outline_show: bool = True
        self.heal_outline_size: int = 1
        self.heal_outline_color: str = "#000000"
        self.display_keep_seconds: int = 120
        # ── Overlay Master background ──────────────────────────────────────────────
        self.om_win_bg_alpha: int = 0
        self.om_win_bg_color: str = "#14141E"
        # ── Combat History overlay settings ────────────────────────────────────────
        self.coh_win_width: int = 380
        self.coh_win_height: int = 600
        self.coh_win_bg_alpha: int = 0
        self.coh_win_bg_color: str = "#000000"
        self.coh_name_size: int = 10
        self.coh_name_color: str = "#FFFFFF"
        self.coh_stat_size: int = 10
        self.coh_list_height: int = 420
        self.coh_label_size: int = 10
        # ── Charts overlay settings ───────────────────────────────────────────────
        self.cht_win_width: int = 300
        self.cht_win_height: int = 500
        self.cht_win_bg_alpha: int = 0
        self.cht_win_bg_color: str = "#000000"
        self.cht_name_size: int = 10
        self.cht_name_color: str = "#FFFFFF"
        self.cht_me_color: str = "#1E90FF"
        self.cht_other_color: str = "#787878"
        self.cht_val_size: int = 10
        self.cht_label_size: int = 10
        self._load()

    def _load(self):
        if _PREFS_PATH.exists():
            raw = json.loads(_PREFS_PATH.read_text(encoding="utf-8"))
            windows = raw.get("windows", {})
            self.enable_hotkey = raw.get("enable_hotkey", DEFAULT_ENABLE_HOTKEY)
            om = raw.get("overlay_master", {})
            self.character_name = om.get("character_name", "")
            self.log_folder = om.get("log_folder", "")
            self.sum_name_size = om.get("sum_name_size", 12)
            self.sum_dps_size = om.get("sum_dps_size", 12)
            self.sum_dps_show = om.get("sum_dps_show", True)
            self.sum_def_size = om.get("sum_def_size", 12)
            self.sum_def_show = om.get("sum_def_show", True)
            self.sum_heal_size = om.get("sum_heal_size", 12)
            self.sum_heal_show = om.get("sum_heal_show", True)
            self.dps_dps_size = om.get("dps_dps_size", 12)
            self.dps_dps_show = om.get("dps_dps_show", True)
            self.dps_name_size = om.get("dps_name_size", 12)
            self.def_def_size = om.get("def_def_size", 12)
            self.def_def_show = om.get("def_def_show", True)
            self.def_name_size = om.get("def_name_size", 12)
            self.heal_heal_size = om.get("heal_heal_size", 12)
            self.heal_heal_show = om.get("heal_heal_show", True)
            self.heal_name_size = om.get("heal_name_size", 12)
            self.sum_name_color = om.get("sum_name_color", "#FFFFFF")
            self.sum_dps_color = om.get("sum_dps_color", "#FF8C00")
            self.sum_def_color = om.get("sum_def_color", "#4169E1")
            self.sum_heal_color = om.get("sum_heal_color", "#32CD32")
            self.dps_name_color = om.get("dps_name_color", "#FFFFFF")
            self.dps_dps_color = om.get("dps_dps_color", "#FF8C00")
            self.def_name_color = om.get("def_name_color", "#FFFFFF")
            self.def_def_color = om.get("def_def_color", "#4169E1")
            self.heal_name_color = om.get("heal_name_color", "#FFFFFF")
            self.heal_heal_color = om.get("heal_heal_color", "#32CD32")
            self.sum_win_width = om.get("sum_win_width", 300)
            self.sum_name_col_color = om.get("sum_name_col_color", "transparent")
            self.sum_win_bg_alpha = om.get("sum_win_bg_alpha", 0)
            self.sum_win_bg_color = om.get("sum_win_bg_color", "#000000")
            self.dps_win_width = om.get("dps_win_width", 300)
            self.dps_name_col_color = om.get("dps_name_col_color", "transparent")
            self.dps_win_bg_alpha = om.get("dps_win_bg_alpha", 0)
            self.dps_win_bg_color = om.get("dps_win_bg_color", "#000000")
            self.def_win_width = om.get("def_win_width", 300)
            self.def_name_col_color = om.get("def_name_col_color", "transparent")
            self.def_win_bg_alpha = om.get("def_win_bg_alpha", 0)
            self.def_win_bg_color = om.get("def_win_bg_color", "#000000")
            self.heal_win_width = om.get("heal_win_width", 300)
            self.heal_name_col_color = om.get("heal_name_col_color", "transparent")
            self.heal_win_bg_alpha = om.get("heal_win_bg_alpha", 0)
            self.heal_win_bg_color = om.get("heal_win_bg_color", "#000000")
            self.sum_avg_show = om.get("sum_avg_show", True)
            self.sum_total_show = om.get("sum_total_show", True)
            self.sum_bar_border_show = om.get("sum_bar_border_show", True)
            self.sum_bar_border_size = om.get("sum_bar_border_size", 1)
            self.sum_bar_border_color = om.get("sum_bar_border_color", "#FFFFFF")
            self.sum_bar_bg_show = om.get("sum_bar_bg_show", True)
            self.sum_bar_bg_size = om.get("sum_bar_bg_size", 12)
            self.sum_bar_bg_color = om.get("sum_bar_bg_color", "#FFFFFF")
            self.sum_dps_bar_fg_show = om.get("sum_dps_bar_fg_show", True)
            self.sum_dps_bar_fg_size = om.get("sum_dps_bar_fg_size", 71)
            self.sum_dps_bar_fg_color = om.get("sum_dps_bar_fg_color", "#7A2020")
            self.sum_def_bar_fg_show = om.get("sum_def_bar_fg_show", True)
            self.sum_def_bar_fg_size = om.get("sum_def_bar_fg_size", 71)
            self.sum_def_bar_fg_color = om.get("sum_def_bar_fg_color", "#1E3A7A")
            self.sum_heal_bar_fg_show = om.get("sum_heal_bar_fg_show", True)
            self.sum_heal_bar_fg_size = om.get("sum_heal_bar_fg_size", 71)
            self.sum_heal_bar_fg_color = om.get("sum_heal_bar_fg_color", "#1E6B1E")
            self.sum_score_show = om.get("sum_score_show", True)
            self.sum_score_size = om.get("sum_score_size", 12)
            self.sum_score_color = om.get("sum_score_color", "#FFD700")
            self.sum_show_companions = om.get("sum_show_companions", False)
            self.sum_row_height = om.get("sum_row_height", 24)
            self.sum_outline_show = om.get("sum_outline_show", True)
            self.sum_outline_size = om.get("sum_outline_size", 1)
            self.sum_outline_color = om.get("sum_outline_color", "#000000")
            self.dps_avg_show = om.get("dps_avg_show", True)
            self.dps_total_show = om.get("dps_total_show", True)
            self.dps_bar_border_show = om.get("dps_bar_border_show", True)
            self.dps_bar_border_size = om.get("dps_bar_border_size", 1)
            self.dps_bar_border_color = om.get("dps_bar_border_color", "#FFFFFF")
            self.dps_bar_bg_show = om.get("dps_bar_bg_show", True)
            self.dps_bar_bg_size = om.get("dps_bar_bg_size", 12)
            self.dps_bar_bg_color = om.get("dps_bar_bg_color", "#FFFFFF")
            self.dps_bar_fg_show = om.get("dps_bar_fg_show", True)
            self.dps_bar_fg_size = om.get("dps_bar_fg_size", 71)
            self.dps_bar_fg_color = om.get("dps_bar_fg_color", "#7A2020")
            self.dps_score_show = om.get("dps_score_show", True)
            self.dps_score_size = om.get("dps_score_size", 12)
            self.dps_score_color = om.get("dps_score_color", "#FFD700")
            self.dps_show_companions = om.get("dps_show_companions", False)
            self.dps_row_height = om.get("dps_row_height", 24)
            self.dps_outline_show = om.get("dps_outline_show", True)
            self.dps_outline_size = om.get("dps_outline_size", 1)
            self.dps_outline_color = om.get("dps_outline_color", "#000000")
            self.def_avg_show = om.get("def_avg_show", True)
            self.def_total_show = om.get("def_total_show", True)
            self.def_bar_border_show = om.get("def_bar_border_show", True)
            self.def_bar_border_size = om.get("def_bar_border_size", 1)
            self.def_bar_border_color = om.get("def_bar_border_color", "#FFFFFF")
            self.def_bar_bg_show = om.get("def_bar_bg_show", True)
            self.def_bar_bg_size = om.get("def_bar_bg_size", 12)
            self.def_bar_bg_color = om.get("def_bar_bg_color", "#FFFFFF")
            self.def_bar_fg_show = om.get("def_bar_fg_show", True)
            self.def_bar_fg_size = om.get("def_bar_fg_size", 71)
            self.def_bar_fg_color = om.get("def_bar_fg_color", "#1E3A7A")
            self.def_score_show = om.get("def_score_show", True)
            self.def_score_size = om.get("def_score_size", 12)
            self.def_score_color = om.get("def_score_color", "#FFD700")
            self.def_show_companions = om.get("def_show_companions", False)
            self.def_row_height = om.get("def_row_height", 24)
            self.def_outline_show = om.get("def_outline_show", True)
            self.def_outline_size = om.get("def_outline_size", 1)
            self.def_outline_color = om.get("def_outline_color", "#000000")
            self.heal_avg_show = om.get("heal_avg_show", True)
            self.heal_total_show = om.get("heal_total_show", True)
            self.heal_bar_border_show = om.get("heal_bar_border_show", True)
            self.heal_bar_border_size = om.get("heal_bar_border_size", 1)
            self.heal_bar_border_color = om.get("heal_bar_border_color", "#FFFFFF")
            self.heal_bar_bg_show = om.get("heal_bar_bg_show", True)
            self.heal_bar_bg_size = om.get("heal_bar_bg_size", 12)
            self.heal_bar_bg_color = om.get("heal_bar_bg_color", "#FFFFFF")
            self.heal_bar_fg_show = om.get("heal_bar_fg_show", True)
            self.heal_bar_fg_size = om.get("heal_bar_fg_size", 71)
            self.heal_bar_fg_color = om.get("heal_bar_fg_color", "#1E6B1E")
            self.heal_score_show = om.get("heal_score_show", True)
            self.heal_score_size = om.get("heal_score_size", 12)
            self.heal_score_color = om.get("heal_score_color", "#FFD700")
            self.heal_show_companions = om.get("heal_show_companions", False)
            self.heal_row_height = om.get("heal_row_height", 24)
            self.heal_outline_show = om.get("heal_outline_show", True)
            self.heal_outline_size = om.get("heal_outline_size", 1)
            self.heal_outline_color = om.get("heal_outline_color", "#000000")
            self.display_keep_seconds = om.get("display_keep_seconds", 120)
            self.om_win_bg_alpha = om.get("om_win_bg_alpha", 0)
            self.om_win_bg_color = om.get("om_win_bg_color", "#14141E")
            self.coh_win_width = om.get("coh_win_width", 380)
            self.coh_win_height = om.get("coh_win_height", 600)
            self.coh_win_bg_alpha = om.get("coh_win_bg_alpha", 0)
            self.coh_win_bg_color = om.get("coh_win_bg_color", "#000000")
            self.coh_name_size = om.get("coh_name_size", 10)
            self.coh_name_color = om.get("coh_name_color", "#FFFFFF")
            self.coh_stat_size = om.get("coh_stat_size", 10)
            self.coh_list_height = om.get("coh_list_height", 420)
            self.coh_label_size = om.get("coh_label_size", 10)
            self.cht_win_width = om.get("cht_win_width", 300)
            self.cht_win_height = om.get("cht_win_height", 500)
            self.cht_win_bg_alpha = om.get("cht_win_bg_alpha", 0)
            self.cht_win_bg_color = om.get("cht_win_bg_color", "#000000")
            self.cht_name_size = om.get("cht_name_size", 10)
            self.cht_name_color = om.get("cht_name_color", "#FFFFFF")
            self.cht_me_color = om.get("cht_me_color", "#1E90FF")
            self.cht_other_color = om.get("cht_other_color", "#787878")
            self.cht_val_size = om.get("cht_val_size", 10)
            self.cht_label_size = om.get("cht_label_size", 10)
        else:
            windows = {}

        for name in WINDOW_NAMES:
            entry = windows.get(name, DEFAULT_WINDOW_PREFS)
            self._data[name] = WindowPrefs(
                x=entry.get("x", DEFAULT_WINDOW_PREFS["x"]),
                y=entry.get("y", DEFAULT_WINDOW_PREFS["y"]),
                default_x=entry.get("default_x", DEFAULT_WINDOW_PREFS["default_x"]),
                default_y=entry.get("default_y", DEFAULT_WINDOW_PREFS["default_y"]),
                expand=entry.get("expand", DEFAULT_WINDOW_PREFS["expand"]),
                anchor=entry.get("anchor", DEFAULT_WINDOW_PREFS["anchor"]),
                visible=entry.get("visible", True),
            )

    def get(self, window_name: str) -> WindowPrefs:
        return self._data.get(window_name, WindowPrefs(**DEFAULT_WINDOW_PREFS))

    def set_window_visible(self, window_name: str, visible: bool):
        if window_name in self._data:
            self._data[window_name].visible = visible
            self.save()

    def set_position(self, window_name: str, x: int, y: int):
        if window_name in self._data:
            self._data[window_name].x = x
            self._data[window_name].y = y
        else:
            self._data[window_name] = WindowPrefs(
                x=x,
                y=y,
                default_x=DEFAULT_WINDOW_PREFS["default_x"],
                default_y=DEFAULT_WINDOW_PREFS["default_y"],
                expand="down",
                anchor="top-left",
            )
        self.save()

    def save(self):
        payload = {
            "enable_hotkey": self.enable_hotkey,
            "overlay_master": {
                "character_name": self.character_name,
                "log_folder": self.log_folder,
                "sum_name_size": self.sum_name_size,
                "sum_dps_size": self.sum_dps_size,
                "sum_dps_show": self.sum_dps_show,
                "sum_def_size": self.sum_def_size,
                "sum_def_show": self.sum_def_show,
                "sum_heal_size": self.sum_heal_size,
                "sum_heal_show": self.sum_heal_show,
                "dps_dps_size": self.dps_dps_size,
                "dps_dps_show": self.dps_dps_show,
                "dps_name_size": self.dps_name_size,
                "def_def_size": self.def_def_size,
                "def_def_show": self.def_def_show,
                "def_name_size": self.def_name_size,
                "heal_heal_size": self.heal_heal_size,
                "heal_heal_show": self.heal_heal_show,
                "heal_name_size": self.heal_name_size,
                "sum_name_color": self.sum_name_color,
                "sum_dps_color": self.sum_dps_color,
                "sum_def_color": self.sum_def_color,
                "sum_heal_color": self.sum_heal_color,
                "dps_name_color": self.dps_name_color,
                "dps_dps_color": self.dps_dps_color,
                "def_name_color": self.def_name_color,
                "def_def_color": self.def_def_color,
                "heal_name_color": self.heal_name_color,
                "heal_heal_color": self.heal_heal_color,
                "sum_win_width": self.sum_win_width,
                "sum_name_col_color": self.sum_name_col_color,
                "sum_win_bg_alpha": self.sum_win_bg_alpha,
                "sum_win_bg_color": self.sum_win_bg_color,
                "dps_win_width": self.dps_win_width,
                "dps_name_col_color": self.dps_name_col_color,
                "dps_win_bg_alpha": self.dps_win_bg_alpha,
                "dps_win_bg_color": self.dps_win_bg_color,
                "def_win_width": self.def_win_width,
                "def_name_col_color": self.def_name_col_color,
                "def_win_bg_alpha": self.def_win_bg_alpha,
                "def_win_bg_color": self.def_win_bg_color,
                "heal_win_width": self.heal_win_width,
                "heal_name_col_color": self.heal_name_col_color,
                "heal_win_bg_alpha": self.heal_win_bg_alpha,
                "heal_win_bg_color": self.heal_win_bg_color,
                "sum_avg_show": self.sum_avg_show,
                "sum_total_show": self.sum_total_show,
                "sum_bar_border_show": self.sum_bar_border_show,
                "sum_bar_border_size": self.sum_bar_border_size,
                "sum_bar_border_color": self.sum_bar_border_color,
                "sum_bar_bg_show": self.sum_bar_bg_show,
                "sum_bar_bg_size": self.sum_bar_bg_size,
                "sum_bar_bg_color": self.sum_bar_bg_color,
                "sum_dps_bar_fg_show": self.sum_dps_bar_fg_show,
                "sum_dps_bar_fg_size": self.sum_dps_bar_fg_size,
                "sum_dps_bar_fg_color": self.sum_dps_bar_fg_color,
                "sum_def_bar_fg_show": self.sum_def_bar_fg_show,
                "sum_def_bar_fg_size": self.sum_def_bar_fg_size,
                "sum_def_bar_fg_color": self.sum_def_bar_fg_color,
                "sum_heal_bar_fg_show": self.sum_heal_bar_fg_show,
                "sum_heal_bar_fg_size": self.sum_heal_bar_fg_size,
                "sum_heal_bar_fg_color": self.sum_heal_bar_fg_color,
                "sum_score_show": self.sum_score_show,
                "sum_score_size": self.sum_score_size,
                "sum_score_color": self.sum_score_color,
                "sum_show_companions": self.sum_show_companions,
                "sum_row_height": self.sum_row_height,
                "sum_outline_show": self.sum_outline_show,
                "sum_outline_size": self.sum_outline_size,
                "sum_outline_color": self.sum_outline_color,
                "dps_avg_show": self.dps_avg_show,
                "dps_total_show": self.dps_total_show,
                "dps_bar_border_show": self.dps_bar_border_show,
                "dps_bar_border_size": self.dps_bar_border_size,
                "dps_bar_border_color": self.dps_bar_border_color,
                "dps_bar_bg_show": self.dps_bar_bg_show,
                "dps_bar_bg_size": self.dps_bar_bg_size,
                "dps_bar_bg_color": self.dps_bar_bg_color,
                "dps_bar_fg_show": self.dps_bar_fg_show,
                "dps_bar_fg_size": self.dps_bar_fg_size,
                "dps_bar_fg_color": self.dps_bar_fg_color,
                "dps_score_show": self.dps_score_show,
                "dps_score_size": self.dps_score_size,
                "dps_score_color": self.dps_score_color,
                "dps_show_companions": self.dps_show_companions,
                "dps_row_height": self.dps_row_height,
                "dps_outline_show": self.dps_outline_show,
                "dps_outline_size": self.dps_outline_size,
                "dps_outline_color": self.dps_outline_color,
                "def_avg_show": self.def_avg_show,
                "def_total_show": self.def_total_show,
                "def_bar_border_show": self.def_bar_border_show,
                "def_bar_border_size": self.def_bar_border_size,
                "def_bar_border_color": self.def_bar_border_color,
                "def_bar_bg_show": self.def_bar_bg_show,
                "def_bar_bg_size": self.def_bar_bg_size,
                "def_bar_bg_color": self.def_bar_bg_color,
                "def_bar_fg_show": self.def_bar_fg_show,
                "def_bar_fg_size": self.def_bar_fg_size,
                "def_bar_fg_color": self.def_bar_fg_color,
                "def_score_show": self.def_score_show,
                "def_score_size": self.def_score_size,
                "def_score_color": self.def_score_color,
                "def_show_companions": self.def_show_companions,
                "def_row_height": self.def_row_height,
                "def_outline_show": self.def_outline_show,
                "def_outline_size": self.def_outline_size,
                "def_outline_color": self.def_outline_color,
                "heal_avg_show": self.heal_avg_show,
                "heal_total_show": self.heal_total_show,
                "heal_bar_border_show": self.heal_bar_border_show,
                "heal_bar_border_size": self.heal_bar_border_size,
                "heal_bar_border_color": self.heal_bar_border_color,
                "heal_bar_bg_show": self.heal_bar_bg_show,
                "heal_bar_bg_size": self.heal_bar_bg_size,
                "heal_bar_bg_color": self.heal_bar_bg_color,
                "heal_bar_fg_show": self.heal_bar_fg_show,
                "heal_bar_fg_size": self.heal_bar_fg_size,
                "heal_bar_fg_color": self.heal_bar_fg_color,
                "heal_score_show": self.heal_score_show,
                "heal_score_size": self.heal_score_size,
                "heal_score_color": self.heal_score_color,
                "heal_show_companions": self.heal_show_companions,
                "heal_row_height": self.heal_row_height,
                "heal_outline_show": self.heal_outline_show,
                "heal_outline_size": self.heal_outline_size,
                "heal_outline_color": self.heal_outline_color,
                "display_keep_seconds": self.display_keep_seconds,
                "om_win_bg_alpha": self.om_win_bg_alpha,
                "om_win_bg_color": self.om_win_bg_color,
                "coh_win_width": self.coh_win_width,
                "coh_win_height": self.coh_win_height,
                "coh_win_bg_alpha": self.coh_win_bg_alpha,
                "coh_win_bg_color": self.coh_win_bg_color,
                "coh_name_size": self.coh_name_size,
                "coh_name_color": self.coh_name_color,
                "coh_stat_size": self.coh_stat_size,
                "coh_list_height": self.coh_list_height,
                "coh_label_size": self.coh_label_size,
                "cht_win_width": self.cht_win_width,
                "cht_win_height": self.cht_win_height,
                "cht_win_bg_alpha": self.cht_win_bg_alpha,
                "cht_win_bg_color": self.cht_win_bg_color,
                "cht_name_size": self.cht_name_size,
                "cht_name_color": self.cht_name_color,
                "cht_me_color": self.cht_me_color,
                "cht_other_color": self.cht_other_color,
                "cht_val_size": self.cht_val_size,
                "cht_label_size": self.cht_label_size,
            },
            "windows": {name: asdict(prefs) for name, prefs in self._data.items()},
        }
        _PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
        _PREFS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
