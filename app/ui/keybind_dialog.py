# ◢▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧◣
# ▧ - Lunar Edge Games                                          ▧
# ▧ - Tor Meter                                                 ▧
# ▧▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▧
# ▧ - Module: App                                               ▧
# ▧ - Sub-Module: UI                                            ▧
# ▧ - Component: Keybind Capture Dialog                         ▧
# ◥▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧◤

"""Modal dialog used to capture a new global hotkey combination."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QLineEdit, QVBoxLayout, QWidget

from app.keybinds import combo_to_string, qt_event_to_combo


class KeybindCaptureDialog(QDialog):
    """Prompts the user to press a new key combination, then accept or cancel."""

    def __init__(self, current_combo: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Set Keybind")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setModal(True)
        self._combo_str = current_combo

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Press the new key combination..."))

        self._display = QLineEdit(current_combo)
        self._display.setReadOnly(True)
        self._display.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._display)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def combo_string(self) -> str:
        """The captured combination text (or the original, if nothing was captured)."""
        return self._combo_str

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # Ensure key presses land on the dialog (not a child widget) so capture works reliably.
        self.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            return
        combo = qt_event_to_combo(event)
        if combo is not None:
            self._combo_str = combo_to_string(*combo)
            self._display.setText(self._combo_str)
        # Deliberately do not call super(): prevents Enter/Return from acting as
        # an implicit "accept" so the user must explicitly click OK or Cancel.
