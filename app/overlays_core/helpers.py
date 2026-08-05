"""Helper widgets and layout utilities for overlay configuration UIs."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QRect, QSize, QTimer
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QMouseEvent, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

_EDIT_STYLE = (
    "color: white; background: rgba(255,255,255,20);"
    "border: 1px solid rgba(255,255,255,60);"
    "border-radius: 3px; font-size: 9px;"
)
_LABEL_STYLE = "color: white; font-size: 9px; background: transparent;"
_SLIDER_STYLE = (
    "QSlider::groove:horizontal {"
    "  background: rgba(255,255,255,40); height: 4px; border-radius: 2px; }"
    "QSlider::sub-page:horizontal {"
    "  background: #1E90FF; border-radius: 2px; }"
    "QSlider::handle:horizontal {"
    "  background: #1E90FF; border: 1px solid #6ab8ff;"
    "  width: 10px; height: 10px; border-radius: 5px; margin: -3px 0; }"
    "QSlider::handle:horizontal:disabled {"
    "  background: #555; border: 1px solid #777; }"
)
_CHECK_STYLE = (
    "QCheckBox::indicator { width: 12px; height: 12px; border-radius: 2px;"
    "  border: 1px solid rgba(255,255,255,120); background: rgba(255,255,255,20); }"
    "QCheckBox::indicator:checked { background: #1E90FF; border: 1px solid #6ab8ff; }"
)

_COL_CHECK = 16
_COL_LABEL = 52
_COL_EDIT = 34
_COL_COLOR = 16

class _RotatedLabel(QWidget):
    """Fixed-width column with a solid background and 90° CCW rotated text.
    When inner widget is provided, clicking collapses/expands it.
    While collapsed the label switches to a horizontal bar with normal text."""

    _STRIP = 26  # px — narrow dimension in both orientations

    def __init__(
        self,
        text: str,
        bg_color: "str | QColor",
        inner: "QWidget | None" = None,
        on_collapse_change: "callable | None" = None,
        parent: "QWidget | None" = None,
    ):
        super().__init__(parent)
        self._text = text
        self._bg = QColor(bg_color) if isinstance(bg_color, str) else bg_color
        self._inner = inner
        self._on_collapse_change = on_collapse_change
        self._collapsed = False
        self._apply_orientation()
        if inner is not None:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _apply_orientation(self):
        """Swap between narrow-vertical (expanded) and wide-horizontal (collapsed)."""
        if self._collapsed:
            # Horizontal bar: fixed height, expand width
            self.setMinimumWidth(0)
            self.setMaximumWidth(16_777_215)
            self.setFixedHeight(self._STRIP)
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        else:
            # Vertical strip: fixed width, expand height
            self.setMinimumHeight(0)
            self.setMaximumHeight(16_777_215)
            self.setFixedWidth(self._STRIP)
            self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

    def sizeHint(self) -> QSize:
        if self._collapsed:
            return QSize(120, self._STRIP)
        return QSize(self._STRIP, 60)

    def mousePressEvent(self, event: QMouseEvent):
        if self._inner is not None and event.button() == Qt.MouseButton.LeftButton:
            self._collapsed = not self._collapsed
            self._inner.setVisible(not self._collapsed)
            self._apply_orientation()
            self.update()
            if self._on_collapse_change:
                QTimer.singleShot(0, self._on_collapse_change)
        super().mousePressEvent(event)

    def paintEvent(self, event):  # pylint: disable=unused-argument
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), self._bg)

        font = QFont()
        font.setPointSize(8)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("white"))

        if self._collapsed:
            # Horizontal layout: ▶ on the left, text centred in remaining space
            ind_font = QFont()
            ind_font.setPointSize(7)
            painter.setFont(ind_font)
            painter.drawText(
                QRect(4, 0, 14, self._STRIP),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                "▶",
            )
            painter.setFont(font)
            painter.drawText(
                QRect(18, 0, self.width() - 22, self._STRIP),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                self._text,
            )
        else:
            if self._inner is not None:
                # Collapse indicator at top (▼ = expanded)
                ind_font = QFont()
                ind_font.setPointSize(6)
                painter.setFont(ind_font)
                painter.drawText(
                    QRect(0, 2, self.width(), 12),
                    Qt.AlignmentFlag.AlignHCenter,
                    "▼",
                )
            # Rotated text centred on the strip
            painter.setFont(font)
            painter.save()
            painter.translate(self.width() / 2.0, self.height() / 2.0)
            painter.rotate(-90)
            fm = painter.fontMetrics()
            w = fm.horizontalAdvance(self._text)
            painter.drawText(-w // 2, fm.descent(), self._text)
            painter.restore()


# ── bordered section frame ───────────────────────────────────────────────────
class _SectionFrame(QWidget):
    """Rounded bordered frame used for each SUM/DPS/DEF/HEAL section."""

    def paintEvent(self, event):  # pylint: disable=unused-argument
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(255, 255, 255, 10))
        painter.setPen(QPen(QColor(255, 255, 255, 60), 1))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 5, 5)


# ── capped scroll area ──────────────────────────────────────────────────────
class _AutoScrollArea(QScrollArea):
    """Scroll area that grows up to MAX_H then scrolls; transparent dark styling."""

    MAX_H = 500

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setWidgetResizable(True)
        self.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical {"
            "  background: rgba(255,255,255,15); width: 6px; border-radius: 3px;"
            "  margin: 0; }"
            "QScrollBar::handle:vertical {"
            "  background: rgba(255,255,255,70); border-radius: 3px;"
            "  min-height: 20px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {"
            "  height: 0; }"
        )

    def sizeHint(self) -> QSize:
        w = self.widget()
        if w is None:
            return super().sizeHint()
        inner = w.sizeHint()
        sb_w = self.verticalScrollBar().sizeHint().width()
        if inner.height() > self.MAX_H:
            return QSize(inner.width() + sb_w, self.MAX_H)
        return QSize(inner.width(), inner.height())


# ── color picker button ──────────────────────────────────────────────────────
class _ColorButton(QWidget):
    """Small square that shows the chosen color and opens QColorDialog on click."""

    def __init__(self, color: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._color = QColor(color)
        self._callback = None
        self.setFixedSize(_COL_COLOR, _COL_COLOR)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Pick color")

    def set_callback(self, fn):
        self._callback = fn

    def set_color(self, color: str):
        self._color = QColor(color)
        self.update()

    def paintEvent(self, event):  # pylint: disable=unused-argument
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(self._color)
        painter.setPen(QPen(QColor(255, 255, 255, 100), 1))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 2, 2)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            dlg = QColorDialog(self._color, self.window())
            dlg.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
            dlg.setOption(QColorDialog.ColorDialogOption.ShowAlphaChannel, True)
            if dlg.exec():
                chosen = dlg.currentColor()
                if chosen.isValid():
                    self._color = chosen
                    self.update()
                    if self._callback:
                        self._callback(chosen.name(QColor.NameFormat.HexArgb))
        event.accept()


# ── outline label ───────────────────────────────────────────────────────────
class _OutlineLabel(QLabel):
    """QLabel that can render its text with a QPainterPath stroke outline."""

    def __init__(self, text: str = "", parent: "QWidget | None" = None) -> None:
        super().__init__(text, parent)
        self._outline_show: bool = False
        self._outline_size: int = 1
        self._outline_qcolor: QColor = QColor("black")
        self._fill_qcolor: QColor = QColor("white")
        self._bg_qcolor: QColor = QColor(0, 0, 0, 0)

    def set_fill_color(self, c: str) -> None:
        self._fill_qcolor = QColor(c)
        self.update()

    def set_bg_color(self, c: str) -> None:
        self._bg_qcolor = QColor(0, 0, 0, 0) if c == "transparent" else QColor(c)
        self.update()

    def set_outline(self, show: bool, size: int, color: QColor) -> None:
        self._outline_show = show
        self._outline_size = size
        self._outline_qcolor = color
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        if not self._outline_show or self._outline_size <= 0:
            super().paintEvent(event)
            return
        text = self.text()
        if not text:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._bg_qcolor.alpha() > 0:
            painter.fillRect(self.rect(), self._bg_qcolor)
        font = self.font()
        fm = QFontMetrics(font)
        r = self.contentsRect()
        br = fm.boundingRect(r, int(self.alignment()), text)
        path = QPainterPath()
        path.addText(br.x(), br.y() + fm.ascent(), font, text)
        pen = QPen(self._outline_qcolor, self._outline_size * 2)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._fill_qcolor)
        painter.drawPath(path)


# ── grid row builder ─────────────────────────────────────────────────────────
def _add_grid_row(
    grid: QGridLayout,
    row_idx: int,
    has_checkbox: bool,
    label_text: str,
    init_value: int = 0,
    init_show: bool = True,
    init_color: str = "#FFFFFF",
    has_size: bool = True,
    has_color: bool = True,
    value_range: tuple = (4, 24),
    on_value_change=None,
    on_show_change=None,
    on_color_change=None,
):
    """Add one row to a QGridLayout. Columns: 0=checkbox, 1=label, 2=slider, 3=textbox, 4=color."""
    checkbox = None
    if has_checkbox:
        checkbox = QCheckBox()
        checkbox.setChecked(init_show)
        checkbox.setStyleSheet(_CHECK_STYLE)
        grid.addWidget(checkbox, row_idx, 0, Qt.AlignmentFlag.AlignVCenter)

    lbl = QLabel(label_text)
    lbl.setStyleSheet(_LABEL_STYLE)
    lbl.setEnabled(init_show)
    if not has_checkbox:
        col_span = 2 if has_size else 5
        grid.addWidget(lbl, row_idx, 0, 1, col_span)
    else:
        if has_size:
            grid.addWidget(lbl, row_idx, 1)
        else:
            grid.addWidget(lbl, row_idx, 1, 1, 4)

    slider = None
    textbox = None
    if has_size:
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(*value_range)
        slider.setValue(max(value_range[0], min(value_range[1], init_value)))
        slider.setStyleSheet(_SLIDER_STYLE)
        slider.setEnabled(init_show)
        grid.addWidget(slider, row_idx, 2)

        textbox = QLineEdit(str(init_value))
        textbox.setFixedWidth(_COL_EDIT)
        textbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        textbox.setStyleSheet(_EDIT_STYLE)
        textbox.setEnabled(init_show)
        grid.addWidget(textbox, row_idx, 3)

    if has_color:
        color_btn = _ColorButton(init_color)
        if on_color_change:
            color_btn.set_callback(on_color_change)
        grid.addWidget(color_btn, row_idx, 4, Qt.AlignmentFlag.AlignVCenter)

    if has_size:
        # Two-way sync
        def _on_slider(val: int):
            textbox.setText(str(val))
            if on_value_change:
                on_value_change(val)

        def _on_text():
            try:
                v = max(value_range[0], min(value_range[1], int(textbox.text())))
                slider.setValue(v)
            except ValueError:
                textbox.setText(str(slider.value()))

        slider.valueChanged.connect(_on_slider)
        textbox.editingFinished.connect(_on_text)

    if checkbox:

        def _on_check(state: int):
            enabled = bool(state)
            lbl.setEnabled(enabled)
            if slider:
                slider.setEnabled(enabled)
            if textbox:
                textbox.setEnabled(enabled)
            if on_show_change:
                on_show_change(enabled)

        checkbox.stateChanged.connect(_on_check)


def _make_section_inner() -> tuple[QWidget, QGridLayout]:
    """Create an inner QWidget with a QGridLayout using fixed equal columns."""
    inner = QWidget()
    inner.setStyleSheet("background: transparent;")
    grid = QGridLayout(inner)
    grid.setContentsMargins(4, 4, 4, 4)
    grid.setHorizontalSpacing(4)
    grid.setVerticalSpacing(3)
    grid.setColumnMinimumWidth(0, _COL_CHECK)
    grid.setColumnMinimumWidth(1, _COL_LABEL)
    grid.setColumnStretch(2, 1)
    grid.setColumnMinimumWidth(3, _COL_EDIT)
    grid.setColumnMinimumWidth(4, _COL_COLOR)
    return inner, grid


def _make_show_hide_wrapper(
    inner: QWidget,
    init_visible: bool,
    on_change=None,
) -> "tuple[QWidget, QCheckBox]":
    """Wrap *inner* with a Show / Hide checkbox row.  Returns (wrapper, checkbox)."""
    wrapper = QWidget()
    wrapper.setStyleSheet("background: transparent;")
    vbox = QVBoxLayout(wrapper)
    vbox.setContentsMargins(0, 0, 0, 0)
    vbox.setSpacing(0)

    header = QWidget()
    header.setStyleSheet("background: transparent;")
    hbox = QHBoxLayout(header)
    hbox.setContentsMargins(4, 2, 4, 2)
    hbox.setSpacing(6)
    cb = QCheckBox()
    cb.setChecked(init_visible)
    cb.setStyleSheet(_CHECK_STYLE)
    hbox.addWidget(cb)
    lbl = QLabel("Show / Hide")
    lbl.setStyleSheet(_LABEL_STYLE)
    hbox.addWidget(lbl)
    hbox.addStretch()
    if on_change:
        cb.stateChanged.connect(lambda state: on_change(bool(state)))

    vbox.addWidget(header)
    vbox.addWidget(inner)
    return wrapper, cb


def _section(
    label_text: str,
    bg_color: str,
    inner: QWidget,
    on_collapse_change: "callable | None" = None,
) -> _SectionFrame:
    frame = _SectionFrame()
    frame_l = QHBoxLayout(frame)
    frame_l.setContentsMargins(4, 4, 4, 4)
    frame_l.setSpacing(4)
    frame_l.addWidget(
        _RotatedLabel(
            label_text,
            bg_color,
            inner=inner,
            on_collapse_change=on_collapse_change,
            parent=frame,
        )
    )
    frame_l.addWidget(inner, 1)
    return frame


# ── overlay windows ──────────────────────────────────────────────────────────

