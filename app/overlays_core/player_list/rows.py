"""Row widgets for player-list overlays."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QHBoxLayout, QSizePolicy, QWidget

from app.constants import fmt_num

from ..helpers import _OutlineLabel
from .bars import _StatBar, _TriStatBar

_ME_BG = QColor(30, 144, 255, 51)  # 20% transparent blue

class PlayerRow(QWidget):
    """Single player stat entry: name | stat bar | score."""

    def __init__(
        self,
        name: str,
        value: float = 0.0,
        total: float = 0.0,
        score: float = 0.0,
        is_me: bool = False,
        name_size: int = 9,
        name_color: str = "#FFFFFF",
        score_show: bool = True,
        score_size: int = 9,
        score_color: str = "#FFFFFF",
        stat_show: bool = True,
        stat_size: int = 8,
        stat_color: str = "#FFFFFF",
        avg_show: bool = True,
        total_show: bool = True,
        border_show: bool = False,
        border_size: int = 1,
        border_color: str = "#FFFFFF",
        bar_color: str = "#1E90FF",
        bar_bg_show: bool = True,
        bar_bg_size: int = 12,
        bar_bg_color: str = "#FFFFFF",
        bar_fg_show: bool = True,
        bar_fg_size: int = 71,
        outline_show: bool = False,
        outline_size: int = 1,
        outline_color: str = "#000000",
        row_height: int = 24,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._is_me = is_me
        self._name_size = name_size
        self._name_color = name_color
        self._name_col_color = "transparent"
        self._score_size = score_size
        self._score_color = score_color
        self._outline_show = outline_show
        self._outline_size = outline_size
        self._outline_qcolor = QColor(outline_color)
        self.setFixedHeight(row_height)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        self._name_lbl = _OutlineLabel(name)
        self._name_lbl.setStyleSheet(
            f"color: {name_color}; font-size: {name_size}px; font-weight: bold; background: transparent;"
        )
        self._name_lbl.set_fill_color(name_color)
        self._name_lbl.set_outline(outline_show, outline_size, QColor(outline_color))
        self._name_lbl.setFixedWidth(100)   # Player Name Width
        self._name_lbl.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )
        layout.addWidget(self._name_lbl)

        self._bar = _StatBar(
            value=value,
            total=total,
            stat_show=stat_show,
            stat_size=stat_size,
            stat_color=stat_color,
            avg_show=avg_show,
            total_show=total_show,
            border_show=border_show,
            border_size=border_size,
            border_color=border_color,
            bar_color=bar_color,
            bar_bg_show=bar_bg_show,
            bar_bg_size=bar_bg_size,
            bar_bg_color=bar_bg_color,
            bar_fg_show=bar_fg_show,
            bar_fg_size=bar_fg_size,
            outline_show=outline_show,
            outline_size=outline_size,
            outline_color=outline_color,
        )
        self._bar.setFixedHeight(max(8, row_height - 8))
        layout.addWidget(self._bar, 1)

        self._score_lbl = _OutlineLabel(fmt_num(score))
        self._score_lbl.setStyleSheet(
            f"color: {score_color}; font-size: {score_size}px; font-weight: bold; background: transparent;"
        )
        self._score_lbl.set_fill_color(score_color)
        self._score_lbl.set_outline(outline_show, outline_size, QColor(outline_color))
        self._score_lbl.setFixedWidth(48)   # Score Width (+12px)
        self._score_lbl.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
        )
        self._score_lbl.setVisible(score_show)
        layout.addWidget(self._score_lbl)

    # ── name helpers ─────────────────────────────────────────────────────────
    def _update_name_style(self):
        self._name_lbl.setStyleSheet(
            f"color: {self._name_color}; font-size: {self._name_size}px;"
            f" font-weight: bold; background: {self._name_col_color};"
        )
        self._name_lbl.set_fill_color(self._name_color)
        self._name_lbl.set_bg_color(self._name_col_color)

    def set_name_size(self, v: int) -> None:
        self._name_size = v
        self._update_name_style()

    def set_name_color(self, c: str) -> None:
        self._name_color = c
        self._update_name_style()

    def set_name_col_color(self, c: str) -> None:
        self._name_col_color = c
        self._update_name_style()

    # ── score helpers ─────────────────────────────────────────────────────────
    def _update_score_style(self):
        self._score_lbl.setStyleSheet(
            f"color: {self._score_color}; font-size: {self._score_size}px;"
            " font-weight: bold; background: transparent;"
        )
        self._score_lbl.set_fill_color(self._score_color)

    def set_score_show(self, b: bool) -> None:
        self._score_lbl.setVisible(b)

    def set_score_size(self, v: int) -> None:
        self._score_size = v
        self._update_score_style()

    def set_score_color(self, c: str) -> None:
        self._score_color = c
        self._update_score_style()

    # ── bar proxies ───────────────────────────────────────────────────────────
    def set_stat_show(self, b: bool) -> None:
        self._bar.set_stat_show(b)

    def set_stat_size(self, v: int) -> None:
        self._bar.set_stat_size(v)

    def set_stat_color(self, c: str) -> None:
        self._bar.set_stat_color(c)

    def set_avg_show(self, b: bool) -> None:
        self._bar.set_avg_show(b)

    def set_total_show(self, b: bool) -> None:
        self._bar.set_total_show(b)

    def set_border_show(self, b: bool) -> None:
        self._bar.set_border_show(b)

    def set_border_size(self, v: int) -> None:
        self._bar.set_border_size(v)

    def set_border_color(self, c: str) -> None:
        self._bar.set_border_color(c)

    def set_bar_bg_show(self, b: bool) -> None:
        self._bar.set_bar_bg_show(b)

    def set_bar_bg_size(self, v: int) -> None:
        self._bar.set_bar_bg_size(v)

    def set_bar_bg_color(self, c: str) -> None:
        self._bar.set_bar_bg_color(c)

    def set_bar_fg_show(self, b: bool) -> None:
        self._bar.set_bar_fg_show(b)

    def set_bar_fg_size(self, v: int) -> None:
        self._bar.set_bar_fg_size(v)

    def set_bar_fg_color(self, c: str) -> None:
        self._bar.set_bar_fg_color(c)

    # ── outline helpers ───────────────────────────────────────────────────────
    def set_outline_show(self, b: bool) -> None:
        self._outline_show = b
        self._name_lbl.set_outline(b, self._outline_size, self._outline_qcolor)
        self._score_lbl.set_outline(b, self._outline_size, self._outline_qcolor)
        self._bar.set_outline_show(b)

    def set_outline_size(self, v: int) -> None:
        self._outline_size = v
        self._name_lbl.set_outline(self._outline_show, v, self._outline_qcolor)
        self._score_lbl.set_outline(self._outline_show, v, self._outline_qcolor)
        self._bar.set_outline_size(v)

    def set_outline_color(self, c: str) -> None:
        self._outline_qcolor = QColor(c)
        self._name_lbl.set_outline(self._outline_show, self._outline_size, self._outline_qcolor)
        self._score_lbl.set_outline(self._outline_show, self._outline_size, self._outline_qcolor)
        self._bar.set_outline_color(c)

    def set_row_height(self, v: int) -> None:
        self.setFixedHeight(v)
        self._bar.setFixedHeight(max(8, v - 8))

    def paintEvent(self, event):  # pylint: disable=unused-argument
        if self._is_me:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(_ME_BG)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 3, 3)
        super().paintEvent(event)


# ── tri-stat bar (DPS | DEF | HEAL in one bar) ───────────────────────────────

class _SummaryPlayerRow(QWidget):
    """Player row for the Summary overlay: name | tri-stat bar | score."""

    def __init__(
        self,
        name: str,
        dps_value: float = 0.0,
        dps_total: float = 0.0,
        def_value: float = 0.0,
        def_total: float = 0.0,
        heal_value: float = 0.0,
        heal_total: float = 0.0,
        score: float = 0.0,
        is_me: bool = False,
        name_size: int = 9,
        name_color: str = "#FFFFFF",
        score_show: bool = True,
        score_size: int = 9,
        score_color: str = "#FFD700",
        dps_stat_show: bool = True,
        dps_stat_size: int = 8,
        dps_stat_color: str = "#FF8C00",
        dps_avg_show: bool = True,
        dps_total_show: bool = True,
        dps_bar_fg_show: bool = True,
        dps_bar_fg_size: int = 71,
        dps_bar_fg_color: str = "#7A2020",
        def_stat_show: bool = True,
        def_stat_size: int = 8,
        def_stat_color: str = "#4169E1",
        def_avg_show: bool = True,
        def_total_show: bool = True,
        def_bar_fg_show: bool = True,
        def_bar_fg_size: int = 71,
        def_bar_fg_color: str = "#1E3A7A",
        heal_stat_show: bool = True,
        heal_stat_size: int = 8,
        heal_stat_color: str = "#32CD32",
        heal_avg_show: bool = True,
        heal_total_show: bool = True,
        heal_bar_fg_show: bool = True,
        heal_bar_fg_size: int = 71,
        heal_bar_fg_color: str = "#1E6B1E",
        bar_bg_show: bool = True,
        bar_bg_size: int = 12,
        bar_bg_color: str = "#FFFFFF",
        border_show: bool = False,
        border_size: int = 1,
        border_color: str = "#FFFFFF",
        outline_show: bool = False,
        outline_size: int = 1,
        outline_color: str = "#000000",
        row_height: int = 24,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._is_me = is_me
        self._name_size = name_size
        self._name_color = name_color
        self._name_col_color = "transparent"
        self._score_size = score_size
        self._score_color = score_color
        self._outline_show = outline_show
        self._outline_size = outline_size
        self._outline_qcolor = QColor(outline_color)
        self.setFixedHeight(row_height)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        self._name_lbl = _OutlineLabel(name)
        self._name_lbl.setStyleSheet(
            f"color: {name_color}; font-size: {name_size}px; font-weight: bold; background: transparent;"
        )
        self._name_lbl.set_fill_color(name_color)
        self._name_lbl.set_outline(outline_show, outline_size, QColor(outline_color))
        self._name_lbl.setFixedWidth(100)    # Player Name Column Width
        self._name_lbl.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )
        layout.addWidget(self._name_lbl)

        self._bar = _TriStatBar(
            dps_value=dps_value,
            dps_total=dps_total,
            def_value=def_value,
            def_total=def_total,
            heal_value=heal_value,
            heal_total=heal_total,
            dps_stat_show=dps_stat_show,
            dps_stat_size=dps_stat_size,
            dps_stat_color=dps_stat_color,
            dps_avg_show=dps_avg_show,
            dps_total_show=dps_total_show,
            dps_bar_fg_show=dps_bar_fg_show,
            dps_bar_fg_size=dps_bar_fg_size,
            dps_bar_fg_color=dps_bar_fg_color,
            def_stat_show=def_stat_show,
            def_stat_size=def_stat_size,
            def_stat_color=def_stat_color,
            def_avg_show=def_avg_show,
            def_total_show=def_total_show,
            def_bar_fg_show=def_bar_fg_show,
            def_bar_fg_size=def_bar_fg_size,
            def_bar_fg_color=def_bar_fg_color,
            heal_stat_show=heal_stat_show,
            heal_stat_size=heal_stat_size,
            heal_stat_color=heal_stat_color,
            heal_avg_show=heal_avg_show,
            heal_total_show=heal_total_show,
            heal_bar_fg_show=heal_bar_fg_show,
            heal_bar_fg_size=heal_bar_fg_size,
            heal_bar_fg_color=heal_bar_fg_color,
            bar_bg_show=bar_bg_show,
            bar_bg_size=bar_bg_size,
            bar_bg_color=bar_bg_color,
            border_show=border_show,
            border_size=border_size,
            border_color=border_color,
            outline_show=outline_show,
            outline_size=outline_size,
            outline_color=outline_color,
        )
        self._bar.setFixedHeight(max(8, row_height - 8))
        layout.addWidget(self._bar, 1)

        self._score_lbl = _OutlineLabel(fmt_num(score))
        self._score_lbl.setStyleSheet(
            f"color: {score_color}; font-size: {score_size}px; font-weight: bold; background: transparent;"
        )
        self._score_lbl.set_fill_color(score_color)
        self._score_lbl.set_outline(outline_show, outline_size, QColor(outline_color))
        self._score_lbl.setFixedWidth(48)    # Score Column Width (+12px)
        self._score_lbl.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
        )
        self._score_lbl.setVisible(score_show)
        layout.addWidget(self._score_lbl)

    # ── name ─────────────────────────────────────────────────────────────────
    def _update_name_style(self):
        self._name_lbl.setStyleSheet(
            f"color: {self._name_color}; font-size: {self._name_size}px;"
            f" font-weight: bold; background: {self._name_col_color};"
        )
        self._name_lbl.set_fill_color(self._name_color)
        self._name_lbl.set_bg_color(self._name_col_color)

    def set_name_size(self, v: int) -> None:
        self._name_size = v
        self._update_name_style()

    def set_name_color(self, c: str) -> None:
        self._name_color = c
        self._update_name_style()

    def set_name_col_color(self, c: str) -> None:
        self._name_col_color = c
        self._update_name_style()

    # ── score ─────────────────────────────────────────────────────────────────
    def _update_score_style(self):
        self._score_lbl.setStyleSheet(
            f"color: {self._score_color}; font-size: {self._score_size}px;"
            " font-weight: bold; background: transparent;"
        )
        self._score_lbl.set_fill_color(self._score_color)

    def set_score_show(self, b: bool) -> None:
        self._score_lbl.setVisible(b)

    def set_score_size(self, v: int) -> None:
        self._score_size = v
        self._update_score_style()

    def set_score_color(self, c: str) -> None:
        self._score_color = c
        self._update_score_style()

    # ── proxy all bar setters ─────────────────────────────────────────────────
    def set_avg_show(self, b: bool) -> None:
        self._bar.set_avg_show(b)

    def set_total_show(self, b: bool) -> None:
        self._bar.set_total_show(b)

    def set_border_show(self, b: bool) -> None:
        self._bar.set_border_show(b)

    def set_border_size(self, v: int) -> None:
        self._bar.set_border_size(v)

    def set_border_color(self, c: str) -> None:
        self._bar.set_border_color(c)

    def set_bar_bg_show(self, b: bool) -> None:
        self._bar.set_bar_bg_show(b)

    def set_bar_bg_size(self, v: int) -> None:
        self._bar.set_bar_bg_size(v)

    def set_bar_bg_color(self, c: str) -> None:
        self._bar.set_bar_bg_color(c)

    def set_dps_stat_show(self, b: bool) -> None:
        self._bar.set_dps_stat_show(b)

    def set_dps_stat_size(self, v: int) -> None:
        self._bar.set_dps_stat_size(v)

    def set_dps_stat_color(self, c: str) -> None:
        self._bar.set_dps_stat_color(c)

    def set_dps_bar_fg_show(self, b: bool) -> None:
        self._bar.set_dps_bar_fg_show(b)

    def set_dps_bar_fg_size(self, v: int) -> None:
        self._bar.set_dps_bar_fg_size(v)

    def set_dps_bar_fg_color(self, c: str) -> None:
        self._bar.set_dps_bar_fg_color(c)

    def set_def_stat_show(self, b: bool) -> None:
        self._bar.set_def_stat_show(b)

    def set_def_stat_size(self, v: int) -> None:
        self._bar.set_def_stat_size(v)

    def set_def_stat_color(self, c: str) -> None:
        self._bar.set_def_stat_color(c)

    def set_def_bar_fg_show(self, b: bool) -> None:
        self._bar.set_def_bar_fg_show(b)

    def set_def_bar_fg_size(self, v: int) -> None:
        self._bar.set_def_bar_fg_size(v)

    def set_def_bar_fg_color(self, c: str) -> None:
        self._bar.set_def_bar_fg_color(c)

    def set_heal_stat_show(self, b: bool) -> None:
        self._bar.set_heal_stat_show(b)

    def set_heal_stat_size(self, v: int) -> None:
        self._bar.set_heal_stat_size(v)

    def set_heal_stat_color(self, c: str) -> None:
        self._bar.set_heal_stat_color(c)

    def set_heal_bar_fg_show(self, b: bool) -> None:
        self._bar.set_heal_bar_fg_show(b)

    def set_heal_bar_fg_size(self, v: int) -> None:
        self._bar.set_heal_bar_fg_size(v)

    def set_heal_bar_fg_color(self, c: str) -> None:
        self._bar.set_heal_bar_fg_color(c)

    # ── outline helpers ───────────────────────────────────────────────────────
    def set_outline_show(self, b: bool) -> None:
        self._outline_show = b
        self._name_lbl.set_outline(b, self._outline_size, self._outline_qcolor)
        self._score_lbl.set_outline(b, self._outline_size, self._outline_qcolor)
        self._bar.set_outline_show(b)

    def set_outline_size(self, v: int) -> None:
        self._outline_size = v
        self._name_lbl.set_outline(self._outline_show, v, self._outline_qcolor)
        self._score_lbl.set_outline(self._outline_show, v, self._outline_qcolor)
        self._bar.set_outline_size(v)

    def set_outline_color(self, c: str) -> None:
        self._outline_qcolor = QColor(c)
        self._name_lbl.set_outline(self._outline_show, self._outline_size, self._outline_qcolor)
        self._score_lbl.set_outline(self._outline_show, self._outline_size, self._outline_qcolor)
        self._bar.set_outline_color(c)

    def set_row_height(self, v: int) -> None:
        self.setFixedHeight(v)
        self._bar.setFixedHeight(max(8, v - 8))

    def paintEvent(self, event):  # pylint: disable=unused-argument
        if self._is_me:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(_ME_BG)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 3, 3)
        super().paintEvent(event)


# ── shared player-list base ───────────────────────────────────────────────────

