"""Nihilus' Book of Grudges overlay window."""

from __future__ import annotations

from dataclasses import dataclass
import math

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QColor, QPainter, QPen
from PyQt6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QMenu, QPushButton, QScrollArea, QVBoxLayout, QWidget, QSizePolicy

from app.combat_session import Fight
from app.overlays_shared.player_match import player_stats_matches
from app.window import OverlayWindow

from .store import CharacterGrudgeBook, GrudgesStore


_COLUMN_DEFS: list[tuple[str, str, int]] = [
    ("enemy", "Enemy", 172),
    ("encounters", "Enc", 54),
    ("kills", "Kills", 54),
    ("deaths", "Deaths", 54),
    ("avg_ttk", "Avg TTK", 66),
    ("fastest_ttk", "Fastest", 66),
    ("damage_out", "Dmg Out", 66),
    ("damage_in", "Dmg In", 66),
    ("avg_out", "Avg Out", 66),
    ("avg_in", "Avg In", 66),
    ("kill_rate", "Kill %", 60),
    ("crit_rate", "Crit %", 60),
    ("last_seen", "Last Seen", 78),
]


@dataclass(slots=True)
class _EnemyRowData:
    key: str
    name: str
    encounters: int
    kills: int
    deaths: int
    avg_ttk_ms: float
    fastest_ttk_ms: int
    slowest_ttk_ms: int
    damage_out: int
    damage_in: int
    avg_damage_out: float
    avg_damage_in: float
    kill_rate: float
    crit_rate: float
    last_seen_ms: int


