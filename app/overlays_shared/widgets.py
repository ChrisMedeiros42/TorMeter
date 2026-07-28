"""Shared overlay widgets reused across multiple overlay windows."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from app.combat_session import PlayerFightStats
from app.constants import fmt_num

class _Separator(QWidget):
    """A 1 px horizontal separator line."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(1)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event):  # pylint: disable=unused-argument
        painter = QPainter(self)
        painter.setPen(QPen(QColor(255, 255, 255, 60), 1))
        y = self.height() // 2
        painter.drawLine(0, y, self.width(), y)


# ── local-player stat footer ──────────────────────────────────────────────────
_PILL_STYLE = (
    "color: {color}; font-size: {size}px; background: rgba(255,255,255,15);"
    " border-radius: 3px; padding: 1px 4px;"
)


def _footer_label_style(size: int) -> str:
    return (
        "color: rgba(255,255,255,120); "
        f"font-size: {size}px; background: transparent;"
    )


class _StatPill(QLabel):
    """Small colored label showing one stat value."""

    def __init__(self, color: str, size: int = 9, parent: QWidget | None = None):
        super().__init__("—", parent)
        self._color = color
        self._size = size
        self.setStyleSheet(_PILL_STYLE.format(color=color, size=size))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_value(self, text: str) -> None:
        self.setText(text)

    def set_value_size(self, size: int) -> None:
        self._size = size
        self.setStyleSheet(_PILL_STYLE.format(color=self._color, size=size))


class _ComboArrowNav(QWidget):
    """◀ / ▶ buttons that step a QComboBox through its items."""

    _BTN_STYLE = (
        "QPushButton { color: rgba(255,255,255,180); background: rgba(255,255,255,15);"
        " border: 1px solid rgba(255,255,255,50); border-radius: 3px;"
        " font-size: 9px; padding: 0 2px; }"
        "QPushButton:hover { background: rgba(255,255,255,35); }"
        "QPushButton:pressed { background: rgba(255,255,255,55); }"
        "QPushButton:disabled { color: rgba(255,255,255,40);"
        " background: rgba(255,255,255,8); border-color: rgba(255,255,255,20); }"
    )

    def __init__(self, combo: QComboBox, parent: QWidget | None = None):
        super().__init__(parent)
        self._combo = combo
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        self._prev = QPushButton("◀")
        self._prev.setFixedSize(16, 14)
        self._prev.setStyleSheet(self._BTN_STYLE)
        self._prev.clicked.connect(self._go_prev)
        self._next = QPushButton("▶")
        self._next.setFixedSize(16, 14)
        self._next.setStyleSheet(self._BTN_STYLE)
        self._next.clicked.connect(self._go_next)
        lay.addWidget(self._prev)
        lay.addWidget(self._next)
        combo.currentIndexChanged.connect(self._update_state)
        combo.model().rowsInserted.connect(self._update_state)
        combo.model().rowsRemoved.connect(self._update_state)
        self._update_state()

    def _go_prev(self) -> None:
        idx = self._combo.currentIndex()
        if idx > 0:
            self._combo.setCurrentIndex(idx - 1)

    def _go_next(self) -> None:
        idx = self._combo.currentIndex()
        if idx < self._combo.count() - 1:
            self._combo.setCurrentIndex(idx + 1)

    def _update_state(self, *_) -> None:
        idx = self._combo.currentIndex()
        n = self._combo.count()
        self._prev.setEnabled(idx > 0)
        self._next.setEnabled(idx < n - 1)


