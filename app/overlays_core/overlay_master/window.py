# ◢▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧◣
# ▧ - Lunar Edge Games                                          ▧
# ▧ - Tor Meter                                                 ▧
# ▧▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▧
# ▧ - Module: Overlays Core                                     ▧
# ▧ - Sub-Module: Overlay Master                                ▧
# ▧ - Component: Window                                         ▧
# ◥▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧◤

"""Overlay master window implementation."""

from __future__ import annotations

import time

from PyQt6.QtCore import Qt, QRect, QSize, QTimer
from PyQt6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPen
from PyQt6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from app.combat_session import Fight, PlayerFightStats
from app.observable import ObservableValue
from app.window import OverlayWindow

from ..helpers import (
    _EDIT_STYLE,
    _LABEL_STYLE,
    _AutoScrollArea,
    _ColorButton,
    _OutlineLabel,
    _RotatedLabel,
    _SectionFrame,
    _add_grid_row,
    _make_section_inner,
    _make_show_hide_wrapper,
    _section,
)

class OverlayMasterWindow(OverlayWindow):
    title = "Overlay Master"
    window_name = "Overlay Master"
    _min_content_width = 300

    def __init__(self, prefs=None, vis_obs: "dict[str, ObservableValue] | None" = None):
        self._vis_obs_dict: dict[str, ObservableValue] = vis_obs or {}
        super().__init__(prefs)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        p = self._prefs
        alpha = getattr(p, "om_win_bg_alpha", 0) if p else 0
        if alpha > 0:
            c = QColor(getattr(p, "om_win_bg_color", "#14141E") if p else "#14141E")
            c.setAlpha(max(0, min(255, alpha)))
        else:
            c = QColor(20, 20, 30, 200)
        painter.setBrush(c)
        painter.setPen(QPen(QColor("#6ab8ff"), 1))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 5, 5)
        super().paintEvent(event)

    def apply_win_bg_alpha(self, v: int) -> None:
        p = self._prefs
        if p:
            p.om_win_bg_alpha = v
        self.update()

    def apply_win_bg_color(self, c: str) -> None:
        p = self._prefs
        if p:
            p.om_win_bg_color = c
        self.update()

    def _resize_to_content(self):
        """Invalidate inner section layout before delegating to base resize."""
        sc = getattr(self, "_sections_container", None)
        if sc is not None:
            lay = sc.layout()
            if lay:
                lay.invalidate()
                lay.activate()
            sa = getattr(self, "_scroll_area", None)
            if sa is not None:
                sa.updateGeometry()
        super()._resize_to_content()

    def _setup_content(self):
        p = self._prefs
        self._linked: dict = {}
        self._vis_checks: dict = {}  # key → QCheckBox for Show/Hide rows
        self._win_size_sliders: dict = {}  # key → {"width": QSlider, "height": QSlider}
        self._watcher_status_label: QLabel | None = None
        self._watcher_debug_label: QLabel | None = None
        self._watcher_debug_checkbox: QCheckBox | None = None
        self._watcher_status_timer: QTimer | None = None

        # ── Title ──────────────────────────────────────────────────────────────
        title_label = QLabel(self.title, self._content)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: white;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        title_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self._layout.addWidget(title_label)

        # ── Character name row ───────────────────────────────────────────────
        char_row = QWidget()
        char_row.setStyleSheet("background: transparent;")
        char_l = QHBoxLayout(char_row)
        char_l.setContentsMargins(2, 2, 2, 2)
        char_l.setSpacing(6)
        char_lbl = QLabel("My Character Name:")
        char_lbl.setStyleSheet(_LABEL_STYLE)
        char_l.addWidget(char_lbl)
        char_edit = QLineEdit()
        char_edit.setStyleSheet(_EDIT_STYLE)
        if p:
            char_edit.setText(p.character_name)

        def _save_char():
            name = char_edit.text().strip()
            char_edit.setText(name)
            if p:
                p.character_name = name
                p.save()
            self._notify_all("apply_character_name", name)

        char_edit.editingFinished.connect(_save_char)
        char_edit.returnPressed.connect(_save_char)
        char_l.addWidget(char_edit, 1)
        self._layout.addWidget(char_row)

        # ── Log folder row ───────────────────────────────────────────────────
        log_row = QWidget()
        log_row.setStyleSheet("background: transparent;")
        log_l = QHBoxLayout(log_row)
        log_l.setContentsMargins(2, 2, 2, 2)
        log_l.setSpacing(6)
        log_lbl = QLabel("Combat Logs Folder:")
        log_lbl.setStyleSheet(_LABEL_STYLE)
        log_l.addWidget(log_lbl)
        log_edit = QLineEdit()
        log_edit.setStyleSheet(_EDIT_STYLE)
        log_edit.setReadOnly(True)
        log_edit.setPlaceholderText("(auto-detected)")
        if p and p.log_folder:
            log_edit.setText(p.log_folder)
        log_l.addWidget(log_edit, 1)
        browse_btn = QPushButton("...")
        browse_btn.setFixedWidth(28)
        browse_btn.setStyleSheet(
            "color: white; background: rgba(255,255,255,30);"
            "border: 1px solid rgba(255,255,255,60); border-radius: 3px;"
            "font-size: 10px; padding: 0;"
        )

        def _browse_log_folder():
            from pathlib import Path

            chosen = QFileDialog.getExistingDirectory(
                self,
                "Select Combat Logs Folder",
                log_edit.text() or str(Path.home()),
                QFileDialog.Option.ShowDirsOnly,
            )
            if chosen:
                log_edit.setText(chosen)
                if p:
                    p.log_folder = chosen
                    p.save()
                watcher = getattr(self, "_watcher", None)
                if watcher is not None:
                    watcher.set_log_dir(Path(chosen))

        browse_btn.clicked.connect(_browse_log_folder)
        log_l.addWidget(browse_btn)
        self._layout.addWidget(log_row)

        # Live watcher status for troubleshooting auto-detect and active file.
        watcher_status = QLabel("Log Watcher: waiting for watcher...")
        watcher_status.setStyleSheet(
            "color: rgba(255,255,255,180); font-size: 10px; background: transparent;"
        )
        watcher_status.setWordWrap(True)
        watcher_status.setContentsMargins(4, 0, 4, 2)
        self._watcher_status_label = watcher_status
        self._layout.addWidget(watcher_status)

        watcher_debug_toggle = QCheckBox("Show Watcher Debug")
        watcher_debug_toggle.setStyleSheet(
            "color: rgba(255,255,255,200); font-size: 9px; background: transparent;"
        )
        watcher_debug_toggle.setChecked(bool(getattr(p, "om_show_watcher_debug", False) if p else False))

        def _toggle_watcher_debug(checked: bool) -> None:
            if p:
                p.om_show_watcher_debug = bool(checked)
                p.save()
            self._refresh_watcher_status()

        watcher_debug_toggle.toggled.connect(_toggle_watcher_debug)
        self._watcher_debug_checkbox = watcher_debug_toggle
        self._layout.addWidget(watcher_debug_toggle)

        watcher_debug = QLabel("")
        watcher_debug.setStyleSheet(
            "color: rgba(255,255,255,160); font-size: 9px; background: transparent;"
        )
        watcher_debug.setWordWrap(True)
        watcher_debug.setContentsMargins(8, 0, 4, 2)
        self._watcher_debug_label = watcher_debug
        self._layout.addWidget(watcher_debug)

        # ── Player retention row ─────────────────────────────────────────────
        keep_row = QWidget()
        keep_row.setStyleSheet("background: transparent;")
        keep_l = QHBoxLayout(keep_row)
        keep_l.setContentsMargins(2, 2, 2, 2)
        keep_l.setSpacing(6)
        keep_lbl = QLabel("Keep Players On Display (sec):")
        keep_lbl.setStyleSheet(_LABEL_STYLE)
        keep_l.addWidget(keep_lbl)
        keep_edit = QLineEdit()
        keep_edit.setStyleSheet(_EDIT_STYLE)
        keep_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        keep_edit.setFixedWidth(64)
        keep_edit.setText(str(getattr(p, "display_keep_seconds", 120) if p else 120))

        def _save_keep_seconds():
            if not p:
                return
            try:
                v = int(keep_edit.text())
            except ValueError:
                v = getattr(p, "display_keep_seconds", 120)
            v = max(30, min(600, v))
            keep_edit.setText(str(v))
            p.display_keep_seconds = v
            p.save()

        keep_edit.editingFinished.connect(_save_keep_seconds)
        keep_l.addWidget(keep_edit)
        keep_l.addStretch(1)
        self._layout.addWidget(keep_row)

        # ── Window BG row ────────────────────────────────────────────────────
        _bg_inner, _bg_grid = _make_section_inner()
        _add_grid_row(
            _bg_grid,
            0,
            False,
            "Window BG",
            p.om_win_bg_alpha if p else 0,
            init_color=p.om_win_bg_color if p else "#14141E",
            value_range=(0, 255),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "om_win_bg_alpha", v),
                        p.save(),
                        self.apply_win_bg_alpha(v),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "om_win_bg_color", c),
                        p.save(),
                        self.apply_win_bg_color(c),
                    )
                )
                if p
                else None
            ),
        )
        self._layout.addWidget(_bg_inner)

        # ── SUM section ──────────────────────────────────────────────────────
        sum_inner, sum_grid = _make_section_inner()
        _add_grid_row(
            sum_grid,
            0,
            False,
            "Name Size",
            p.sum_name_size if p else 9,
            init_color=p.sum_name_color if p else "#FFFFFF",
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "sum_name_size", v),
                        p.save(),
                        self._notify("SUM", "apply_name_size", v),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "sum_name_color", c),
                        p.save(),
                        self._notify("SUM", "apply_name_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            sum_grid,
            1,
            False,
            "Window Control",
            p.sum_win_width if p else 300,
            init_color=p.sum_name_col_color if p else "transparent",
            value_range=(100, 800),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "sum_win_width", v),
                        p.save(),
                        self._notify("SUM", "apply_win_width", v),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "sum_name_col_color", c),
                        p.save(),
                        self._notify("SUM", "apply_name_col_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            sum_grid,
            2,
            False,
            "Window BG",
            p.sum_win_bg_alpha if p else 0,
            init_color=p.sum_win_bg_color if p else "#000000",
            value_range=(0, 255),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "sum_win_bg_alpha", v),
                        p.save(),
                        self._notify("SUM", "apply_win_bg_alpha", v),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "sum_win_bg_color", c),
                        p.save(),
                        self._notify("SUM", "apply_win_bg_color", c),
                    )
                )
                if p
                else None
            ),
        )
        # DPS stat + Bar FG
        _add_grid_row(
            sum_grid,
            3,
            True,
            "DPS",
            p.sum_dps_size if p else 8,
            init_show=p.sum_dps_show if p else True,
            init_color=p.sum_dps_color if p else "#FF8C00",
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "sum_dps_size", v),
                        p.save(),
                        self._notify("SUM", "apply_dps_stat_size", v),
                    )
                )
                if p
                else None
            ),
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "sum_dps_show", e),
                        p.save(),
                        self._notify("SUM", "apply_dps_stat_show", e),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "sum_dps_color", c),
                        p.save(),
                        self._notify("SUM", "apply_dps_stat_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            sum_grid,
            4,
            True,
            "Bar FG",
            p.sum_dps_bar_fg_size if p else 71,
            init_show=p.sum_dps_bar_fg_show if p else True,
            init_color=p.sum_dps_bar_fg_color if p else "#7A2020",
            value_range=(0, 255),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "sum_dps_bar_fg_size", v),
                        p.save(),
                        self._notify("SUM", "apply_dps_bar_fg_size", v),
                    )
                )
                if p
                else None
            ),
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "sum_dps_bar_fg_show", e),
                        p.save(),
                        self._notify("SUM", "apply_dps_bar_fg_show", e),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "sum_dps_bar_fg_color", c),
                        p.save(),
                        self._notify("SUM", "apply_dps_bar_fg_color", c),
                    )
                )
                if p
                else None
            ),
        )
        # DEF stat + Bar FG
        _add_grid_row(
            sum_grid,
            5,
            True,
            "DEF",
            p.sum_def_size if p else 8,
            init_show=p.sum_def_show if p else True,
            init_color=p.sum_def_color if p else "#4169E1",
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "sum_def_size", v),
                        p.save(),
                        self._notify("SUM", "apply_def_stat_size", v),
                    )
                )
                if p
                else None
            ),
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "sum_def_show", e),
                        p.save(),
                        self._notify("SUM", "apply_def_stat_show", e),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "sum_def_color", c),
                        p.save(),
                        self._notify("SUM", "apply_def_stat_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            sum_grid,
            6,
            True,
            "Bar FG",
            p.sum_def_bar_fg_size if p else 71,
            init_show=p.sum_def_bar_fg_show if p else True,
            init_color=p.sum_def_bar_fg_color if p else "#1E3A7A",
            value_range=(0, 255),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "sum_def_bar_fg_size", v),
                        p.save(),
                        self._notify("SUM", "apply_def_bar_fg_size", v),
                    )
                )
                if p
                else None
            ),
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "sum_def_bar_fg_show", e),
                        p.save(),
                        self._notify("SUM", "apply_def_bar_fg_show", e),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "sum_def_bar_fg_color", c),
                        p.save(),
                        self._notify("SUM", "apply_def_bar_fg_color", c),
                    )
                )
                if p
                else None
            ),
        )
        # HEAL stat + Bar FG
        _add_grid_row(
            sum_grid,
            7,
            True,
            "HEAL",
            p.sum_heal_size if p else 8,
            init_show=p.sum_heal_show if p else True,
            init_color=p.sum_heal_color if p else "#32CD32",
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "sum_heal_size", v),
                        p.save(),
                        self._notify("SUM", "apply_heal_stat_size", v),
                    )
                )
                if p
                else None
            ),
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "sum_heal_show", e),
                        p.save(),
                        self._notify("SUM", "apply_heal_stat_show", e),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "sum_heal_color", c),
                        p.save(),
                        self._notify("SUM", "apply_heal_stat_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            sum_grid,
            8,
            True,
            "Bar FG",
            p.sum_heal_bar_fg_size if p else 71,
            init_show=p.sum_heal_bar_fg_show if p else True,
            init_color=p.sum_heal_bar_fg_color if p else "#1E6B1E",
            value_range=(0, 255),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "sum_heal_bar_fg_size", v),
                        p.save(),
                        self._notify("SUM", "apply_heal_bar_fg_size", v),
                    )
                )
                if p
                else None
            ),
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "sum_heal_bar_fg_show", e),
                        p.save(),
                        self._notify("SUM", "apply_heal_bar_fg_show", e),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "sum_heal_bar_fg_color", c),
                        p.save(),
                        self._notify("SUM", "apply_heal_bar_fg_color", c),
                    )
                )
                if p
                else None
            ),
        )
        # Shared bar background
        _add_grid_row(
            sum_grid,
            9,
            True,
            "Bar BG",
            p.sum_bar_bg_size if p else 12,
            init_show=p.sum_bar_bg_show if p else True,
            init_color=p.sum_bar_bg_color if p else "#FFFFFF",
            value_range=(0, 255),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "sum_bar_bg_size", v),
                        p.save(),
                        self._notify("SUM", "apply_bar_bg_size", v),
                    )
                )
                if p
                else None
            ),
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "sum_bar_bg_show", e),
                        p.save(),
                        self._notify("SUM", "apply_bar_bg_show", e),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "sum_bar_bg_color", c),
                        p.save(),
                        self._notify("SUM", "apply_bar_bg_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            sum_grid,
            10,
            True,
            "Average",
            init_show=p.sum_avg_show if p else True,
            has_size=False,
            has_color=False,
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "sum_avg_show", e),
                        p.save(),
                        self._notify("SUM", "apply_avg_show", e),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            sum_grid,
            11,
            True,
            "Total",
            init_show=p.sum_total_show if p else True,
            has_size=False,
            has_color=False,
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "sum_total_show", e),
                        p.save(),
                        self._notify("SUM", "apply_total_show", e),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            sum_grid,
            12,
            True,
            "Bar Border",
            p.sum_bar_border_size if p else 1,
            init_show=p.sum_bar_border_show if p else True,
            init_color=p.sum_bar_border_color if p else "#FFFFFF",
            value_range=(1, 10),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "sum_bar_border_size", v),
                        p.save(),
                        self._notify("SUM", "apply_border_size", v),
                    )
                )
                if p
                else None
            ),
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "sum_bar_border_show", e),
                        p.save(),
                        self._notify("SUM", "apply_border_show", e),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "sum_bar_border_color", c),
                        p.save(),
                        self._notify("SUM", "apply_border_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            sum_grid,
            13,
            True,
            "Score",
            p.sum_score_size if p else 9,
            init_show=p.sum_score_show if p else True,
            init_color=p.sum_score_color if p else "#FFD700",
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "sum_score_size", v),
                        p.save(),
                        self._notify("SUM", "apply_score_size", v),
                    )
                )
                if p
                else None
            ),
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "sum_score_show", e),
                        p.save(),
                        self._notify("SUM", "apply_score_show", e),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "sum_score_color", c),
                        p.save(),
                        self._notify("SUM", "apply_score_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            sum_grid,
            14,
            True,
            "Show Companions",
            init_show=p.sum_show_companions if p else False,
            has_size=False,
            has_color=False,
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "sum_show_companions", e),
                        p.save(),
                        self._notify("SUM", "apply_show_companions", e),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            sum_grid,
            15,
            True,
            "Outline",
            p.sum_outline_size if p else 1,
            init_show=p.sum_outline_show if p else True,
            init_color=p.sum_outline_color if p else "#000000",
            value_range=(0, 5),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "sum_outline_size", v),
                        p.save(),
                        self._notify("SUM", "apply_outline_size", v),
                    )
                )
                if p
                else None
            ),
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "sum_outline_show", e),
                        p.save(),
                        self._notify("SUM", "apply_outline_show", e),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "sum_outline_color", c),
                        p.save(),
                        self._notify("SUM", "apply_outline_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            sum_grid,
            16,
            False,
            "Row Height",
            p.sum_row_height if p else 24,
            init_show=True,
            has_size=True,
            has_color=False,
            value_range=(16, 48),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "sum_row_height", v),
                        p.save(),
                        self._notify("SUM", "apply_row_height", v),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            sum_grid,
            17,
            False,
            "Footer Value Size",
            p.sum_footer_value_size if p else 9,
            init_show=True,
            has_size=True,
            has_color=False,
            value_range=(6, 24),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "sum_footer_value_size", v),
                        p.save(),
                        self._notify("SUM", "apply_footer_value_size", v),
                    )
                )
                if p
                else None
            ),
        )
        def _make_on_change(key, win_name):
            def _fn(b):
                obs = self._vis_obs_dict.get(win_name)
                if obs is not None:
                    obs.set(b)
                else:
                    # Fallback if observable not bound yet
                    win = self._linked.get(key)
                    if win:
                        if b:
                            win.show()
                        else:
                            win.hide()
            return _fn

        _sum_wrapped, _sum_cb = _make_show_hide_wrapper(
            sum_inner,
            init_visible=self._vis_obs_dict.get("Summary", ObservableValue(p.get("Summary").visible if p else True)).value,
            on_change=_make_on_change("SUM", "Summary"),
        )
        self._vis_checks["SUM"] = _sum_cb
        _sum_sec = _section(
            "SUM", "#6B6B00", _sum_wrapped, on_collapse_change=self._resize_to_content,
        )

        # ── DPS section ──────────────────────────────────────────────────────
        dps_inner, dps_grid = _make_section_inner()
        _add_grid_row(
            dps_grid,
            0,
            False,
            "Name Size",
            p.dps_name_size if p else 12,
            init_color=p.dps_name_color if p else "#FFFFFF",
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "dps_name_size", v),
                        p.save(),
                        self._notify("DPS", "apply_name_size", v),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "dps_name_color", c),
                        p.save(),
                        self._notify("DPS", "apply_name_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            dps_grid,
            1,
            False,
            "Window Control",
            p.dps_win_width if p else 300,
            init_color=p.dps_name_col_color if p else "transparent",
            value_range=(100, 800),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "dps_win_width", v),
                        p.save(),
                        self._notify("DPS", "apply_win_width", v),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "dps_name_col_color", c),
                        p.save(),
                        self._notify("DPS", "apply_name_col_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            dps_grid,
            2,
            False,
            "Window BG",
            p.dps_win_bg_alpha if p else 0,
            init_color=p.dps_win_bg_color if p else "#000000",
            value_range=(0, 255),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "dps_win_bg_alpha", v),
                        p.save(),
                        self._notify("DPS", "apply_win_bg_alpha", v),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "dps_win_bg_color", c),
                        p.save(),
                        self._notify("DPS", "apply_win_bg_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            dps_grid,
            3,
            True,
            "DPS",
            p.dps_dps_size if p else 12,
            init_show=p.dps_dps_show if p else True,
            init_color=p.dps_dps_color if p else "#FF8C00",
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "dps_dps_size", v),
                        p.save(),
                        self._notify("DPS", "apply_stat_size", v),
                    )
                )
                if p
                else None
            ),
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "dps_dps_show", e),
                        p.save(),
                        self._notify("DPS", "apply_stat_show", e),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "dps_dps_color", c),
                        p.save(),
                        self._notify("DPS", "apply_stat_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            dps_grid,
            4,
            True,
            "Average",
            init_show=p.dps_avg_show if p else True,
            has_size=False,
            has_color=False,
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "dps_avg_show", e),
                        p.save(),
                        self._notify("DPS", "apply_avg_show", e),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            dps_grid,
            5,
            True,
            "Total",
            init_show=p.dps_total_show if p else True,
            has_size=False,
            has_color=False,
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "dps_total_show", e),
                        p.save(),
                        self._notify("DPS", "apply_total_show", e),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            dps_grid,
            6,
            True,
            "Bar Border",
            p.dps_bar_border_size if p else 1,
            init_show=p.dps_bar_border_show if p else True,
            init_color=p.dps_bar_border_color if p else "#FFFFFF",
            value_range=(1, 10),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "dps_bar_border_size", v),
                        p.save(),
                        self._notify("DPS", "apply_border_size", v),
                    )
                )
                if p
                else None
            ),
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "dps_bar_border_show", e),
                        p.save(),
                        self._notify("DPS", "apply_border_show", e),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "dps_bar_border_color", c),
                        p.save(),
                        self._notify("DPS", "apply_border_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            dps_grid,
            7,
            True,
            "Bar BG",
            p.dps_bar_bg_size if p else 12,
            init_show=p.dps_bar_bg_show if p else True,
            init_color=p.dps_bar_bg_color if p else "#FFFFFF",
            value_range=(0, 255),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "dps_bar_bg_size", v),
                        p.save(),
                        self._notify("DPS", "apply_bar_bg_size", v),
                    )
                )
                if p
                else None
            ),
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "dps_bar_bg_show", e),
                        p.save(),
                        self._notify("DPS", "apply_bar_bg_show", e),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "dps_bar_bg_color", c),
                        p.save(),
                        self._notify("DPS", "apply_bar_bg_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            dps_grid,
            8,
            True,
            "Bar FG",
            p.dps_bar_fg_size if p else 71,
            init_show=p.dps_bar_fg_show if p else True,
            init_color=p.dps_bar_fg_color if p else "#7A2020",
            value_range=(0, 255),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "dps_bar_fg_size", v),
                        p.save(),
                        self._notify("DPS", "apply_bar_fg_size", v),
                    )
                )
                if p
                else None
            ),
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "dps_bar_fg_show", e),
                        p.save(),
                        self._notify("DPS", "apply_bar_fg_show", e),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "dps_bar_fg_color", c),
                        p.save(),
                        self._notify("DPS", "apply_bar_fg_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            dps_grid,
            9,
            True,
            "Score",
            p.dps_score_size if p else 12,
            init_show=p.dps_score_show if p else True,
            init_color=p.dps_score_color if p else "#FFD700",
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "dps_score_size", v),
                        p.save(),
                        self._notify("DPS", "apply_score_size", v),
                    )
                )
                if p
                else None
            ),
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "dps_score_show", e),
                        p.save(),
                        self._notify("DPS", "apply_score_show", e),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "dps_score_color", c),
                        p.save(),
                        self._notify("DPS", "apply_score_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            dps_grid,
            10,
            True,
            "Show Companions",
            init_show=p.dps_show_companions if p else False,
            has_size=False,
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "dps_show_companions", e),
                        p.save(),
                        self._notify("DPS", "apply_show_companions", e),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            dps_grid,
            11,
            True,
            "Outline",
            p.dps_outline_size if p else 1,
            init_show=p.dps_outline_show if p else True,
            init_color=p.dps_outline_color if p else "#000000",
            value_range=(0, 5),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "dps_outline_size", v),
                        p.save(),
                        self._notify("DPS", "apply_outline_size", v),
                    )
                )
                if p
                else None
            ),
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "dps_outline_show", e),
                        p.save(),
                        self._notify("DPS", "apply_outline_show", e),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "dps_outline_color", c),
                        p.save(),
                        self._notify("DPS", "apply_outline_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            dps_grid,
            12,
            False,
            "Row Height",
            p.dps_row_height if p else 24,
            init_show=True,
            has_size=True,
            has_color=False,
            value_range=(16, 48),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "dps_row_height", v),
                        p.save(),
                        self._notify("DPS", "apply_row_height", v),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            dps_grid,
            13,
            False,
            "Footer Value Size",
            p.dps_footer_value_size if p else 9,
            init_show=True,
            has_size=True,
            has_color=False,
            value_range=(6, 24),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "dps_footer_value_size", v),
                        p.save(),
                        self._notify("DPS", "apply_footer_value_size", v),
                    )
                )
                if p
                else None
            ),
        )
        _dps_wrapped, _dps_cb = _make_show_hide_wrapper(
            dps_inner,
            init_visible=self._vis_obs_dict.get("DPS", ObservableValue(p.get("DPS").visible if p else True)).value,
            on_change=_make_on_change("DPS", "DPS"),
        )
        self._vis_checks["DPS"] = _dps_cb
        _dps_sec = _section(
            "DPS", "#7A2020", _dps_wrapped, on_collapse_change=self._resize_to_content,
        )

        # ── DEF section ──────────────────────────────────────────────────────
        def_inner, def_grid = _make_section_inner()
        _add_grid_row(
            def_grid,
            0,
            False,
            "Name Size",
            p.def_name_size if p else 12,
            init_color=p.def_name_color if p else "#FFFFFF",
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "def_name_size", v),
                        p.save(),
                        self._notify("DEF", "apply_name_size", v),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "def_name_color", c),
                        p.save(),
                        self._notify("DEF", "apply_name_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            def_grid,
            1,
            False,
            "Window Control",
            p.def_win_width if p else 300,
            init_color=p.def_name_col_color if p else "transparent",
            value_range=(100, 800),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "def_win_width", v),
                        p.save(),
                        self._notify("DEF", "apply_win_width", v),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "def_name_col_color", c),
                        p.save(),
                        self._notify("DEF", "apply_name_col_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            def_grid,
            2,
            False,
            "Window BG",
            p.def_win_bg_alpha if p else 0,
            init_color=p.def_win_bg_color if p else "#000000",
            value_range=(0, 255),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "def_win_bg_alpha", v),
                        p.save(),
                        self._notify("DEF", "apply_win_bg_alpha", v),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "def_win_bg_color", c),
                        p.save(),
                        self._notify("DEF", "apply_win_bg_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            def_grid,
            3,
            True,
            "DEF",
            p.def_def_size if p else 12,
            init_show=p.def_def_show if p else True,
            init_color=p.def_def_color if p else "#4169E1",
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "def_def_size", v),
                        p.save(),
                        self._notify("DEF", "apply_stat_size", v),
                    )
                )
                if p
                else None
            ),
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "def_def_show", e),
                        p.save(),
                        self._notify("DEF", "apply_stat_show", e),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "def_def_color", c),
                        p.save(),
                        self._notify("DEF", "apply_stat_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            def_grid,
            4,
            True,
            "Average",
            init_show=p.def_avg_show if p else True,
            has_size=False,
            has_color=False,
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "def_avg_show", e),
                        p.save(),
                        self._notify("DEF", "apply_avg_show", e),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            def_grid,
            5,
            True,
            "Total",
            init_show=p.def_total_show if p else True,
            has_size=False,
            has_color=False,
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "def_total_show", e),
                        p.save(),
                        self._notify("DEF", "apply_total_show", e),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            def_grid,
            6,
            True,
            "Bar Border",
            p.def_bar_border_size if p else 1,
            init_show=p.def_bar_border_show if p else True,
            init_color=p.def_bar_border_color if p else "#FFFFFF",
            value_range=(1, 10),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "def_bar_border_size", v),
                        p.save(),
                        self._notify("DEF", "apply_border_size", v),
                    )
                )
                if p
                else None
            ),
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "def_bar_border_show", e),
                        p.save(),
                        self._notify("DEF", "apply_border_show", e),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "def_bar_border_color", c),
                        p.save(),
                        self._notify("DEF", "apply_border_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            def_grid,
            7,
            True,
            "Bar BG",
            p.def_bar_bg_size if p else 12,
            init_show=p.def_bar_bg_show if p else True,
            init_color=p.def_bar_bg_color if p else "#FFFFFF",
            value_range=(0, 255),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "def_bar_bg_size", v),
                        p.save(),
                        self._notify("DEF", "apply_bar_bg_size", v),
                    )
                )
                if p
                else None
            ),
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "def_bar_bg_show", e),
                        p.save(),
                        self._notify("DEF", "apply_bar_bg_show", e),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "def_bar_bg_color", c),
                        p.save(),
                        self._notify("DEF", "apply_bar_bg_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            def_grid,
            8,
            True,
            "Bar FG",
            p.def_bar_fg_size if p else 71,
            init_show=p.def_bar_fg_show if p else True,
            init_color=p.def_bar_fg_color if p else "#1E3A7A",
            value_range=(0, 255),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "def_bar_fg_size", v),
                        p.save(),
                        self._notify("DEF", "apply_bar_fg_size", v),
                    )
                )
                if p
                else None
            ),
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "def_bar_fg_show", e),
                        p.save(),
                        self._notify("DEF", "apply_bar_fg_show", e),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "def_bar_fg_color", c),
                        p.save(),
                        self._notify("DEF", "apply_bar_fg_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            def_grid,
            9,
            True,
            "Score",
            p.def_score_size if p else 12,
            init_show=p.def_score_show if p else True,
            init_color=p.def_score_color if p else "#FFD700",
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "def_score_size", v),
                        p.save(),
                        self._notify("DEF", "apply_score_size", v),
                    )
                )
                if p
                else None
            ),
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "def_score_show", e),
                        p.save(),
                        self._notify("DEF", "apply_score_show", e),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "def_score_color", c),
                        p.save(),
                        self._notify("DEF", "apply_score_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            def_grid,
            10,
            True,
            "Show Companions",
            init_show=p.def_show_companions if p else False,
            has_size=False,
            has_color=False,
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "def_show_companions", e),
                        p.save(),
                        self._notify("DEF", "apply_show_companions", e),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            def_grid,
            11,
            True,
            "Outline",
            p.def_outline_size if p else 1,
            init_show=p.def_outline_show if p else True,
            init_color=p.def_outline_color if p else "#000000",
            value_range=(0, 5),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "def_outline_size", v),
                        p.save(),
                        self._notify("DEF", "apply_outline_size", v),
                    )
                )
                if p
                else None
            ),
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "def_outline_show", e),
                        p.save(),
                        self._notify("DEF", "apply_outline_show", e),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "def_outline_color", c),
                        p.save(),
                        self._notify("DEF", "apply_outline_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            def_grid,
            12,
            False,
            "Row Height",
            p.def_row_height if p else 24,
            init_show=True,
            has_size=True,
            has_color=False,
            value_range=(16, 48),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "def_row_height", v),
                        p.save(),
                        self._notify("DEF", "apply_row_height", v),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            def_grid,
            13,
            False,
            "Footer Value Size",
            p.def_footer_value_size if p else 9,
            init_show=True,
            has_size=True,
            has_color=False,
            value_range=(6, 24),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "def_footer_value_size", v),
                        p.save(),
                        self._notify("DEF", "apply_footer_value_size", v),
                    )
                )
                if p
                else None
            ),
        )
        _def_wrapped, _def_cb = _make_show_hide_wrapper(
            def_inner,
            init_visible=self._vis_obs_dict.get("Defense", ObservableValue(p.get("Defense").visible if p else True)).value,
            on_change=_make_on_change("DEF", "Defense"),
        )
        self._vis_checks["DEF"] = _def_cb
        _def_sec = _section(
            "DEF", "#1E3A7A", _def_wrapped, on_collapse_change=self._resize_to_content,
        )

        # ── HEAL section ─────────────────────────────────────────────────────
        heal_inner, heal_grid = _make_section_inner()
        _add_grid_row(
            heal_grid,
            0,
            False,
            "Name Size",
            p.heal_name_size if p else 12,
            init_color=p.heal_name_color if p else "#FFFFFF",
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "heal_name_size", v),
                        p.save(),
                        self._notify("HEAL", "apply_name_size", v),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "heal_name_color", c),
                        p.save(),
                        self._notify("HEAL", "apply_name_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            heal_grid,
            1,
            False,
            "Window Control",
            p.heal_win_width if p else 300,
            init_color=p.heal_name_col_color if p else "transparent",
            value_range=(100, 800),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "heal_win_width", v),
                        p.save(),
                        self._notify("HEAL", "apply_win_width", v),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "heal_name_col_color", c),
                        p.save(),
                        self._notify("HEAL", "apply_name_col_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            heal_grid,
            2,
            False,
            "Window BG",
            p.heal_win_bg_alpha if p else 0,
            init_color=p.heal_win_bg_color if p else "#000000",
            value_range=(0, 255),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "heal_win_bg_alpha", v),
                        p.save(),
                        self._notify("HEAL", "apply_win_bg_alpha", v),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "heal_win_bg_color", c),
                        p.save(),
                        self._notify("HEAL", "apply_win_bg_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            heal_grid,
            3,
            True,
            "HEAL",
            p.heal_heal_size if p else 12,
            init_show=p.heal_heal_show if p else True,
            value_range=(0, 255),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "heal_heal_size", v),
                        p.save(),
                        self._notify("HEAL", "apply_stat_size", v),
                    )
                )
                if p
                else None
            ),
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "heal_heal_show", e),
                        p.save(),
                        self._notify("HEAL", "apply_stat_show", e),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "heal_heal_color", c),
                        p.save(),
                        self._notify("HEAL", "apply_stat_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            heal_grid,
            4,
            True,
            "Average",
            init_show=p.heal_avg_show if p else True,
            has_size=False,
            value_range=(0, 255),
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "heal_avg_show", e),
                        p.save(),
                        self._notify("HEAL", "apply_avg_show", e),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            heal_grid,
            5,
            True,
            "Total",
            init_show=p.heal_total_show if p else True,
            has_size=False,
            has_color=False,
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "heal_total_show", e),
                        p.save(),
                        self._notify("HEAL", "apply_total_show", e),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            heal_grid,
            6,
            True,
            "Bar Border",
            p.heal_bar_border_size if p else 1,
            init_show=p.heal_bar_border_show if p else True,
            init_color=p.heal_bar_border_color if p else "#FFFFFF",
            value_range=(1, 10),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "heal_bar_border_size", v),
                        p.save(),
                        self._notify("HEAL", "apply_border_size", v),
                    )
                )
                if p
                else None
            ),
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "heal_bar_border_show", e),
                        p.save(),
                        self._notify("HEAL", "apply_border_show", e),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "heal_bar_border_color", c),
                        p.save(),
                        self._notify("HEAL", "apply_border_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            heal_grid,
            7,
            True,
            "Bar BG",
            p.heal_bar_bg_size if p else 12,
            init_show=p.heal_bar_bg_show if p else True,
            init_color=p.heal_bar_bg_color if p else "#FFFFFF",
            value_range=(0, 255),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "heal_bar_bg_size", v),
                        p.save(),
                        self._notify("HEAL", "apply_bar_bg_size", v),
                    )
                )
                if p
                else None
            ),
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "heal_bar_bg_show", e),
                        p.save(),
                        self._notify("HEAL", "apply_bar_bg_show", e),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "heal_bar_bg_color", c),
                        p.save(),
                        self._notify("HEAL", "apply_bar_bg_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            heal_grid,
            8,
            True,
            "Bar FG",
            p.heal_bar_fg_size if p else 71,
            init_show=p.heal_bar_fg_show if p else True,
            init_color=p.heal_bar_fg_color if p else "#1E6B1E",
            value_range=(0, 255),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "heal_bar_fg_size", v),
                        p.save(),
                        self._notify("HEAL", "apply_bar_fg_size", v),
                    )
                )
                if p
                else None
            ),
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "heal_bar_fg_show", e),
                        p.save(),
                        self._notify("HEAL", "apply_bar_fg_show", e),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "heal_bar_fg_color", c),
                        p.save(),
                        self._notify("HEAL", "apply_bar_fg_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            heal_grid,
            9,
            True,
            "Score",
            p.heal_score_size if p else 12,
            init_show=p.heal_score_show if p else True,
            init_color=p.heal_score_color if p else "#FFD700",
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "heal_score_size", v),
                        p.save(),
                        self._notify("HEAL", "apply_score_size", v),
                    )
                )
                if p
                else None
            ),
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "heal_score_show", e),
                        p.save(),
                        self._notify("HEAL", "apply_score_show", e),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "heal_score_color", c),
                        p.save(),
                        self._notify("HEAL", "apply_score_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            heal_grid,
            10,
            True,
            "Show Companions",
            init_show=p.heal_show_companions if p else False,
            has_size=False,
            has_color=False,
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "heal_show_companions", e),
                        p.save(),
                        self._notify("HEAL", "apply_show_companions", e),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            heal_grid,
            11,
            True,
            "Outline",
            p.heal_outline_size if p else 1,
            init_show=p.heal_outline_show if p else True,
            init_color=p.heal_outline_color if p else "#000000",
            value_range=(0, 5),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "heal_outline_size", v),
                        p.save(),
                        self._notify("HEAL", "apply_outline_size", v),
                    )
                )
                if p
                else None
            ),
            on_show_change=(
                (
                    lambda e: (
                        setattr(p, "heal_outline_show", e),
                        p.save(),
                        self._notify("HEAL", "apply_outline_show", e),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "heal_outline_color", c),
                        p.save(),
                        self._notify("HEAL", "apply_outline_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            heal_grid,
            12,
            False,
            "Row Height",
            p.heal_row_height if p else 24,
            init_show=True,
            has_size=True,
            has_color=False,
            value_range=(16, 48),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "heal_row_height", v),
                        p.save(),
                        self._notify("HEAL", "apply_row_height", v),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            heal_grid,
            13,
            False,
            "Footer Value Size",
            p.heal_footer_value_size if p else 9,
            init_show=True,
            has_size=True,
            has_color=False,
            value_range=(6, 24),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "heal_footer_value_size", v),
                        p.save(),
                        self._notify("HEAL", "apply_footer_value_size", v),
                    )
                )
                if p
                else None
            ),
        )
        _heal_wrapped, _heal_cb = _make_show_hide_wrapper(
            heal_inner,
            init_visible=self._vis_obs_dict.get("Heal", ObservableValue(p.get("Heal").visible if p else True)).value,
            on_change=_make_on_change("HEAL", "Heal"),
        )
        self._vis_checks["HEAL"] = _heal_cb
        _heal_sec = _section(
            "HEAL", "#1E6B1E", _heal_wrapped, on_collapse_change=self._resize_to_content,
        )

        # ── Combat History section ─────────────────────────────────────────────
        coh_inner, coh_grid = _make_section_inner()
        _add_grid_row(
            coh_grid,
            0,
            False,
            "Window Width",
            p.coh_win_width if p else 380,
            init_show=True,
            init_color=None,
            has_size=True,
            has_color=False,
            value_range=(200, 800),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "coh_win_width", v),
                        p.save(),
                        self._notify("COH", "apply_win_width", v),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            coh_grid,
            1,
            False,
            "Window Height",
            p.coh_win_height if p else 600,
            init_show=True,
            init_color=None,
            has_size=True,
            has_color=False,
            value_range=(100, 1200),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "coh_win_height", v),
                        p.save(),
                        self._notify("COH", "apply_win_height", v),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            coh_grid,
            2,
            False,
            "Window BG",
            p.coh_win_bg_alpha if p else 0,
            init_color=p.coh_win_bg_color if p else "#000000",
            value_range=(0, 255),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "coh_win_bg_alpha", v),
                        p.save(),
                        self._notify("COH", "apply_win_bg_alpha", v),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "coh_win_bg_color", c),
                        p.save(),
                        self._notify("COH", "apply_win_bg_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            coh_grid,
            3,
            False,
            "Name Size",
            p.coh_name_size if p else 10,
            init_show=True,
            init_color=p.coh_name_color if p else "#FFFFFF",
            has_size=True,
            has_color=True,
            value_range=(4, 24),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "coh_name_size", v),
                        p.save(),
                        self._notify("COH", "apply_name_size", v),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "coh_name_color", c),
                        p.save(),
                        self._notify("COH", "apply_name_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            coh_grid,
            4,
            False,
            "Stat Size",
            p.coh_stat_size if p else 10,
            init_show=True,
            init_color=None,
            has_size=True,
            has_color=False,
            value_range=(4, 24),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "coh_stat_size", v),
                        p.save(),
                        self._notify("COH", "apply_stat_size", v),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            coh_grid,
            5,
            False,
            "List Height",
            p.coh_list_height if p else 420,
            init_show=True,
            init_color=None,
            has_size=True,
            has_color=False,
            value_range=(100, 800),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "coh_list_height", v),
                        p.save(),
                        self._notify("COH", "apply_list_height", v),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            coh_grid,
            6,
            False,
            "Text Size",
            p.coh_label_size if p else 10,
            init_show=True,
            init_color=None,
            has_size=True,
            has_color=False,
            value_range=(6, 24),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "coh_label_size", v),
                        p.save(),
                        self._notify("COH", "apply_text_size", v),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            coh_grid,
            7,
            False,
            "Footer Value Size",
            p.coh_footer_value_size if p else 9,
            init_show=True,
            init_color=None,
            has_size=True,
            has_color=False,
            value_range=(6, 24),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "coh_footer_value_size", v),
                        p.save(),
                        self._notify("COH", "apply_footer_value_size", v),
                    )
                )
                if p
                else None
            ),
        )
        _coh_wrapped, _coh_cb = _make_show_hide_wrapper(
            coh_inner,
            init_visible=self._vis_obs_dict.get("Combat History", ObservableValue(p.get("Combat History").visible if p else True)).value,
            on_change=_make_on_change("COH", "Combat History"),
        )
        self._vis_checks["COH"] = _coh_cb
        _coh_sec = _section(
            "COH", "#1A3A4A", _coh_wrapped, on_collapse_change=self._resize_to_content,
        )

        # ── Charts section ─────────────────────────────────────────────────────
        cht_inner, cht_grid = _make_section_inner()
        _add_grid_row(
            cht_grid,
            0,
            False,
            "Window Width",
            p.cht_win_width if p else 300,
            init_show=True,
            init_color=None,
            has_size=True,
            has_color=False,
            value_range=(200, 800),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "cht_win_width", v),
                        p.save(),
                        self._notify("CHT", "apply_win_width", v),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            cht_grid,
            1,
            False,
            "Window Height",
            p.cht_win_height if p else 500,
            init_show=True,
            init_color=None,
            has_size=True,
            has_color=False,
            value_range=(100, 1200),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "cht_win_height", v),
                        p.save(),
                        self._notify("CHT", "apply_win_height", v),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            cht_grid,
            2,
            False,
            "Window BG",
            p.cht_win_bg_alpha if p else 0,
            init_color=p.cht_win_bg_color if p else "#000000",
            value_range=(0, 255),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "cht_win_bg_alpha", v),
                        p.save(),
                        self._notify("CHT", "apply_win_bg_alpha", v),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "cht_win_bg_color", c),
                        p.save(),
                        self._notify("CHT", "apply_win_bg_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            cht_grid,
            3,
            False,
            "Name Size",
            p.cht_name_size if p else 10,
            init_show=True,
            init_color=p.cht_name_color if p else "#FFFFFF",
            has_size=True,
            has_color=True,
            value_range=(4, 24),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "cht_name_size", v),
                        p.save(),
                        self._notify("CHT", "apply_name_size", v),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "cht_name_color", c),
                        p.save(),
                        self._notify("CHT", "apply_name_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            cht_grid,
            4,
            False,
            "Me Bar",
            0,
            init_show=True,
            init_color=p.cht_me_color if p else "#1E90FF",
            has_size=False,
            has_color=True,
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "cht_me_color", c),
                        p.save(),
                        self._notify("CHT", "apply_me_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            cht_grid,
            5,
            False,
            "Other Bar",
            0,
            init_show=True,
            init_color=p.cht_other_color if p else "#787878",
            has_size=False,
            has_color=True,
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "cht_other_color", c),
                        p.save(),
                        self._notify("CHT", "apply_other_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            cht_grid,
            6,
            False,
            "Value Size",
            p.cht_val_size if p else 10,
            init_show=True,
            init_color=None,
            has_size=True,
            has_color=False,
            value_range=(4, 24),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "cht_val_size", v),
                        p.save(),
                        self._notify("CHT", "apply_val_size", v),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            cht_grid,
            7,
            False,
            "Text Size",
            p.cht_label_size if p else 10,
            init_show=True,
            init_color=None,
            has_size=True,
            has_color=False,
            value_range=(6, 24),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "cht_label_size", v),
                        p.save(),
                        self._notify("CHT", "apply_text_size", v),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            cht_grid,
            8,
            False,
            "Footer Value Size",
            p.cht_footer_value_size if p else 9,
            init_show=True,
            init_color=None,
            has_size=True,
            has_color=False,
            value_range=(6, 24),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "cht_footer_value_size", v),
                        p.save(),
                        self._notify("CHT", "apply_footer_value_size", v),
                    )
                )
                if p
                else None
            ),
        )
        _cht_wrapped, _cht_cb = _make_show_hide_wrapper(
            cht_inner,
            init_visible=self._vis_obs_dict.get("Charts", ObservableValue(p.get("Charts").visible if p else True)).value,
            on_change=_make_on_change("CHT", "Charts"),
        )
        self._vis_checks["CHT"] = _cht_cb
        _cht_sec = _section(
            "CHT", "#2A1A3A", _cht_wrapped, on_collapse_change=self._resize_to_content,
        )

        # ── Nihilus' Book of Grudges section ─────────────────────────────────
        nbg_inner, nbg_grid = _make_section_inner()
        _add_grid_row(
            nbg_grid,
            0,
            False,
            "Window Width",
            p.nbg_win_width if p else 360,
            init_show=True,
            init_color=None,
            has_size=True,
            has_color=False,
            value_range=(220, 1000),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "nbg_win_width", v),
                        p.save(),
                        self._notify("NBG", "apply_win_width", v),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            nbg_grid,
            1,
            False,
            "Window Height",
            p.nbg_win_height if p else 300,
            init_show=True,
            init_color=None,
            has_size=True,
            has_color=False,
            value_range=(120, 1200),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "nbg_win_height", v),
                        p.save(),
                        self._notify("NBG", "apply_win_height", v),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            nbg_grid,
            2,
            False,
            "Window BG",
            p.nbg_win_bg_alpha if p else 0,
            init_color=p.nbg_win_bg_color if p else "#000000",
            value_range=(0, 255),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "nbg_win_bg_alpha", v),
                        p.save(),
                        self._notify("NBG", "apply_win_bg_alpha", v),
                    )
                )
                if p
                else None
            ),
            on_color_change=(
                (
                    lambda c: (
                        setattr(p, "nbg_win_bg_color", c),
                        p.save(),
                        self._notify("NBG", "apply_win_bg_color", c),
                    )
                )
                if p
                else None
            ),
        )
        _add_grid_row(
            nbg_grid,
            3,
            False,
            "Text Size",
            p.nbg_label_size if p else 10,
            init_show=True,
            init_color=None,
            has_size=True,
            has_color=False,
            value_range=(6, 24),
            on_value_change=(
                (
                    lambda v: (
                        setattr(p, "nbg_label_size", v),
                        p.save(),
                        self._notify("NBG", "apply_text_size", v),
                    )
                )
                if p
                else None
            ),
        )
        _nbg_wrapped, _nbg_cb = _make_show_hide_wrapper(
            nbg_inner,
            init_visible=self._vis_obs_dict.get("Nihilus' Book of Grudges", ObservableValue(p.get("Nihilus' Book of Grudges").visible if p else True)).value,
            on_change=_make_on_change("NBG", "Nihilus' Book of Grudges"),
        )
        self._vis_checks["NBG"] = _nbg_cb
        _nbg_sec = _section(
            "NBG", "#5A2E18", _nbg_wrapped, on_collapse_change=self._resize_to_content,
        )

        # ── Store width/height slider refs for drag-resize → OM sync ───────────
        for _k, _g, _wr, _hr in (
            ("SUM", sum_grid, 1, None),
            ("DPS", dps_grid, 1, None),
            ("DEF", def_grid, 1, None),
            ("HEAL", heal_grid, 1, None),
            ("COH", coh_grid, 0, 1),
            ("CHT", cht_grid, 0, 1),
            ("NBG", nbg_grid, 0, 1),
        ):
            _sl: dict = {}
            _wi = _g.itemAtPosition(_wr, 2)
            if _wi is not None:
                _sl["width"] = _wi.widget()
            if _hr is not None:
                _hi = _g.itemAtPosition(_hr, 2)
                if _hi is not None:
                    _sl["height"] = _hi.widget()
            if _sl:
                self._win_size_sliders[_k] = _sl

        # ── Scrollable sections wrapper (max 600 px tall) ─────────────────────
        sections_container = QWidget()
        sections_container.setStyleSheet("background: transparent;")
        sec_layout = QVBoxLayout(sections_container)
        sec_layout.setContentsMargins(0, 0, 0, 0)
        sec_layout.setSpacing(4)
        sec_layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinimumSize)
        for sec in (_sum_sec, _dps_sec, _def_sec, _heal_sec, _coh_sec, _cht_sec, _nbg_sec):
            sec_layout.addWidget(sec)

        self._sections_container = sections_container
        self._scroll_area = _AutoScrollArea()
        self._scroll_area.setWidget(sections_container)
        self._layout.addWidget(self._scroll_area)

    def _on_win_resized_by_user(self, win_key: str, total_w: int, total_h: int) -> None:
        """Update OM sliders when an overlay is resized via its drag handle."""
        from app.window import BORDER_WIDTH, CONTENT_PADDING, MENU_BAR_HEIGHT as _MBH
        co = BORDER_WIDTH + CONTENT_PADDING
        content_w = max(1, total_w - co * 2)
        content_h = max(1, total_h - _MBH - co)
        sliders = self._win_size_sliders.get(win_key, {})
        w_slider = sliders.get("width")
        h_slider = sliders.get("height")
        if w_slider is not None:
            w_slider.setValue(content_w)  # fires on_value_change → saves pref + notifies overlay
        if h_slider is not None:
            h_slider.setValue(content_h)

    def _notify(self, win_key: str, method: str, value) -> None:
        """Forward a live setting change to a linked stat overlay."""
        win = self._linked.get(win_key)
        if win is not None:
            fn = getattr(win, method, None)
            if fn:
                fn(value)

    def _notify_all(self, method: str, value) -> None:
        """Forward a live setting change to all linked overlays."""
        for win in self._linked.values():
            fn = getattr(win, method, None)
            if fn:
                try:
                    fn(value)
                except Exception:
                    # Keep broadcasting even if one overlay fails to refresh.
                    continue

    def receive_watcher(self, watcher) -> None:
        """Store the LogWatcher so the browse button can redirect it."""
        self._watcher = watcher

        # Refresh status when watcher state changes.
        watcher.session_reset.connect(self._refresh_watcher_status)
        watcher.fight_opened.connect(lambda _fight: self._refresh_watcher_status())
        watcher.fight_closed.connect(lambda _fight: self._refresh_watcher_status())
        watcher.fight_updated.connect(lambda _fight: self._refresh_watcher_status())

        # Also poll periodically because active file can change between signals.
        if self._watcher_status_timer is None:
            self._watcher_status_timer = QTimer(self)
            self._watcher_status_timer.setInterval(1000)
            self._watcher_status_timer.timeout.connect(self._refresh_watcher_status)
            self._watcher_status_timer.start()

        self._refresh_watcher_status()

    def _refresh_watcher_status(self) -> None:
        lbl = self._watcher_status_label
        dbg_lbl = self._watcher_debug_label
        dbg_cb = self._watcher_debug_checkbox
        if lbl is None:
            return

        def _set_status_style(color: str) -> None:
            lbl.setStyleSheet(
                f"color: {color}; font-size: 10px; background: transparent;"
            )

        watcher = getattr(self, "_watcher", None)
        if watcher is None:
            _set_status_style("rgba(255,255,255,180)")
            lbl.setText("Log Watcher: waiting for watcher...")
            if dbg_lbl is not None:
                dbg_lbl.setVisible(False)
            return

        log_dir = getattr(watcher, "log_dir", None)
        active_file = getattr(watcher, "current_file", None)

        dir_text = str(log_dir) if log_dir is not None else "(auto-detect pending)"
        file_text = str(active_file.name) if active_file is not None else "(none)"
        if log_dir is None:
            _set_status_style("#ff8080")
        elif active_file is None:
            _set_status_style("#ffd166")
        else:
            _set_status_style("#7bd88f")
        lbl.setText(f"Log Watcher: dir={dir_text} | file={file_text}")

        if dbg_lbl is None:
            return
        show_debug = bool(dbg_cb.isChecked()) if dbg_cb is not None else False
        dbg_lbl.setVisible(show_debug)
        if not show_debug:
            return

        now = time.monotonic()
        current = getattr(watcher, "current_fight", None)
        open_players = len(getattr(watcher, "_open_players", {}) or {})
        grace_end_ms = int(getattr(watcher, "_grace_end_ms", 0) or 0)
        last_event_wall = float(getattr(watcher, "_current_fight_last_event_wall", 0.0) or 0.0)
        last_damage_wall = float(getattr(watcher, "_current_fight_last_damage_wall", 0.0) or 0.0)
        last_ts_ms = getattr(watcher, "_last_event_ts_ms", None)

        idle_event_ms = int((now - last_event_wall) * 1000) if last_event_wall > 0 else -1
        idle_damage_ms = int((now - last_damage_wall) * 1000) if last_damage_wall > 0 else -1

        if current is not None and last_ts_ms is not None and grace_end_ms > 0 and not open_players:
            grace_left = max(0, grace_end_ms - int(last_ts_ms))
        else:
            grace_left = 0

        dbg_lbl.setText(
            "Watcher Debug: "
            f"fight_open={'yes' if current is not None else 'no'} | "
            f"open_players={open_players} | "
            f"idle_event_ms={idle_event_ms} | "
            f"idle_damage_ms={idle_damage_ms} | "
            f"grace_left_ms={grace_left}"
        )

    def link_overlays(
        self,
        sum_win: "SummaryWindow",
        dps_win: "_PlayerListOverlay",
        def_win: "_PlayerListOverlay",
        heal_win: "_PlayerListOverlay",
        coh_win=None,
        cht_win=None,
        nbg_win=None,
        vis_obs: "dict[str, ObservableValue] | None" = None,
    ) -> None:
        """Wire Overlay Master controls to the live stat overlay windows."""
        self._linked["SUM"] = sum_win
        self._linked["DPS"] = dps_win
        self._linked["DEF"] = def_win
        self._linked["HEAL"] = heal_win
        if coh_win is not None:
            self._linked["COH"] = coh_win
        if cht_win is not None:
            self._linked["CHT"] = cht_win
        if nbg_win is not None:
            self._linked["NBG"] = nbg_win

        # If vis_obs provided at link time (wasn't available at construction), store it
        if vis_obs is not None:
            self._vis_obs_dict = vis_obs

        # Subscribe Show/Hide checkboxes to their observables so any external
        # change (menu toggle, X button) keeps the checkbox in sync.
        _key_to_win_name = {
            "SUM": "Summary", "DPS": "DPS", "DEF": "Defense",
            "HEAL": "Heal", "COH": "Combat History", "CHT": "Charts",
            "NBG": "Nihilus' Book of Grudges",
        }

        def _make_sync_cb(checkbox):
            def _sync(visible: bool):
                checkbox.blockSignals(True)
                checkbox.setChecked(visible)
                checkbox.blockSignals(False)
            return _sync

        for key, cb in self._vis_checks.items():
            win_name = _key_to_win_name.get(key)
            if win_name and win_name in self._vis_obs_dict:
                self._vis_obs_dict[win_name].subscribe(_make_sync_cb(cb))

        p = self._prefs
        self._notify_all(
            "apply_character_name",
            (p.character_name.strip() if p and p.character_name else ""),
        )

        # Wire drag-resize → OM slider callbacks for all linked overlays.
        def _make_resize_cb(win_key: str):
            def _cb(total_w: int, total_h: int) -> None:
                self._on_win_resized_by_user(win_key, total_w, total_h)
            return _cb

        for _key, _win in self._linked.items():
            if hasattr(_win, "_manual_resize_callback"):
                _win._manual_resize_callback = _make_resize_cb(_key)


# ── stat progress bar ────────────────────────────────────────────────────────

