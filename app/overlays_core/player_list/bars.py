"""Bar widgets for player-list overlays."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

from app.constants import fmt_num

class _StatBar(QWidget):
    """Horizontal bar with configurable fill, border, and stat text."""

    def __init__(
        self,
        value: float = 0.0,
        total: float = 0.0,
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
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._value = value
        self._total = total
        self._stat_show = stat_show
        self._stat_size = stat_size
        self._stat_qcolor = QColor(stat_color)
        self._avg_show = avg_show
        self._total_show = total_show
        self._border_show = border_show
        self._border_size = border_size
        self._border_qcolor = QColor(border_color)
        self._bar_fg_color_hex = bar_color
        self._bar_fg_size = bar_fg_size
        self._bar_fg_show = bar_fg_show
        _bc = QColor(bar_color)
        _bc.setAlpha(int(bar_fg_size / 100 * 255))
        self._bar_qcolor = _bc
        self._bar_bg_color_hex = bar_bg_color
        self._bar_bg_size = bar_bg_size
        self._bar_bg_show = bar_bg_show
        _bg = QColor(bar_bg_color)
        _bg.setAlpha(int(bar_bg_size / 100 * 255))
        self._bar_bg_qcolor = _bg
        self._fill_value = value
        self._fill_total = total if total > 0 else 1.0
        self._outline_show = outline_show
        self._outline_size = outline_size
        self._outline_qcolor = QColor(outline_color)
        self.setFixedHeight(16)
        self.setMinimumWidth(100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def update_data(
        self,
        value: float,
        total: float,
        fill_value: float | None = None,
        fill_total: float | None = None,
    ):
        self._value = value
        self._total = total
        self._fill_value = fill_value if fill_value is not None else value
        self._fill_total = (fill_total if fill_total is not None else total) or 1.0
        self.update()

    def set_stat_show(self, b: bool):
        self._stat_show = b
        self.update()

    def set_stat_size(self, v: int):
        self._stat_size = v
        self.update()

    def set_stat_color(self, c: str):
        self._stat_qcolor = QColor(c)
        self.update()

    def set_avg_show(self, b: bool):
        self._avg_show = b
        self.update()

    def set_total_show(self, b: bool):
        self._total_show = b
        self.update()

    def set_border_show(self, b: bool):
        self._border_show = b
        self.update()

    def set_border_size(self, v: int):
        self._border_size = v
        self.update()

    def set_border_color(self, c: str):
        self._border_qcolor = QColor(c)
        self.update()

    def set_bar_bg_show(self, b: bool):
        self._bar_bg_show = b
        self.update()

    def _rebuild_bar_bg_qcolor(self):
        _bg = QColor(self._bar_bg_color_hex)
        _bg.setAlpha(int(self._bar_bg_size / 100 * 255))
        self._bar_bg_qcolor = _bg
        self.update()

    def set_bar_bg_size(self, v: int):
        self._bar_bg_size = v
        self._rebuild_bar_bg_qcolor()

    def set_bar_bg_color(self, c: str):
        self._bar_bg_color_hex = c
        self._rebuild_bar_bg_qcolor()

    def set_bar_fg_show(self, b: bool):
        self._bar_fg_show = b
        self.update()

    def _rebuild_bar_fg_qcolor(self):
        _bc = QColor(self._bar_fg_color_hex)
        _bc.setAlpha(int(self._bar_fg_size / 100 * 255))
        self._bar_qcolor = _bc
        self.update()

    def set_bar_fg_size(self, v: int):
        self._bar_fg_size = v
        self._rebuild_bar_fg_qcolor()

    def set_bar_fg_color(self, c: str):
        self._bar_fg_color_hex = c
        self._rebuild_bar_fg_qcolor()

    def set_outline_show(self, b: bool) -> None:
        self._outline_show = b
        self.update()

    def set_outline_size(self, v: int) -> None:
        self._outline_size = v
        self.update()

    def set_outline_color(self, c: str) -> None:
        self._outline_qcolor = QColor(c)
        self.update()

    def paintEvent(self, event):  # pylint: disable=unused-argument
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Background track
        if self._bar_bg_show:
            painter.setBrush(self._bar_bg_qcolor)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(0, 0, w, h, 3, 3)

        # Filled portion
        ratio = self._fill_value / self._fill_total
        fill_w = int(w * max(0.0, min(1.0, ratio)))
        if self._bar_fg_show and fill_w > 0:
            painter.setBrush(self._bar_qcolor)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(0, 0, fill_w, h, 3, 3)

        # Border
        if self._border_show and self._border_size > 0:
            inset = int(self._border_size / 2)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(self._border_qcolor, self._border_size))
            painter.drawRoundedRect(
                QRect(0, 0, w, h).adjusted(inset, inset, -inset, -inset), 3, 3
            )

        # Text
        if self._stat_show:
            parts: list[str] = []
            if self._avg_show:
                parts.append(fmt_num(self._value))
            if self._total_show:
                parts.append(fmt_num(self._total))
            if parts:
                text = " / ".join(parts)
                font = QFont()
                font.setPointSize(self._stat_size)
                font.setBold(True)
                if self._outline_show and self._outline_size > 0:
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    fm = QFontMetrics(font)
                    r = self.rect()
                    br = fm.boundingRect(r, int(Qt.AlignmentFlag.AlignCenter), text)
                    path = QPainterPath()
                    path.addText(br.x(), br.y() + fm.ascent(), font, text)
                    pen = QPen(self._outline_qcolor, self._outline_size * 2)
                    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                    painter.setPen(pen)
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawPath(path)
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(self._stat_qcolor)
                    painter.drawPath(path)
                else:
                    painter.setPen(self._stat_qcolor)
                    painter.setFont(font)
                    painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)


# ── player row ───────────────────────────────────────────────────────────────
_ME_BG = QColor(30, 144, 255, 51)  # 20% transparent blue


class _TriStatBar(QWidget):
    """One bar divided into 3 proportional segments: DPS | DEF | HEAL."""

    def __init__(
        self,
        dps_value: float = 0.0,
        dps_total: float = 0.0,
        def_value: float = 0.0,
        def_total: float = 0.0,
        heal_value: float = 0.0,
        heal_total: float = 0.0,
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
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._dps_value = dps_value
        self._dps_total = dps_total
        self._def_value = def_value
        self._def_total = def_total
        self._heal_value = heal_value
        self._heal_total = heal_total
        self._fill_frac: float = 1.0
        # DPS
        self._dps_stat_show = dps_stat_show
        self._dps_stat_size = dps_stat_size
        self._dps_stat_qcolor = QColor(dps_stat_color)
        self._dps_avg_show = dps_avg_show
        self._dps_total_show = dps_total_show
        self._dps_fg_show = dps_bar_fg_show
        self._dps_fg_size = dps_bar_fg_size
        self._dps_fg_hex = dps_bar_fg_color
        self._dps_fg_qcolor = self._alpha(dps_bar_fg_color, dps_bar_fg_size)
        # DEF
        self._def_stat_show = def_stat_show
        self._def_stat_size = def_stat_size
        self._def_stat_qcolor = QColor(def_stat_color)
        self._def_avg_show = def_avg_show
        self._def_total_show = def_total_show
        self._def_fg_show = def_bar_fg_show
        self._def_fg_size = def_bar_fg_size
        self._def_fg_hex = def_bar_fg_color
        self._def_fg_qcolor = self._alpha(def_bar_fg_color, def_bar_fg_size)
        # HEAL
        self._heal_stat_show = heal_stat_show
        self._heal_stat_size = heal_stat_size
        self._heal_stat_qcolor = QColor(heal_stat_color)
        self._heal_avg_show = heal_avg_show
        self._heal_total_show = heal_total_show
        self._heal_fg_show = heal_bar_fg_show
        self._heal_fg_size = heal_bar_fg_size
        self._heal_fg_hex = heal_bar_fg_color
        self._heal_fg_qcolor = self._alpha(heal_bar_fg_color, heal_bar_fg_size)
        # Shared BG
        self._bg_show = bar_bg_show
        self._bg_size = bar_bg_size
        self._bg_hex = bar_bg_color
        self._bg_qcolor = self._alpha(bar_bg_color, bar_bg_size)
        # Border
        self._border_show = border_show
        self._border_size = border_size
        self._border_qcolor = QColor(border_color)
        # Outline
        self._outline_show = outline_show
        self._outline_size = outline_size
        self._outline_qcolor = QColor(outline_color)

        self.setFixedHeight(16)
        self.setMinimumWidth(100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    @staticmethod
    def _alpha(hex_color: str, size: int) -> QColor:
        c = QColor(hex_color)
        c.setAlpha(int(size / 100 * 255))
        return c

    # ── DPS ──────────────────────────────────────────────────────────────────
    def set_dps_stat_show(self, b: bool) -> None:
        self._dps_stat_show = b
        self.update()

    def set_dps_stat_size(self, v: int) -> None:
        self._dps_stat_size = v
        self.update()

    def set_dps_stat_color(self, c: str) -> None:
        self._dps_stat_qcolor = QColor(c)
        self.update()

    def set_dps_bar_fg_show(self, b: bool) -> None:
        self._dps_fg_show = b
        self.update()

    def set_dps_bar_fg_size(self, v: int) -> None:
        self._dps_fg_size = v
        self._dps_fg_qcolor = self._alpha(self._dps_fg_hex, v)
        self.update()

    def set_dps_bar_fg_color(self, c: str) -> None:
        self._dps_fg_hex = c
        self._dps_fg_qcolor = self._alpha(c, self._dps_fg_size)
        self.update()

    # ── DEF ──────────────────────────────────────────────────────────────────
    def set_def_stat_show(self, b: bool) -> None:
        self._def_stat_show = b
        self.update()

    def set_def_stat_size(self, v: int) -> None:
        self._def_stat_size = v
        self.update()

    def set_def_stat_color(self, c: str) -> None:
        self._def_stat_qcolor = QColor(c)
        self.update()

    def set_def_bar_fg_show(self, b: bool) -> None:
        self._def_fg_show = b
        self.update()

    def set_def_bar_fg_size(self, v: int) -> None:
        self._def_fg_size = v
        self._def_fg_qcolor = self._alpha(self._def_fg_hex, v)
        self.update()

    def set_def_bar_fg_color(self, c: str) -> None:
        self._def_fg_hex = c
        self._def_fg_qcolor = self._alpha(c, self._def_fg_size)
        self.update()

    # ── HEAL ─────────────────────────────────────────────────────────────────
    def set_heal_stat_show(self, b: bool) -> None:
        self._heal_stat_show = b
        self.update()

    def set_heal_stat_size(self, v: int) -> None:
        self._heal_stat_size = v
        self.update()

    def set_heal_stat_color(self, c: str) -> None:
        self._heal_stat_qcolor = QColor(c)
        self.update()

    def set_heal_bar_fg_show(self, b: bool) -> None:
        self._heal_fg_show = b
        self.update()

    def set_heal_bar_fg_size(self, v: int) -> None:
        self._heal_fg_size = v
        self._heal_fg_qcolor = self._alpha(self._heal_fg_hex, v)
        self.update()

    def set_heal_bar_fg_color(self, c: str) -> None:
        self._heal_fg_hex = c
        self._heal_fg_qcolor = self._alpha(c, self._heal_fg_size)
        self.update()

    def update_data(
        self,
        dps_value: float,
        dps_total: float,
        def_value: float,
        def_total: float,
        heal_value: float,
        heal_total: float,
        fill_frac: float = 1.0,
    ) -> None:
        """Update all three bar values and repaint."""
        self._dps_value = dps_value
        self._dps_total = dps_total
        self._def_value = def_value
        self._def_total = def_total
        self._heal_value = heal_value
        self._heal_total = heal_total
        self._fill_frac = max(0.0, min(1.0, fill_frac))
        self.update()

    # ── Shared ───────────────────────────────────────────────────────────────
    def set_avg_show(self, b: bool) -> None:
        self._dps_avg_show = b
        self._def_avg_show = b
        self._heal_avg_show = b
        self.update()

    def set_total_show(self, b: bool) -> None:
        self._dps_total_show = b
        self._def_total_show = b
        self._heal_total_show = b
        self.update()

    def set_bar_bg_show(self, b: bool) -> None:
        self._bg_show = b
        self.update()

    def set_bar_bg_size(self, v: int) -> None:
        self._bg_size = v
        self._bg_qcolor = self._alpha(self._bg_hex, v)
        self.update()

    def set_bar_bg_color(self, c: str) -> None:
        self._bg_hex = c
        self._bg_qcolor = self._alpha(c, self._bg_size)
        self.update()

    def set_border_show(self, b: bool) -> None:
        self._border_show = b
        self.update()

    def set_border_size(self, v: int) -> None:
        self._border_size = v
        self.update()

    def set_border_color(self, c: str) -> None:
        self._border_qcolor = QColor(c)
        self.update()

    def set_outline_show(self, b: bool) -> None:
        self._outline_show = b
        self.update()

    def set_outline_size(self, v: int) -> None:
        self._outline_size = v
        self.update()

    def set_outline_color(self, c: str) -> None:
        self._outline_qcolor = QColor(c)
        self.update()

    def paintEvent(self, event):  # pylint: disable=unused-argument
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Proportions — equal thirds when all zero
        dv = max(self._dps_value, 0.0)
        ev = max(self._def_value, 0.0)
        hv = max(self._heal_value, 0.0)
        total = dv + ev + hv
        if total > 0:
            dps_frac, def_frac = dv / total, ev / total
        else:
            dps_frac = def_frac = 1 / 3
        # Sub-bars are proportional within the player's filled fraction of the bar
        filled_w = round(w * self._fill_frac)
        dps_w = round(filled_w * dps_frac)
        def_w = round(filled_w * def_frac)
        heal_w = filled_w - dps_w - def_w  # remainder avoids float gaps

        # Background track
        if self._bg_show:
            painter.setBrush(self._bg_qcolor)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(0, 0, w, h, 3, 3)

        # Segment fills
        for seg_x, seg_w, fg_show, fg_qcolor in (
            (0, dps_w, self._dps_fg_show, self._dps_fg_qcolor),
            (dps_w, def_w, self._def_fg_show, self._def_fg_qcolor),
            (dps_w + def_w, heal_w, self._heal_fg_show, self._heal_fg_qcolor),
        ):
            if fg_show and seg_w > 0:
                painter.setBrush(fg_qcolor)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRect(QRect(seg_x, 0, seg_w, h))

        # Border
        if self._border_show and self._border_size > 0:
            inset = int(self._border_size / 2)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(self._border_qcolor, self._border_size))
            painter.drawRoundedRect(
                QRect(0, 0, w, h).adjusted(inset, inset, -inset, -inset), 3, 3
            )

        # Text labels — each centered in an equal third of the full bar width
        third = w // 3
        label_rects = (
            QRect(0, 0, third, h),
            QRect(third, 0, third, h),
            QRect(2 * third, 0, w - 2 * third, h),
        )
        font = QFont()
        for lbl_rect, show, size, qcolor, value, tot_val, avg_s, tot_s in (
            (
                label_rects[0],
                self._dps_stat_show,
                self._dps_stat_size,
                self._dps_stat_qcolor,
                self._dps_value,
                self._dps_total,
                self._dps_avg_show,
                self._dps_total_show,
            ),
            (
                label_rects[1],
                self._def_stat_show,
                self._def_stat_size,
                self._def_stat_qcolor,
                self._def_value,
                self._def_total,
                self._def_avg_show,
                self._def_total_show,
            ),
            (
                label_rects[2],
                self._heal_stat_show,
                self._heal_stat_size,
                self._heal_stat_qcolor,
                self._heal_value,
                self._heal_total,
                self._heal_avg_show,
                self._heal_total_show,
            ),
        ):
            if not show or lbl_rect.width() < 12:
                continue
            parts: list[str] = []
            if avg_s:
                parts.append(fmt_num(value))
            if tot_s:
                parts.append(fmt_num(tot_val))
            if not parts:
                continue
            text = " / ".join(parts)
            font.setPointSize(size)
            font.setBold(True)
            if self._outline_show and self._outline_size > 0:
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                fm = QFontMetrics(font)
                br = fm.boundingRect(lbl_rect, int(Qt.AlignmentFlag.AlignCenter), text)
                path = QPainterPath()
                path.addText(br.x(), br.y() + fm.ascent(), font, text)
                pen = QPen(self._outline_qcolor, self._outline_size * 2)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPath(path)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(qcolor)
                painter.drawPath(path)
            else:
                painter.setFont(font)
                painter.setPen(qcolor)
                painter.drawText(
                    lbl_rect,
                    Qt.AlignmentFlag.AlignCenter,
                    text,
                )


# ── summary player row ───────────────────────────────────────────────────────