class _PlayerFilterButton(QWidget):
    """Filter button that toggles an inline player-toggle panel."""

    filter_changed = pyqtSignal()

    _BTN_STYLE = (
        "QPushButton { color: rgba(255,255,255,180); background: rgba(255,255,255,15);"
        " border: 1px solid rgba(255,255,255,50); border-radius: 3px;"
        " font-size: 9px; padding: 0 3px; }"
        "QPushButton:hover { background: rgba(255,255,255,35); }"
        "QPushButton:pressed { background: rgba(255,255,255,55); }"
    )
    _CB_STYLE = (
        "QCheckBox { color: rgba(255,255,255,200); font-size: 8pt;"
        " background: transparent; spacing: 4px; }"
        "QCheckBox::indicator { width: 10px; height: 10px;"
        " border: 1px solid rgba(255,255,255,80); border-radius: 2px;"
        " background: rgba(255,255,255,15); }"
        "QCheckBox::indicator:checked { background: rgba(30,144,255,200);"
        " border-color: rgba(30,144,255,255); }"
    )

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._hidden: set[str] = set()
        self._players: list[str] = []
        self._checkboxes: dict[str, QCheckBox] = {}
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._vbox = QVBoxLayout(self)
        self._vbox.setContentsMargins(0, 0, 0, 0)
        self._vbox.setSpacing(2)

        self._btn = QPushButton("≡ Filter")
        self._btn.setFixedHeight(14)
        self._btn.setStyleSheet(self._BTN_STYLE)
        self._btn.setToolTip("Toggle player filter")
        self._btn.clicked.connect(self._toggle_panel)
        self._vbox.addWidget(self._btn)

        self._panel = QWidget()
        self._panel.setStyleSheet(
            "QWidget { background: rgba(255,255,255,8); border-radius: 3px; }"
        )
        self._panel_layout = QVBoxLayout(self._panel)
        self._panel_layout.setContentsMargins(6, 2, 6, 2)
        self._panel_layout.setSpacing(1)
        self._panel.setVisible(False)
        self._vbox.addWidget(self._panel)

    @property
    def hidden_players(self) -> set[str]:
        return self._hidden

    def set_players(self, names: list[str]) -> None:
        """Update the available player list; discard hidden names that no longer exist."""
        self._players = list(names)
        self._hidden &= set(names)
        self._rebuild_panel()

    def _rebuild_panel(self) -> None:
        while self._panel_layout.count():
            item = self._panel_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._checkboxes.clear()
        for name in self._players:
            cb = QCheckBox(name)
            cb.setChecked(name not in self._hidden)
            cb.setStyleSheet(self._CB_STYLE)
            cb.toggled.connect(lambda checked, n=name: self._on_toggle(n, checked))
            self._panel_layout.addWidget(cb)
            self._checkboxes[name] = cb

    def _on_toggle(self, name: str, checked: bool) -> None:
        if checked:
            self._hidden.discard(name)
        else:
            self._hidden.add(name)
        self.filter_changed.emit()

    def _toggle_panel(self) -> None:
        self._panel.setVisible(not self._panel.isVisible())
        # Walk parent chain to trigger overlay resize
        p = self.parent()
        while p is not None:
            if hasattr(p, "_resize_to_content"):
                p._resize_to_content()  # type: ignore[attr-defined]
                break
            p = p.parent()


class _LocalPlayerFooter(QWidget):
    """Separator + one row of stat pills for the local player's current fight.

    Displayed stats (depends on overlay context):
      DPS, HPS, DTPS, Crit%
    The caller selects which to show via the `show_*` flags at construction.
    """

    def __init__(
        self,
        show_dps: bool = True,
        show_hps: bool = False,
        show_dtps: bool = True,
        show_crit: bool = True,
        value_size: int = 9,
        filter_widget: QWidget | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet("background: transparent;")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 2, 0, 0)
        outer.setSpacing(2)
        outer.addWidget(_Separator())

        row = QWidget()
        row.setStyleSheet("background: transparent;")
        row_l = QHBoxLayout(row)
        row_l.setContentsMargins(4, 0, 4, 2)
        row_l.setSpacing(4)

        me_lbl = QLabel("me:")
        me_lbl.setStyleSheet(_footer_label_style(value_size))
        self._labels: list[QLabel] = [me_lbl]
        row_l.addWidget(me_lbl)

        self._pills: dict[str, _StatPill] = {}

        if show_dps:
            lbl = QLabel("DPS")
            lbl.setStyleSheet(_footer_label_style(value_size))
            self._labels.append(lbl)
            row_l.addWidget(lbl)
            self._pills["dps"] = _StatPill("#FF8C00", value_size)
            row_l.addWidget(self._pills["dps"])

        if show_dtps:
            lbl = QLabel("DTPS")
            lbl.setStyleSheet(_footer_label_style(value_size))
            self._labels.append(lbl)
            row_l.addWidget(lbl)
            self._pills["dtps"] = _StatPill("#4169E1", value_size)
            row_l.addWidget(self._pills["dtps"])

        if show_hps:
            lbl = QLabel("HPS")
            lbl.setStyleSheet(_footer_label_style(value_size))
            self._labels.append(lbl)
            row_l.addWidget(lbl)
            self._pills["hps"] = _StatPill("#32CD32", value_size)
            row_l.addWidget(self._pills["hps"])

        if show_crit:
            lbl = QLabel("Crit")
            lbl.setStyleSheet(_footer_label_style(value_size))
            self._labels.append(lbl)
            row_l.addWidget(lbl)
            self._pills["crit"] = _StatPill("#FFD700", value_size)
            row_l.addWidget(self._pills["crit"])

        row_l.addStretch(1)
        if filter_widget is not None:
            row_l.addWidget(filter_widget)
        outer.addWidget(row)

    def update_stats(self, stats: PlayerFightStats | None, duration_s: float) -> None:
        """Refresh all pills from a PlayerFightStats snapshot."""
        if stats is None:
            for pill in self._pills.values():
                pill.set_value("—")
            return
        if "dps" in self._pills:
            self._pills["dps"].set_value(fmt_num(stats.dps(duration_s)))
        if "dtps" in self._pills:
            self._pills["dtps"].set_value(fmt_num(stats.dtps(duration_s)))
        if "hps" in self._pills:
            self._pills["hps"].set_value(fmt_num(stats.hps(duration_s)))
        if "crit" in self._pills:
            self._pills["crit"].set_value(f"{stats.crit_rate:.0%}")

    def set_value_size(self, size: int) -> None:
        for lbl in self._labels:
            lbl.setStyleSheet(_footer_label_style(size))
        for pill in self._pills.values():
            pill.set_value_size(size)


# ── shared player-list base ───────────────────────────────────────────────────



