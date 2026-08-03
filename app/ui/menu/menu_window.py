"""Main TorMeter menu window implementation."""

from __future__ import annotations

import ctypes
from typing import TYPE_CHECKING

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QColor, QKeyEvent, QMouseEvent, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget

from app.constants import DEBUG, HOTKEY_ID, MOD_CONTROL, MOD_SHIFT, VK_F7, VK_F8, VK_F9
from app.hotkey import HotkeyFilter
from app.observable import ObservableValue
from app.preferences import Preferences

from .constants import ARROW_W, EXCLUDED_FROM_SHOWALL, MENU_BAR_HEIGHT, WINDOW_NAME
from .widgets import ActionButton, MenuButton, RowButton

if TYPE_CHECKING:
    from app.window import OverlayWindow


class TorMeterMenu(QWidget):
    """Compact always-on-top menu that controls visibility of overlay windows."""

    def __init__(self, prefs: Preferences, vis_obs: dict[str, ObservableValue] | None = None):
        super().__init__()
        self._prefs = prefs
        self._vis_obs: dict[str, ObservableValue] = vis_obs or {}
        self._overlays: dict[str, OverlayWindow] = {}
        self._enabled = False
        self._expanded = False
        self._drag_start: QPoint | None = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)

        self._hwnd = int(self.winId())
        self._menu_hotkey_id = HOTKEY_ID + 1
        self._restore_hotkey_id = HOTKEY_ID + 2
        self._quit_hotkey_id = HOTKEY_ID + 3
        ctypes.windll.user32.RegisterHotKey(
            self._hwnd, self._menu_hotkey_id, MOD_CONTROL | MOD_SHIFT, VK_F7
        )
        ctypes.windll.user32.RegisterHotKey(
            self._hwnd, self._restore_hotkey_id, MOD_CONTROL | MOD_SHIFT, VK_F8
        )
        ctypes.windll.user32.RegisterHotKey(
            self._hwnd, self._quit_hotkey_id, MOD_CONTROL | MOD_SHIFT, VK_F9
        )
        self._hotkey_filter = HotkeyFilter(
            {
                self._menu_hotkey_id: self._on_hotkey,
                self._restore_hotkey_id: self._restore_menu,
                self._quit_hotkey_id: self._exit_all,
            }
        )
        QApplication.instance().installNativeEventFilter(self._hotkey_filter)

        self._build_ui()
        self._apply_prefs()
        self.show()

    def register_overlay(self, name: str, window: OverlayWindow):
        self._overlays[name] = window
        if name in self._rows:
            obs = self._vis_obs.get(name)
            if obs is not None:
                self._rows[name].toggle.active = obs.value

                def _make_row_sync(n):
                    def _sync(visible: bool):
                        if n in self._rows:
                            self._rows[n].toggle.active = visible
                            self._rows[n].update()

                    return _sync

                obs.subscribe(_make_row_sync(name))
            else:
                self._rows[name].toggle.active = window.isVisible()

    def _apply_prefs(self):
        wp = self._prefs.get(WINDOW_NAME)
        self.move(wp.x, wp.y)

    def _build_ui(self):
        self._rows: dict[str, RowButton] = {}

        self._toggle_btn = MenuButton("TorMeter", lambda: self._expanded, self)
        self._toggle_btn.set_callback(self._toggle_expand)
        self._toggle_btn.set_enabled_check(lambda: self._enabled)
        self._toggle_btn.set_cog_callback(self._on_hotkey)

        self._dropdown = QWidget(self)
        self._dropdown_layout = QVBoxLayout(self._dropdown)
        self._dropdown_layout.setContentsMargins(4, 4, 4, 4)
        self._dropdown_layout.setSpacing(2)
        self._dropdown.hide()

        def _make_toggle(name: str):
            def _on_toggle(_event=None, *, _name=name):
                obs = self._vis_obs.get(_name)
                if obs is not None:
                    obs.set(not obs.value)
                else:
                    win = self._overlays.get(_name)
                    if win:
                        if win.isVisible():
                            win.hide()
                        else:
                            win.show()
                if _name in self._rows:
                    self._rows[_name].toggle.active = (
                        self._vis_obs[_name].value
                        if _name in self._vis_obs
                        else (
                            self._overlays.get(_name) is not None
                            and self._overlays[_name].isVisible()
                        )
                    )

            return _on_toggle

        def _make_reset(name: str):
            def _on_reset(*, _name=name):
                win = self._overlays.get(_name)
                if win and self._prefs:
                    wp = self._prefs.get(_name)
                    win.move(wp.default_x, wp.default_y)
                    self._prefs.set_position(_name, wp.default_x, wp.default_y)

            return _on_reset

        overlay_names = ["Overlay Master", "Summary", "DPS", "Defense", "Heal"]
        if DEBUG:
            overlay_names.append("Default Overlay")
        for name in overlay_names:
            row = RowButton(name, active=True)
            row.toggle.active = True
            row.mousePressEvent = _make_toggle(name)
            row.set_reset_callback(_make_reset(name))
            self._rows[name] = row
            self._dropdown_layout.addWidget(row)

        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #555;")
        self._dropdown_layout.addWidget(sep)

        for name in ("Combat History", "Charts"):
            row = RowButton(name, active=True)
            row.toggle.active = True
            row.mousePressEvent = _make_toggle(name)
            row.set_reset_callback(_make_reset(name))
            self._rows[name] = row
            self._dropdown_layout.addWidget(row)

        sep_grudges = QWidget()
        sep_grudges.setFixedHeight(1)
        sep_grudges.setStyleSheet("background: #555;")
        self._dropdown_layout.addWidget(sep_grudges)

        grudges_name = "Nihilus' Book of Grudges"
        grudges_row = RowButton(grudges_name, active=True)
        grudges_row.toggle.active = True
        grudges_row.mousePressEvent = _make_toggle(grudges_name)
        grudges_row.set_reset_callback(_make_reset(grudges_name))
        self._rows[grudges_name] = grudges_row
        self._dropdown_layout.addWidget(grudges_row)

        sep2 = QWidget()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet("background: #555;")
        self._dropdown_layout.addWidget(sep2)

        self._showall_btn = ActionButton("Hide All")
        self._showall_btn.set_callback(self._toggle_all)
        self._dropdown_layout.addWidget(self._showall_btn)

        exit_btn = ActionButton("Exit")
        exit_btn.set_callback(self._exit_all)
        self._dropdown_layout.addWidget(exit_btn)

        self._relayout()

    def _relayout(self):
        btn_h = MENU_BAR_HEIGHT + 4
        btn_w = max(160, self._toggle_btn.sizeHint().width() + ARROW_W)
        self._toggle_btn.setGeometry(0, 0, btn_w, btn_h)
        self._toggle_btn.update()

        if self._expanded:
            self._dropdown.setFixedWidth(btn_w)
            self._dropdown.adjustSize()
            drop_h = self._dropdown.sizeHint().height()
            self._dropdown.setGeometry(0, btn_h + 2, btn_w, drop_h)
            self.setFixedSize(btn_w, btn_h + 2 + drop_h)
        else:
            self._dropdown.hide()
            self.setFixedSize(btn_w, btn_h)

    def _toggle_expand(self):
        self._expanded = not self._expanded
        self._dropdown.setVisible(self._expanded)
        self._relayout()

    def _on_hotkey(self):
        self._enabled = not self._enabled
        for win in self._overlays.values():
            win._toggle_click_through()  # pylint: disable=protected-access
        self._toggle_btn.update()

    def _restore_menu(self):
        if self._prefs:
            wp = self._prefs.get(WINDOW_NAME)
            self.move(wp.default_x, wp.default_y)
            self._prefs.set_position(WINDOW_NAME, wp.default_x, wp.default_y)
        self.show()
        self.raise_()
        self.activateWindow()

    def _toggle_all(self):
        visible = [
            n
            for n, w in self._overlays.items()
            if n not in EXCLUDED_FROM_SHOWALL and w.isVisible()
        ]
        hide = len(visible) > 0
        for name in self._overlays:
            if name not in EXCLUDED_FROM_SHOWALL:
                obs = self._vis_obs.get(name)
                if obs is not None:
                    obs.set(not hide)
                else:
                    win = self._overlays[name]
                    if hide:
                        win.hide()
                    else:
                        win.show()
                    if name in self._rows:
                        self._rows[name].toggle.active = not hide
        self._showall_btn.label = "Show All" if hide else "Hide All"
        self._showall_btn.update()

    def _exit_all(self):
        self._flush_vis_to_prefs()
        for obs in self._vis_obs.values():
            obs.dispose()
        for win in self._overlays.values():
            win.detach_visible()
            win.hide()
        QApplication.quit()

    def _flush_vis_to_prefs(self) -> None:
        if not self._prefs:
            return
        for name, obs in self._vis_obs.items():
            self._prefs.set_window_visible(name, obs.value)

    def mousePressEvent(self, event: QMouseEvent):
        if self._enabled and event.button() == Qt.MouseButton.LeftButton:
            if event.position().y() <= MENU_BAR_HEIGHT + 4:
                self._drag_start = (
                    event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_start is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_start)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._drag_start is not None:
            pos = self.frameGeometry().topLeft()
            self._prefs.set_position(WINDOW_NAME, pos.x(), pos.y())
        self._drag_start = None
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        self._flush_vis_to_prefs()
        for obs in self._vis_obs.values():
            obs.dispose()
        for win in self._overlays.values():
            win.detach_visible()
        for hid in (self._menu_hotkey_id, self._restore_hotkey_id, self._quit_hotkey_id):
            ctypes.windll.user32.UnregisterHotKey(self._hwnd, hid)
        QApplication.instance().removeNativeEventFilter(self._hotkey_filter)
        super().closeEvent(event)
        QApplication.quit()

    def paintEvent(self, event):  # pylint: disable=unused-argument
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(20, 20, 30, 200))
        painter.setPen(QPen(QColor("#6ab8ff"), 1))
        painter.drawRoundedRect(self.rect(), 5, 5)
