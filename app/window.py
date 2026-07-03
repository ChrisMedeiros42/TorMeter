# ◢▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧◣
# ▧ - Lunar Edge Games                                        ▧
# ▧ - Tor Meter                                               ▧
# ▧▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▧
# ▧ - Module: Main                                            ▧
# ▧ - Component: Window                                       ▧
# ◥▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧◤

import ctypes

from PyQt6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, QPoint, QRect, QSize, QTimer
from PyQt6.QtGui import QFont, QKeyEvent, QMouseEvent, QPainter, QColor, QPen

from app.constants import (
    GWL_EXSTYLE,
    WS_EX_LAYERED,
    WS_EX_TRANSPARENT,
)
from app.observable import ObservableValue
from app.preferences import Preferences

MENU_BAR_HEIGHT = 16
MENU_BAR_SIDE_PADDING = 1  # left and right padding
BORDER_WIDTH = 2  # half the pen width (pen is 3px, inset by 2 to stay inside)
CLOSE_BTN_SIZE = 8  # square hit area for the X button
CLOSE_BTN_MARGIN = 4  # gap between X and the right border
CONTENT_PADDING = 4  # padding around child content (left, right, bottom)
INITIAL_WIDTH_EXTRA = 50  # extra starting width beyond content


class OverlayWindow(QWidget):
    title: str = "Overlay"
    window_name: str = "Default Overlay"

    # Subclasses may override to enforce a minimum content width (px)
    _min_content_width: int = 0
    # Subclasses may set to cap the content height (0 = unlimited)
    _max_content_height: int = 0

    def __init__(self, prefs: Preferences | None = None):
        super().__init__()
        self._prefs = prefs
        self._click_through = True
        self._drag_start: QPoint | None = None
        self._vis_obs: ObservableValue | None = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # hides from taskbar
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(0.75)  # semi-transparent

        # Content widget sits below the menu bar with padding on left, right, bottom
        # Offset by BORDER_WIDTH so content clears the 3px green border
        _content_offset = BORDER_WIDTH + CONTENT_PADDING
        self._content = QWidget(self)
        self._content.move(_content_offset, MENU_BAR_HEIGHT)
        self._layout = QVBoxLayout(self._content)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(4)
        self._layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinimumSize)

        self._setup_content()

        # Size the window to fit content + padding, with the initial extra width
        self._content.adjustSize()  # force layout calculation before reading size
        content_size: QSize = self._content.sizeHint()
        content_w = max(
            content_size.width(), INITIAL_WIDTH_EXTRA, self._min_content_width
        )
        _content_offset = BORDER_WIDTH + CONTENT_PADDING
        w = content_w + _content_offset * 2
        h = MENU_BAR_HEIGHT + content_size.height() + _content_offset
        self.setFixedSize(w, h)

        # Explicitly size the content widget to fill the padded area
        self._content.setFixedSize(content_w, content_size.height())
        self._content.setStyleSheet(
            "background: transparent;"
        )  # enables proper child clipping

        self.show()
        self._hwnd = int(self.winId())
        self._set_click_through(True)

        # Apply saved position from preferences
        if self._prefs is not None:
            wp = self._prefs.get(self.window_name)
            self.move(wp.x, wp.y)

    def _setup_content(self):
        """
        Override in subclasses to populate self._layout with child widgets.
        """
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

        label = QLabel("Overlay Text", self._content)
        label.setStyleSheet("color: white; font-size: 18px;")
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._layout.addWidget(label)

    def bind_visible(self, obs: ObservableValue) -> None:
        """
        Attach an ObservableValue[bool] as the single source of truth for visibility.

        The window will show/hide whenever *obs* changes, and will push its own
        show/hide events back into *obs* so all subscribers stay in sync.
        """
        self._vis_obs = obs
        # Drive window from observable
        obs.subscribe(lambda visible: self.show() if visible else self.hide())
        # Sync to observable's current value immediately
        if obs.value:
            self.show()
        else:
            self.hide()

    def detach_visible(self) -> None:
        """
        Disconnect from the visibility observable (call before app teardown).
        """
        self._vis_obs = None

    def set_visibility_change_callback(self, fn):
        """
        Legacy shim — subscribes *fn* to the bound observable if present.
        """
        if self._vis_obs is not None and fn is not None:
            self._vis_obs.subscribe(fn)

    def add_visibility_change_callback(self, fn):
        """
        Legacy shim — subscribes *fn* to the bound observable if present.
        """
        if self._vis_obs is not None and fn is not None:
            self._vis_obs.subscribe(fn)

    def _set_click_through(self, enabled: bool):
        style = ctypes.windll.user32.GetWindowLongW(self._hwnd, GWL_EXSTYLE)
        if enabled:
            new_style = style | WS_EX_LAYERED | WS_EX_TRANSPARENT
        else:
            new_style = (style | WS_EX_LAYERED) & ~WS_EX_TRANSPARENT
        ctypes.windll.user32.SetWindowLongW(self._hwnd, GWL_EXSTYLE, new_style)
        self._click_through = enabled

    def _toggle_click_through(self):
        """
        Ctrl+Shift+F7: disable click-through and focus window; press again to restore.
        """
        if self._click_through:
            self._set_click_through(False)
            self.activateWindow()
            self.raise_()
        else:
            self._set_click_through(True)
        self.update()  # trigger repaint to show/hide border

    def _resize_to_content(self):
        """
        Recalculate and apply window size from current content layout hints.
        """

        def _do():
            lay = self._content.layout()
            if lay:
                lay.invalidate()
                lay.activate()
            hint = self._content.sizeHint()
            cw = max(hint.width(), self._min_content_width)
            ch = hint.height()
            if self._max_content_height > 0:
                ch = min(ch, self._max_content_height)
            co = BORDER_WIDTH + CONTENT_PADDING
            self._content.setFixedSize(cw, ch)
            self.setFixedSize(cw + co * 2, MENU_BAR_HEIGHT + ch + co)

        QTimer.singleShot(0, _do)

    def _close_btn_rect(self) -> QRect:
        x = self.width() - BORDER_WIDTH - CLOSE_BTN_MARGIN - CLOSE_BTN_SIZE
        bar_top = BORDER_WIDTH + MENU_BAR_SIDE_PADDING
        bar_height = MENU_BAR_HEIGHT - BORDER_WIDTH
        y = bar_top + (bar_height - CLOSE_BTN_SIZE) // 2
        return QRect(x, y, CLOSE_BTN_SIZE, CLOSE_BTN_SIZE)

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._click_through:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Green border around the whole window (drawn first, underneath menu bar)
            border_pen = QPen(QColor("#90EE90"))
            border_pen.setWidth(3)
            painter.setPen(border_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 4, 4)

            # Blue menu bar inset inside the border, with rounded top corners only
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#1E90FF"))
            bar_rect = QRect(
                BORDER_WIDTH + MENU_BAR_SIDE_PADDING,
                BORDER_WIDTH + MENU_BAR_SIDE_PADDING,
                self.width() - BORDER_WIDTH * 2 - MENU_BAR_SIDE_PADDING * 2,
                MENU_BAR_HEIGHT - BORDER_WIDTH,
            )
            # Draw rounded rect then cover the bottom corners to make only top corners rounded
            painter.drawRoundedRect(bar_rect, 3, 3)
            bottom_fix_h = 4
            painter.drawRect(
                bar_rect.x(),
                bar_rect.bottom() - bottom_fix_h + 1,
                bar_rect.width(),
                bottom_fix_h,
            )

            # Title text in the menu bar
            title_font = QFont()
            title_font.setPointSize(8)
            painter.setFont(title_font)
            title_pen = QPen(QColor("white"))
            painter.setPen(title_pen)
            title_x = BORDER_WIDTH + MENU_BAR_SIDE_PADDING + CLOSE_BTN_MARGIN
            bar_top = BORDER_WIDTH + MENU_BAR_SIDE_PADDING
            bar_height = MENU_BAR_HEIGHT - BORDER_WIDTH
            title_rect = QRect(
                title_x,
                bar_top,
                self._close_btn_rect().x() - title_x - CLOSE_BTN_MARGIN,
                bar_height,
            )
            painter.drawText(
                title_rect,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                self.title,
            )

            # X close button
            btn = self._close_btn_rect()
            x_pen = QPen(QColor("white"))
            x_pen.setWidth(2)
            x_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(x_pen)
            painter.drawLine(btn.topLeft(), btn.bottomRight())
            painter.drawLine(btn.topRight(), btn.bottomLeft())

    def mousePressEvent(self, event: QMouseEvent):
        if not self._click_through and event.button() == Qt.MouseButton.LeftButton:
            if self._close_btn_rect().contains(event.position().toPoint()):
                self.close()
                return
            if event.position().y() <= MENU_BAR_HEIGHT:
                self._drag_start = (
                    event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_start is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_start)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._drag_start is not None and self._prefs is not None:
            pos = self.frameGeometry().topLeft()
            self._prefs.set_position(self.window_name, pos.x(), pos.y())
        self._drag_start = None
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        event.ignore()
        if self._vis_obs is not None:
            self._vis_obs.set(False)  # notifies all subscribers (menu row, OM checkbox)
        else:
            self.hide()

    def hideEvent(self, event):
        super().hideEvent(event)
        if self._vis_obs is not None:
            self._vis_obs.set(False)

    def showEvent(self, event):
        super().showEvent(event)
        if self._vis_obs is not None:
            self._vis_obs.set(True)
        QTimer.singleShot(0, self.update)
