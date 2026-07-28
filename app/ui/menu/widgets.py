"""Custom menu widgets used by the TorMeter menu window."""

from __future__ import annotations

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

from .constants import (
    ARROW_W,
    COG_W,
    RESET_BTN_H,
    RESET_BTN_W,
    ROW_HEIGHT,
    TOGGLE_H,
    TOGGLE_RADIUS,
    TOGGLE_W,
)


class MenuButton(QWidget):
    """Custom-painted toggle button with an embedded arrow and settings zone."""

    def __init__(self, label: str, expanded_fn, parent: QWidget | None = None):
        super().__init__(parent)
        self._label = label
        self._expanded_fn = expanded_fn
        self._hovered = False
        self._callback = None
        self._cog_callback = None
        self._enabled_check = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_callback(self, fn):
        self._callback = fn

    def set_cog_callback(self, fn):
        self._cog_callback = fn

    def set_enabled_check(self, fn):
        self._enabled_check = fn

    def _arrow_rect(self) -> QRect:
        return QRect(self.width() - ARROW_W, 0, ARROW_W, self.height())

    def _cog_rect(self) -> QRect:
        return QRect(0, 0, COG_W, self.height())

    def paintEvent(self, event):  # pylint: disable=unused-argument
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        alpha = 128 if self._hovered else 77
        painter.setBrush(QColor(30, 144, 255, alpha))
        painter.setPen(QPen(QColor("#6ab8ff"), 2))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 4, 4)

        cog_enabled = self._enabled_check() if self._enabled_check else False
        cog_color = QColor("#4CAF50") if cog_enabled else QColor(140, 140, 140)
        painter.setPen(QPen(cog_color))
        cog_font = QFont()
        cog_font.setPointSize(9)
        painter.setFont(cog_font)
        painter.drawText(self._cog_rect(), Qt.AlignmentFlag.AlignCenter, "\u2699")

        painter.setPen(QPen(QColor("#6ab8ff"), 1))
        painter.drawLine(COG_W, 4, COG_W, self.height() - 4)

        painter.setPen(QPen(QColor("white")))
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)
        label_rect = QRect(COG_W, 0, self.width() - COG_W - ARROW_W, self.height())
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, self._label)

        painter.setPen(QPen(QColor("#6ab8ff"), 1))
        painter.drawLine(
            self.width() - ARROW_W, 4, self.width() - ARROW_W, self.height() - 4
        )

        symbol = "\u25b2" if self._expanded_fn() else "\u25bc"
        painter.setPen(QPen(QColor("white")))
        arrow_font = QFont()
        arrow_font.setPointSize(7)
        painter.setFont(arrow_font)
        painter.drawText(self._arrow_rect(), Qt.AlignmentFlag.AlignCenter, symbol)

    def enterEvent(self, event):  # pylint: disable=unused-argument
        self._hovered = True
        self.update()

    def leaveEvent(self, event):  # pylint: disable=unused-argument
        self._hovered = False
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            in_cog = self._cog_rect().contains(event.position().toPoint())
            in_arrow = self._arrow_rect().contains(event.position().toPoint())
            if in_cog:
                if self._cog_callback:
                    self._cog_callback()
            elif in_arrow:
                if self._callback:
                    self._callback()
            elif self._enabled_check is None or not self._enabled_check():
                if self._callback:
                    self._callback()
        super().mousePressEvent(event)


class SmallButton(QWidget):
    """Compact clickable button; does not propagate click to parent widget."""

    def __init__(self, label: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._label = label
        self._hovered = False
        self._callback = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_callback(self, fn):
        self._callback = fn

    def paintEvent(self, event):  # pylint: disable=unused-argument
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._hovered:
            painter.setBrush(QColor(255, 255, 255, 40))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 3, 3)
        painter.setPen(QPen(QColor(160, 200, 255)))
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._label)

    def enterEvent(self, event):  # pylint: disable=unused-argument
        self._hovered = True
        self.update()

    def leaveEvent(self, event):  # pylint: disable=unused-argument
        self._hovered = False
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self._callback:
            self._callback()
        event.accept()


class ToggleSwitch(QWidget):
    def __init__(self, active: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self._active = active
        self.setFixedSize(TOGGLE_W, TOGGLE_H)

    @property
    def active(self) -> bool:
        return self._active

    @active.setter
    def active(self, value: bool):
        self._active = value
        self.update()

    def paintEvent(self, event):  # pylint: disable=unused-argument
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        track_color = QColor("#1E90FF") if self._active else QColor("#555555")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track_color)
        painter.drawRoundedRect(0, 0, TOGGLE_W, TOGGLE_H, TOGGLE_RADIUS, TOGGLE_RADIUS)
        knob_d = TOGGLE_H - 4
        knob_x = TOGGLE_W - knob_d - 2 if self._active else 2
        painter.setBrush(QColor("white"))
        painter.drawEllipse(knob_x, 2, knob_d, knob_d)


class RowButton(QWidget):
    def __init__(self, label: str, active: bool = True, parent: QWidget | None = None):
        super().__init__(parent)
        self._label = label
        self._hovered = False
        self.setFixedHeight(ROW_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle = ToggleSwitch(active, self)
        self._reset_btn = SmallButton("\u21ba", self)

    def set_reset_callback(self, fn):
        self._reset_btn.set_callback(fn)

    @property
    def toggle(self) -> ToggleSwitch:
        return self._toggle

    def resizeEvent(self, event):  # pylint: disable=unused-argument
        self._toggle.move(self.width() - TOGGLE_W - 6, (ROW_HEIGHT - TOGGLE_H) // 2)
        reset_x = self.width() - TOGGLE_W - 6 - RESET_BTN_W - 4
        self._reset_btn.setGeometry(
            reset_x, (ROW_HEIGHT - RESET_BTN_H) // 2, RESET_BTN_W, RESET_BTN_H
        )

    def paintEvent(self, event):  # pylint: disable=unused-argument
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._hovered:
            painter.setBrush(QColor(255, 255, 255, 25))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(self.rect(), 4, 4)
        painter.setPen(QPen(QColor("white")))
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        text_rect = QRect(8, 0, self.width() - TOGGLE_W - RESET_BTN_W - 28, ROW_HEIGHT)
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self._label,
        )

    def enterEvent(self, event):  # pylint: disable=unused-argument
        self._hovered = True
        self.update()

    def leaveEvent(self, event):  # pylint: disable=unused-argument
        self._hovered = False
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle.active = not self.toggle.active
            self.update()
        super().mousePressEvent(event)


class ActionButton(QWidget):
    def __init__(self, label: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.label = label
        self._hovered = False
        self.setFixedHeight(ROW_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._callback = None

    def set_callback(self, fn):
        self._callback = fn

    def paintEvent(self, event):  # pylint: disable=unused-argument
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._hovered:
            painter.setBrush(QColor(255, 255, 255, 25))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(self.rect(), 4, 4)
        painter.setPen(QPen(QColor("white")))
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        painter.drawText(
            self.rect().adjusted(8, 0, -8, 0),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self.label,
        )

    def enterEvent(self, event):  # pylint: disable=unused-argument
        self._hovered = True
        self.update()

    def leaveEvent(self, event):  # pylint: disable=unused-argument
        self._hovered = False
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self._callback:
            self._callback()
        super().mousePressEvent(event)
