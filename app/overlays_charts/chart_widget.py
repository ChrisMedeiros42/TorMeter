"""Chart rendering widget used by the charts overlay."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

from app.constants import fmt_num

from .constants import (
    _BAR_H,
    _BAR_SPACING,
    _LINE_COLORS,
    _ME_FG,
    _NAME_W,
    _OTHER_FG,
    _VAL_W,
)

class _ChartWidget(QWidget):
    """Custom-painted horizontal bar chart."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: list[tuple[str, float, bool]] = []  # (name, value, is_me)
        self._line_data: dict[str, tuple[bool, list[float | None]]] = {}
        self._line_labels: list[str] = []
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._update_height()
        # Appearance (settable via OverlayMaster)
        self._name_pt: int = 7
        self._val_pt: int = 7
        self._me_fg: QColor = QColor(_ME_FG)
        self._other_fg: QColor = QColor(_OTHER_FG)
        self._name_color_me: QColor = QColor("white")
        self._name_color_other: QColor = QColor(200, 200, 200)
        self._chart_type: str = "Bar"

    def set_data(self, entries: list[tuple[str, float, bool]]) -> None:
        self._entries = entries
        self._update_height()
        self.update()

    def set_chart_type(self, t: str) -> None:
        self._chart_type = t
        self._update_height()
        self.update()

    def set_line_data(
        self,
        player_series: dict[str, tuple[bool, list[float | None]]],
        fight_labels: list[str],
    ) -> None:
        self._line_data = player_series
        self._line_labels = fight_labels
        self._update_height()
        self.update()

    def _update_height(self):
        t = getattr(self, "_chart_type", "Bar")
        if t == "Pie":
            n = max(len(self._entries), 1)
            size = max(160, min(240, n * 20))
            self.setFixedHeight(size + 30)  # pie + legend
        elif t == "Line":
            n_players = max(len(getattr(self, "_line_data", {})), 1)
            self.setFixedHeight(max(160, 120 + n_players * 12))
        else:
            n = max(len(self._entries), 1)
            self.setFixedHeight(n * (_BAR_H + _BAR_SPACING) + _BAR_SPACING)

    def set_name_size(self, pt: int) -> None:
        self._name_pt = max(1, int(pt))
        self.update()

    def set_val_size(self, pt: int) -> None:
        self._val_pt = max(1, int(pt))
        self.update()

    def set_me_color(self, c: QColor) -> None:
        self._me_fg = c
        self.update()

    def set_other_color(self, c: QColor) -> None:
        self._other_fg = c
        self.update()

    def set_name_color(self, me: QColor, other: QColor) -> None:
        self._name_color_me = me
        self._name_color_other = other
        self.update()

    def paintEvent(self, event):  # pylint: disable=unused-argument
        t = getattr(self, "_chart_type", "Bar")
        if t == "Line":
            self._paint_line()
        elif not self._entries:
            return
        elif t == "Pie":
            self._paint_pie()
        else:
            self._paint_bar()

    def _paint_bar(self):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        bar_area_w = w - _NAME_W - _VAL_W - 8
        max_val = max(v for _, v, _ in self._entries) or 1.0
        if max_val <= 0:
            max_val = 1.0

        name_font = QFont()
        name_font.setPointSize(max(1, int(self._name_pt)))
        val_font = QFont()
        val_font.setPointSize(max(1, int(self._val_pt)))

        for i, (name, val, is_me) in enumerate(self._entries):
            y = _BAR_SPACING + i * (_BAR_H + _BAR_SPACING)
            # Bar background
            painter.setBrush(QColor(255, 255, 255, 15))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRect(_NAME_W, y, bar_area_w, _BAR_H), 3, 3)
            # Bar fill
            fill_w = int(bar_area_w * val / max_val)
            if fill_w > 0:
                color = self._me_fg if is_me else self._other_fg
                painter.setBrush(color)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(QRect(_NAME_W, y, fill_w, _BAR_H), 3, 3)
            # Name
            painter.setFont(name_font)
            painter.setPen(self._name_color_me if is_me else self._name_color_other)
            painter.drawText(
                QRect(0, y, _NAME_W - 4, _BAR_H),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                name,
            )
            # Value
            painter.setFont(val_font)
            painter.setPen(QColor(255, 200, 80) if is_me else QColor(180, 180, 180))
            painter.drawText(
                QRect(_NAME_W + bar_area_w + 4, y, _VAL_W, _BAR_H),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                fmt_num(val),
            )

    def _paint_line(self):
        """Line chart: per-player time series across fights."""
        if not self._line_data or not self._line_labels:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        pad_l, pad_r, pad_t, pad_b = 44, 8, 10, 28
        plot_w = w - pad_l - pad_r
        plot_h = h - pad_t - pad_b

        n_fights = len(self._line_labels)
        if n_fights == 0:
            return

        all_vals = [
            v
            for _is_me, vals in self._line_data.values()
            for v in vals
            if v is not None
        ]
        max_val = max(all_vals) if all_vals else 1.0
        if max_val <= 0:
            max_val = 1.0

        name_font = QFont()
        name_font.setPointSize(max(1, int(self._name_pt)))
        val_font = QFont()
        val_font.setPointSize(max(self._val_pt - 1, 6))

        def _sample_indices(length: int, target_count: int) -> list[int]:
            if length <= 0:
                return []
            if target_count >= length:
                return list(range(length))
            if target_count <= 1:
                return [0]
            out: list[int] = []
            seen: set[int] = set()
            for k in range(target_count):
                idx = int(round(k * (length - 1) / (target_count - 1)))
                if idx not in seen:
                    out.append(idx)
                    seen.add(idx)
            return out

        x_step = plot_w / max(n_fights - 1, 1)
        x_positions = [int(pad_l + i * x_step) for i in range(n_fights)]

        # Choose Y tick density from available pixel height, capped at 10 labels.
        y_metrics = QFontMetrics(val_font)
        y_label_h = max(1, y_metrics.height())
        y_ticks_by_space = int(plot_h / (y_label_h + 4)) + 1
        y_tick_count = min(10, max(2, y_ticks_by_space))

        # Choose X tick density from available pixel width and text width,
        # capped at 10 labels and sampled evenly.
        x_metrics = QFontMetrics(name_font)
        max_x_label_w = max(
            16,
            max((x_metrics.horizontalAdvance(lbl) for lbl in self._line_labels), default=16)
            + 10,
        )
        if n_fights <= 1:
            x_tick_count = 1
        else:
            x_ticks_by_space = int(plot_w / max_x_label_w) + 1
            x_tick_count = min(10, n_fights, max(2, x_ticks_by_space))
        x_label_indices = _sample_indices(n_fights, x_tick_count)

        # Grid lines
        painter.setPen(QPen(QColor(255, 255, 255, 20), 1))
        y_den = max(y_tick_count - 1, 1)
        for i in range(y_tick_count):
            gy = int(pad_t + plot_h * i / y_den)
            painter.drawLine(pad_l, gy, pad_l + plot_w, gy)

        # Y axis
        painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
        painter.drawLine(pad_l, pad_t, pad_l, pad_t + plot_h)

        # Y axis labels
        painter.setFont(val_font)
        for i in range(y_tick_count):
            ratio = i / y_den
            val = max_val * (1.0 - ratio)
            gy = int(pad_t + plot_h * ratio)
            painter.setPen(QColor(255, 255, 255, 120))
            label = fmt_num(val)
            painter.drawText(
                QRect(0, gy - 6, pad_l - 4, 12),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                label,
            )

        # X axis fight labels
        painter.setFont(name_font)
        for i in x_label_indices:
            label = self._line_labels[i]
            painter.setPen(QColor(255, 255, 255, 100))
            painter.drawText(
                QRect(
                    x_positions[i] - max_x_label_w // 2,
                    pad_t + plot_h + 4,
                    max_x_label_w,
                    pad_b - 4,
                ),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                label,
            )

        # Draw each player's line and dots
        other_idx = 0
        player_colors: dict[str, QColor] = {}
        for pname, (is_me, _vals) in self._line_data.items():
            if is_me:
                player_colors[pname] = self._me_fg
            else:
                player_colors[pname] = _LINE_COLORS[other_idx % len(_LINE_COLORS)]
                other_idx += 1

        for pname, (is_me, vals) in self._line_data.items():
            color = player_colors[pname]
            points = []
            for i, v in enumerate(vals):
                if v is not None and i < len(x_positions):
                    x = x_positions[i]
                    y = int(pad_t + plot_h * (1.0 - v / max_val))
                    points.append((x, y))
            if not points:
                continue
            if len(points) > 1:
                painter.setPen(QPen(color, 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                for j in range(len(points) - 1):
                    painter.drawLine(
                        points[j][0],
                        points[j][1],
                        points[j + 1][0],
                        points[j + 1][1],
                    )
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            for x, y in points:
                painter.drawEllipse(x - 4, y - 4, 8, 8)

        # Inline legend (top-left of plot area): cap to 10 names and prevent overlap.
        legend_limit = 10

        def _latest_non_none(vals: list[float | None]) -> float:
            for v in reversed(vals):
                if v is not None:
                    return float(v)
            return -1.0

        def _peak_non_none(vals: list[float | None]) -> float:
            nums = [float(v) for v in vals if v is not None]
            return max(nums) if nums else -1.0

        legend_items = sorted(
            self._line_data.items(),
            key=lambda item: (
                0 if item[1][0] else 1,  # me first
                -_latest_non_none(item[1][1]),
                -_peak_non_none(item[1][1]),
                item[0].casefold(),
            ),
        )
        visible_legend = legend_items[:legend_limit]
        hidden_count = max(0, len(legend_items) - len(visible_legend))

        # Build drawable legend rows: (label, is_me, color, draw_marker)
        legend_rows: list[tuple[str, bool, QColor, bool]] = [
            (pname, is_me, player_colors[pname], True)
            for pname, (is_me, _vals) in visible_legend
        ]
        if hidden_count > 0:
            legend_rows.append((f"+{hidden_count} more", False, QColor(170, 170, 170), False))

        painter.setFont(name_font)
        legend_metrics = QFontMetrics(name_font)
        row_h = max(12, legend_metrics.height() + 2)
        marker_w = 10

        # Fit legend rows inside plot area using 1-2 columns to avoid label overlap.
        legend_x = pad_l + 6
        legend_y = pad_t + 2
        avail_h = max(1, plot_h - 4)
        max_rows_per_col = max(1, avail_h // row_h)
        total_rows = len(legend_rows)
        if total_rows <= max_rows_per_col:
            col_count = 1
        else:
            col_count = 2
        rows_per_col = max(1, (total_rows + col_count - 1) // col_count)
        col_w = max(80, min(160, max(80, (plot_w - 12) // col_count)))
        text_w = max(40, col_w - marker_w - 6)

        for idx, (label, is_me, color, draw_marker) in enumerate(legend_rows):
            col = idx // rows_per_col
            row = idx % rows_per_col
            x = legend_x + col * col_w
            y = legend_y + row * row_h
            if y + row_h > pad_t + plot_h:
                continue

            if draw_marker:
                painter.setBrush(color)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(x, y + max(1, (row_h - 6) // 2), 6, 6)

            painter.setPen(self._name_color_me if is_me else self._name_color_other)
            text = legend_metrics.elidedText(
                label,
                Qt.TextElideMode.ElideRight,
                text_w,
            )
            painter.drawText(
                QRect(x + marker_w, y, text_w, row_h),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                text,
            )

    def _paint_pie(self):
        """Pie chart with player name legend."""
        if not self._entries:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        legend_h = 14 * len(self._entries)
        pie_h = max(h - legend_h - 4, 80)
        pie_size = min(w - 16, pie_h)
        pie_x = (w - pie_size) // 2
        pie_rect = QRect(pie_x, 4, pie_size, pie_size)

        total = sum(v for _, v, _ in self._entries) or 1.0
        start_angle = 90 * 16  # 12 o'clock in Qt units

        name_font = QFont()
        name_font.setPointSize(max(1, int(self._name_pt)))
        painter.setFont(name_font)

        colors = [
            QColor(self._me_fg if is_me else self._other_fg)
            for _, _, is_me in self._entries
        ]
        # Give each non-me slice a distinct hue
        other_hues = [30, 60, 120, 180, 210, 270, 300, 330]
        other_idx = 0
        for i, (_, _, is_me) in enumerate(self._entries):
            if not is_me:
                colors[i] = QColor.fromHsv(
                    other_hues[other_idx % len(other_hues)], 160, 200, 200
                )
                other_idx += 1

        for i, (name, val, is_me) in enumerate(self._entries):
            span = int(360 * 16 * val / total)
            painter.setBrush(colors[i])
            painter.setPen(QPen(QColor(0, 0, 0, 80), 1))
            painter.drawPie(pie_rect, start_angle, span)
            start_angle += span

        # Legend below pie
        legend_y = pie_h + 8
        for i, (name, val, is_me) in enumerate(self._entries):
            row_y = legend_y + i * 14
            painter.setBrush(colors[i])
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(4, row_y + 2, 10, 10)
            painter.setPen(self._name_color_me if is_me else self._name_color_other)
            pct = val / total * 100
            painter.drawText(
                QRect(18, row_y, w - 22, 14),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                f"{name[:14]}  {fmt_num(val)} ({pct:.0f}%)",
            )