class _EnemyRow(QWidget):
    def __init__(self, data: _EnemyRowData, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(28)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(6)

        self._name = QLabel()
        self._name.setFixedWidth(172)
        self._name.setStyleSheet(
            "color: white; font-size: 10px; font-weight: bold; background: transparent;"
        )
        layout.addWidget(self._name)

        self._enc = self._make_cell("70", 54)
        self._kills = self._make_cell("70", 54)
        self._deaths = self._make_cell("70", 54)
        self._ttk = self._make_cell("00.0s", 66)
        self._fast = self._make_cell("00.0s", 66)
        self._out = self._make_cell("1,000", 66)
        self._in = self._make_cell("1,000", 66)
        self._avg_out = self._make_cell("1,000", 66)
        self._avg_in = self._make_cell("1,000", 66)
        self._rate = self._make_cell("100%", 60)
        self._crit = self._make_cell("100%", 60)
        self._last = self._make_cell("00:00:00", 78)

        for lbl in (
            self._enc,
            self._kills,
            self._deaths,
            self._ttk,
            self._fast,
            self._out,
            self._in,
            self._avg_out,
            self._avg_in,
            self._rate,
            self._crit,
            self._last,
        ):
            layout.addWidget(lbl)

        self.set_data(data)
        self._columns: dict[str, QLabel] = {
            "enemy": self._name,
            "encounters": self._enc,
            "kills": self._kills,
            "deaths": self._deaths,
            "avg_ttk": self._ttk,
            "fastest_ttk": self._fast,
            "damage_out": self._out,
            "damage_in": self._in,
            "avg_out": self._avg_out,
            "avg_in": self._avg_in,
            "kill_rate": self._rate,
            "crit_rate": self._crit,
            "last_seen": self._last,
        }

    def _make_cell(self, placeholder: str, width: int) -> QLabel:
        lbl = QLabel(placeholder)
        lbl.setFixedWidth(width)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(
            "color: rgba(255,255,255,185); font-size: 10px; background: transparent;"
        )
        return lbl

    def set_data(self, data: _EnemyRowData) -> None:
        self._name.setText(data.name)
        self._enc.setText(str(data.encounters))
        self._kills.setText(str(data.kills))
        self._deaths.setText(str(data.deaths))
        self._ttk.setText(_fmt_duration(data.avg_ttk_ms / 1000.0))
        self._fast.setText(_fmt_duration(data.fastest_ttk_ms / 1000.0))
        self._out.setText(_fmt_num(data.damage_out))
        self._in.setText(_fmt_num(data.damage_in))
        self._avg_out.setText(_fmt_avg(data.avg_damage_out))
        self._avg_in.setText(_fmt_avg(data.avg_damage_in))
        self._rate.setText(f"{data.kill_rate:.0%}")
        self._crit.setText(f"{data.crit_rate:.0%}")
        self._last.setText(_fmt_log_time(data.last_seen_ms))

    def set_column_visible(self, key: str, visible: bool) -> None:
        col = self._columns.get(key)
        if col is not None:
            col.setVisible(visible)


class NihilusBookOfGrudgesOverlay(OverlayWindow):
    title = "Nihilus' Book of Grudges"
    window_name = "Nihilus' Book of Grudges"
    _min_content_width = 860

    def __init__(self, prefs=None):
        self._store = GrudgesStore()
        self._my_name: str | None = None
        self._page_size = 10
        self._page_index = 0
        self._rows: list[_EnemyRow] = []
        self._current_book_data: CharacterGrudgeBook | None = None
        self._header_labels: dict[str, QLabel] = {}
        self._column_visible: dict[str, bool] = {
            key: True for key, _, _ in _COLUMN_DEFS
        }
        if prefs is not None:
            pref_cols = getattr(prefs, "nbg_columns_visible", {}) or {}
            if isinstance(pref_cols, dict):
                for key, value in pref_cols.items():
                    if key in self._column_visible:
                        self._column_visible[key] = bool(value)
        # Keep the enemy name column always visible to preserve row identity.
        self._column_visible["enemy"] = True
        self._search_text = ""
        self._sort_mode = "Kills"
        if prefs is not None:
            self._search_text = (getattr(prefs, "nbg_search_text", "") or "").strip().casefold()
            self._sort_mode = (getattr(prefs, "nbg_sort_mode", "Kills") or "Kills").strip() or "Kills"
        super().__init__(prefs)

    def _setup_content(self):
        p = self._prefs
        if p:
            self._min_content_width = p.nbg_win_width
            self._max_content_height = p.nbg_win_height

        self._layout.setSpacing(6)

        self._title_lbl = QLabel(self.title)
        self._title_lbl.setStyleSheet(
            "color: white; font-size: 14px; font-weight: bold; background: transparent;"
        )
        self._title_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._layout.addWidget(self._title_lbl)

        controls = QWidget()
        controls_l = QHBoxLayout(controls)
        controls_l.setContentsMargins(4, 0, 4, 0)
        controls_l.setSpacing(6)

        search_lbl = QLabel("Search:")
        search_lbl.setStyleSheet(
            "color: rgba(255,255,255,180); font-size: 10px; background: transparent;"
        )
        controls_l.addWidget(search_lbl)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("enemy name")
        self._search_edit.setStyleSheet(
            "color: white; background: rgba(255,255,255,18);"
            "border: 1px solid rgba(255,255,255,50); border-radius: 3px;"
            "font-size: 10px; padding: 2px 6px;"
        )
        self._search_edit.textChanged.connect(self._on_search_changed)
        controls_l.addWidget(self._search_edit, 1)

        sort_lbl = QLabel("Sort:")
        sort_lbl.setStyleSheet(
            "color: rgba(255,255,255,180); font-size: 10px; background: transparent;"
        )
        controls_l.addWidget(sort_lbl)

        self._sort_combo = QComboBox()
        self._sort_combo.addItems(
            [
                "Kills",
                "Deaths",
                "Encounters",
                "Avg TTK",
                "Fastest TTK",
                "Damage Out",
                "Damage In",
                "Avg Damage Out",
                "Avg Damage In",
                "Kill %",
                "Crit %",
                "Last Seen",
                "Name",
            ]
        )
        self._sort_combo.setStyleSheet(
            "QComboBox { color: white; background: rgba(255,255,255,18);"
            " border: 1px solid rgba(255,255,255,45); border-radius: 2px;"
            " font-size: 10px; padding: 0 2px; }"
            "QComboBox::drop-down { width: 10px; border: none; }"
            "QComboBox QAbstractItemView { background: rgba(20,20,30,240);"
            " color: white; selection-background-color: rgba(30,144,255,180);"
            " border: 1px solid rgba(255,255,255,60); font-size: 10px; }"
        )
        self._sort_combo.currentTextChanged.connect(self._on_sort_changed)
        controls_l.addWidget(self._sort_combo)

        self._filters_btn = QPushButton("Filters")
        self._filters_btn.setStyleSheet(
            "color: white; background: rgba(255,255,255,24);"
            "border: 1px solid rgba(255,255,255,50); border-radius: 3px;"
            "font-size: 10px; padding: 2px 8px;"
        )
        self._filters_btn.clicked.connect(self._open_filters_menu)
        controls_l.addWidget(self._filters_btn)

        self._search_edit.setText(getattr(self._prefs, "nbg_search_text", "") if self._prefs else "")
        sort_choice = self._sort_mode
        if self._sort_combo.findText(sort_choice) < 0:
            sort_choice = "Kills"
        self._sort_combo.setCurrentText(sort_choice)
        self._sort_mode = sort_choice
        self._layout.addWidget(controls)

        summary_row = QWidget()
        summary_l = QHBoxLayout(summary_row)
        summary_l.setContentsMargins(4, 0, 4, 0)
        summary_l.setSpacing(8)
        self._summary_lbl = QLabel("No grudges recorded yet.")
        self._summary_lbl.setStyleSheet(
            "color: rgba(255,255,255,185); font-size: 10px; background: transparent;"
        )
        self._char_lbl = QLabel("Character: -")
        self._char_lbl.setStyleSheet(
            "color: rgba(255,215,0,190); font-size: 10px; background: transparent;"
        )
        summary_l.addWidget(self._summary_lbl, 1)
        summary_l.addWidget(self._char_lbl)
        self._layout.addWidget(summary_row)

        header = QWidget()
        header_l = QHBoxLayout(header)
        header_l.setContentsMargins(6, 0, 6, 0)
        header_l.setSpacing(6)
        for key, text, width in _COLUMN_DEFS:
            lbl = QLabel(text)
            lbl.setFixedWidth(width)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(
                "color: rgba(255,255,255,180); font-size: 9px; background: transparent;"
            )
            header_l.addWidget(lbl)
            self._header_labels[key] = lbl
        self._layout.addWidget(header)

        self._scroll = QScrollArea()
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self._list_container = QWidget()
        self._list_container.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(2)
        self._scroll.setWidget(self._list_container)
        self._layout.addWidget(self._scroll)

        pager = QWidget()
        pager_l = QHBoxLayout(pager)
        pager_l.setContentsMargins(4, 0, 4, 0)
        pager_l.setSpacing(6)
        self._prev_btn = QPushButton("Prev")
        self._next_btn = QPushButton("Next")
        for btn in (self._prev_btn, self._next_btn):
            btn.setStyleSheet(
                "color: white; background: rgba(255,255,255,24);"
                "border: 1px solid rgba(255,255,255,50); border-radius: 3px;"
                "font-size: 10px; padding: 2px 8px;"
            )
        self._prev_btn.clicked.connect(self._prev_page)
        self._next_btn.clicked.connect(self._next_page)
        self._page_lbl = QLabel("Page 1 / 1")
        self._page_lbl.setStyleSheet(
            "color: rgba(255,255,255,180); font-size: 10px; background: transparent;"
        )
        pager_l.addWidget(self._prev_btn)
        pager_l.addWidget(self._next_btn)
        pager_l.addStretch(1)
        pager_l.addWidget(self._page_lbl)
        self._layout.addWidget(pager)

        if p:
            self.apply_text_size(p.nbg_label_size)
        self._apply_column_visibility()
        self._refresh_from_store()

    def receive_watcher(self, watcher) -> None:
        self._watcher = watcher
        watcher.fight_closed.connect(self._on_fight_closed)
        watcher.session_reset.connect(self._on_session_reset)

    def apply_win_width(self, v: int) -> None:
        self._min_content_width = v
        if self._prefs:
            self._prefs.nbg_win_width = v
        self._resize_to_content()

    def apply_win_height(self, v: int) -> None:
        self._max_content_height = v
        if self._prefs:
            self._prefs.nbg_win_height = v
        self._resize_to_content()

    def apply_win_bg_alpha(self, v: int) -> None:
        if self._prefs:
            self._prefs.nbg_win_bg_alpha = v
        self.update()

    def apply_win_bg_color(self, c: str) -> None:
        if self._prefs:
            self._prefs.nbg_win_bg_color = c
        self.update()

    def apply_text_size(self, v: int) -> None:
        if self._prefs:
            self._prefs.nbg_label_size = v
        title_pt = max(8, v + 3)
        self._title_lbl.setStyleSheet(
            f"color: white; font-size: {title_pt}px; font-weight: bold; background: transparent;"
        )
        self._summary_lbl.setStyleSheet(
            f"color: rgba(255,255,255,185); font-size: {v}px; background: transparent;"
        )
        self._char_lbl.setStyleSheet(
            f"color: rgba(255,215,0,190); font-size: {v}px; background: transparent;"
        )
        for row in self._rows:
            row._name.setStyleSheet(
                f"color: white; font-size: {v}px; font-weight: bold; background: transparent;"
            )
            for cell in (
                row._enc,
                row._kills,
                row._deaths,
                row._ttk,
                row._fast,
                row._out,
                row._in,
                row._avg_out,
                row._avg_in,
                row._rate,
                row._crit,
                row._last,
            ):
                cell.setStyleSheet(
                    f"color: rgba(255,255,255,185); font-size: {v}px; background: transparent;"
                )
        self._resize_to_content()

    def apply_character_name(self, name: str) -> None:
        self._my_name = (name or "").strip() or None
        self._page_index = 0
        self._refresh_from_store()

    def _current_character_name(self) -> str | None:
        candidate = self._my_name or (self._prefs.character_name if self._prefs else "")
        candidate = (candidate or "").strip()
        if not candidate or candidate.casefold() == "me":
            return None
        return candidate

    def _on_fight_closed(self, fight: Fight) -> None:
        character_name = self._current_character_name()
        if character_name is None:
            return
        if self._store.record_fight(character_name, fight):
            self._refresh_from_store()

    def _on_session_reset(self) -> None:
        self._refresh_from_store()

    def _clear_rows(self) -> None:
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self._rows.clear()

    def _refresh_from_store(self) -> None:
        self._clear_rows()

        character_name = self._current_character_name()
        if character_name is None:
            self._current_book_data = None
            self._summary_lbl.setText("Set a valid character name to start tracking grudges.")
            self._char_lbl.setText("Character: -")
            self._page_lbl.setText("Page 1 / 1")
            self._prev_btn.setEnabled(False)
            self._next_btn.setEnabled(False)
            self._resize_to_content()
            return

        book = self._store.snapshot(character_name)
        self._current_book_data = book
        if book is None or not book.enemies:
            self._summary_lbl.setText("No grudges recorded yet.")
            self._char_lbl.setText(f"Character: {character_name}")
            self._page_lbl.setText("Page 1 / 1")
            self._prev_btn.setEnabled(False)
            self._next_btn.setEnabled(False)
            self._resize_to_content()
            return

        records = self._sorted_records(book)
        total_pages = max(1, (len(records) + self._page_size - 1) // self._page_size)
        self._page_index = min(self._page_index, total_pages - 1)
        start = self._page_index * self._page_size
        end = start + self._page_size
        page_records = records[start:end]

        self._summary_lbl.setText(
            f"{len(book.enemies)} enemies tracked | {book.fights} fights | {book.kills} kills"
        )
        self._char_lbl.setText(f"Character: {book.character_name}")
        self._page_lbl.setText(f"Page {self._page_index + 1} / {total_pages}")
        self._prev_btn.setEnabled(self._page_index > 0)
        self._next_btn.setEnabled(self._page_index < total_pages - 1)

        for rec in page_records:
            row = _EnemyRow(rec)
            for key, visible in self._column_visible.items():
                row.set_column_visible(key, visible)
            self._rows.append(row)
            self._list_layout.addWidget(row)

        self._list_layout.addStretch(1)
        self._resize_to_content()

    def _sorted_records(self, book: CharacterGrudgeBook) -> list[_EnemyRowData]:
        records = [
            _EnemyRowData(
                key=record.key,
                name=record.name,
                encounters=record.encounters,
                kills=record.kills,
                deaths=record.deaths,
                avg_ttk_ms=record.avg_ttk_ms,
                fastest_ttk_ms=record.fastest_ttk_ms,
                slowest_ttk_ms=record.slowest_ttk_ms,
                damage_out=record.damage_out,
                damage_in=record.damage_in,
                avg_damage_out=record.avg_damage_out,
                avg_damage_in=record.avg_damage_in,
                kill_rate=record.kill_rate,
                crit_rate=record.crit_rate,
                last_seen_ms=record.last_seen_ms,
            )
            for record in book.enemies.values()
            if not self._search_text or self._search_text in record.name.casefold()
        ]
        records.sort(key=self._sort_key)
        return records

    def _sort_key(self, record: _EnemyRowData):
        if self._sort_mode == "Deaths":
            return (-record.deaths, -record.kills, -record.encounters, record.name.casefold())
        if self._sort_mode == "Encounters":
            return (-record.encounters, -record.kills, -record.last_seen_ms, record.name.casefold())
        if self._sort_mode == "Avg TTK":
            return (-record.avg_ttk_ms, -record.kills, record.name.casefold())
        if self._sort_mode == "Fastest TTK":
            return (record.fastest_ttk_ms or 10**12, -record.kills, record.name.casefold())
        if self._sort_mode == "Damage Out":
            return (-record.damage_out, -record.kills, record.name.casefold())
        if self._sort_mode == "Damage In":
            return (-record.damage_in, -record.kills, record.name.casefold())
        if self._sort_mode == "Avg Damage Out":
            return (-record.avg_damage_out, -record.kills, record.name.casefold())
        if self._sort_mode == "Avg Damage In":
            return (-record.avg_damage_in, -record.kills, record.name.casefold())
        if self._sort_mode == "Kill %":
            return (-record.kill_rate, -record.kills, record.name.casefold())
        if self._sort_mode == "Crit %":
            return (-record.crit_rate, -record.kills, record.name.casefold())
        if self._sort_mode == "Last Seen":
            return (-record.last_seen_ms, -record.kills, record.name.casefold())
        if self._sort_mode == "Name":
            return (record.name.casefold(), -record.kills, -record.encounters, record.name.casefold())
        return (-record.kills, -record.encounters, -record.last_seen_ms, record.name.casefold())

    def _on_search_changed(self, text: str) -> None:
        self._search_text = (text or "").strip().casefold()
        if self._prefs:
            self._prefs.nbg_search_text = (text or "").strip()
            self._prefs.save()
        self._page_index = 0
        self._refresh_from_store()

    def _on_sort_changed(self, text: str) -> None:
        self._sort_mode = text or "Kills"
        if self._prefs:
            self._prefs.nbg_sort_mode = self._sort_mode
            self._prefs.save()
        self._page_index = 0
        self._refresh_from_store()

    def _open_filters_menu(self) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: rgba(20,20,30,240); color: white;"
            " border: 1px solid rgba(255,255,255,60); }"
            "QMenu::item { padding: 4px 14px 4px 8px; }"
            "QMenu::item:selected { background: rgba(30,144,255,160); }"
        )
        for key, text, _ in _COLUMN_DEFS:
            if key == "enemy":
                continue
            action = QAction(text, menu)
            action.setCheckable(True)
            action.setChecked(self._column_visible.get(key, True))
            action.toggled.connect(
                lambda checked, column_key=key: self._on_column_filter_toggled(column_key, checked)
            )
            menu.addAction(action)
        menu.popup(self._filters_btn.mapToGlobal(self._filters_btn.rect().bottomLeft()))

    def _on_column_filter_toggled(self, key: str, visible: bool) -> None:
        self._column_visible[key] = visible
        if self._prefs:
            self._prefs.nbg_columns_visible = dict(self._column_visible)
            self._prefs.save()
        self._apply_column_visibility()

    def _apply_column_visibility(self) -> None:
        for key, lbl in self._header_labels.items():
            lbl.setVisible(self._column_visible.get(key, True))
        for row in self._rows:
            for key, visible in self._column_visible.items():
                row.set_column_visible(key, visible)
        self._resize_to_content()

    def _prev_page(self) -> None:
        if self._page_index > 0:
            self._page_index -= 1
            self._refresh_from_store()

    def _next_page(self) -> None:
        book = self._current_book_data
        if book is None:
            return
        records = self._sorted_records(book)
        total_pages = max(1, (len(records) + self._page_size - 1) // self._page_size)
        if self._page_index < total_pages - 1:
            self._page_index += 1
            self._refresh_from_store()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        p = self._prefs
        alpha = getattr(p, "nbg_win_bg_alpha", 0) if p else 0
        if alpha > 0:
            c = QColor(getattr(p, "nbg_win_bg_color", "#000000") if p else "#000000")
            c.setAlpha(max(0, min(255, alpha)))
        else:
            c = QColor(20, 20, 30, 200)
        painter.setBrush(c)
        painter.setPen(QPen(QColor("#6ab8ff"), 1))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 5, 5)
        super().paintEvent(event)


def _fmt_num(value: float) -> str:
    if value < 100_000:
        return f"{value:,}"
    if value < 1_000_000:
        return f"{value / 1_000:.1f}K"
    if value < 1_000_000_000:
        return f"{value / 1_000_000:.1f}M"
    return f"{value / 1_000_000_000:.1f}B"


def _fmt_avg(value: float) -> str:
    if value <= 0:
        return "0.00"
    truncated = math.trunc(value * 100) / 100
    return f"{truncated:,.2f}"


def _fmt_duration(value_s: float) -> str:
    if value_s <= 0:
        return "—"
    if value_s < 10:
        return f"{value_s:.1f}s"
    return f"{value_s:.0f}s"


def _fmt_log_time(timestamp_ms: int) -> str:
    if timestamp_ms <= 0:
        return "—"
    total_seconds = max(0, timestamp_ms // 1000)
    hours = (total_seconds // 3600) % 24
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
