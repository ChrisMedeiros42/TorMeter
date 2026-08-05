"""Main Combat History overlay window."""

from __future__ import annotations

import re

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.combat_session import CombatSession, Fight
from app.log_watcher import LogWatcher
from app.overlays_shared.player_match import player_name_matches, player_stats_matches
from app.overlays_shared.widgets import _ComboArrowNav, _LocalPlayerFooter, _PlayerFilterButton, _Separator
from app.session_loader import SessionLoader
from app.window import OverlayWindow

from .constants import _COMBO_STYLE, _LABEL_STYLE, _SCOPE_LIVE
from .rows import _AutoScrollArea, _FightRow, _SessionRow

class CombatHistoryOverlay(OverlayWindow):
    title = "Combat History"
    window_name = "Combat History"
    _min_content_width = 340

    def _init_resize_debounce(self) -> None:
        # Coalesce resize bursts caused by rapid fight/session UI updates.
        self._resize_debounce_timer = QTimer(self)
        self._resize_debounce_timer.setSingleShot(True)
        self._resize_debounce_timer.setInterval(120)
        self._resize_debounce_timer.timeout.connect(self._resize_to_content)

    def _request_resize_to_content(self) -> None:
        timer = getattr(self, "_resize_debounce_timer", None)
        if timer is None:
            self._resize_to_content()
            return
        timer.start()

    def _setup_content(self):
        p = self._prefs
        self._session: CombatSession | None = None
        self._my_name: str | None = None
        self._display_player: str | None = None  # player shown in fight/session rows
        self._selected_fight: Fight | None = None
        self._fight_rows: list[_FightRow] = []
        self._session_loader: SessionLoader | None = None
        self._viewing_live = True  # False when a previous session is selected
        self._live_fight_row: _FightRow | None = None  # row for in-progress fight
        self._me_bg_color = (p.coh_me_bg_color if p else "#1E90FF33")

        # Apply saved width/height from prefs
        if p:
            self._min_content_width = p.coh_win_width
            self._max_content_height = p.coh_win_height

        # ── session selector combobox ───────────────────────────────────────────
        sel_row = QWidget()
        sel_row.setStyleSheet("background: transparent;")
        sel_l = QHBoxLayout(sel_row)
        sel_l.setContentsMargins(4, 2, 4, 2)
        sel_l.setSpacing(4)
        sel_lbl = QLabel("Session:")
        sel_lbl.setStyleSheet(_LABEL_STYLE)
        self._sel_lbl = sel_lbl
        sel_l.addWidget(sel_lbl)
        self._session_combo = QComboBox()
        self._session_combo.setStyleSheet(_COMBO_STYLE)
        self._session_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToContents
        )
        self._session_combo.addItem(_SCOPE_LIVE)
        self._session_combo.currentIndexChanged.connect(self._on_session_combo_changed)
        sel_l.addWidget(self._session_combo)
        sel_l.addWidget(_ComboArrowNav(self._session_combo))
        sel_l.addStretch(1)
        self._layout.addWidget(sel_row)

        # ── player selector combobox ────────────────────────────────────────
        player_row = QWidget()
        player_row.setStyleSheet("background: transparent;")
        player_l = QHBoxLayout(player_row)
        player_l.setContentsMargins(4, 2, 4, 2)
        player_l.setSpacing(4)
        player_lbl = QLabel("Player:")
        player_lbl.setStyleSheet(_LABEL_STYLE)
        self._player_sel_lbl = player_lbl
        player_l.addWidget(player_lbl)
        self._player_combo = QComboBox()
        self._player_combo.setStyleSheet(_COMBO_STYLE)
        self._player_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToContents
        )
        self._player_combo.currentIndexChanged.connect(self._on_player_combo_changed)
        player_l.addWidget(self._player_combo)
        player_l.addWidget(_ComboArrowNav(self._player_combo))
        player_l.addStretch(1)
        self._layout.addWidget(player_row)

        # ── column header ───────────────────────────────────────────────────
        hdr_row = QWidget()
        hdr_row.setStyleSheet("background: transparent;")
        hdr_l = QHBoxLayout(hdr_row)
        hdr_l.setContentsMargins(14, 0, 4, 0)
        hdr_l.setSpacing(4)
        hdr_fight_lbl = QLabel("Fight", styleSheet=_LABEL_STYLE)
        self._hdr_fight_lbl = hdr_fight_lbl
        hdr_l.addWidget(hdr_fight_lbl)
        hdr_l.addStretch(1)
        self._hdr_stat_labels: list[QLabel] = []
        for text, color in (
            ("DPS", "#FF8C00"),
            ("DTPS", "#4169E1"),
            ("HPS", "#32CD32"),
            ("Crit", "#FFD700"),
        ):
            lbl = QLabel(text)
            lbl.setStyleSheet(
                f"color: {color}; font-size: 7px; background: transparent;"
            )
            lbl.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            lbl.setFixedWidth(40)
            hdr_l.addWidget(lbl)
            self._hdr_stat_labels.append(lbl)
        self._layout.addWidget(hdr_row)

        # ── session row ──────────────────────────────────────────────────────
        empty_session = CombatSession()
        self._session_row = _SessionRow(empty_session, None)
        self._layout.addWidget(self._session_row)

        self._layout.addWidget(_Separator())

        # ── scrollable fight list ────────────────────────────────────────────
        self._list_widget = QWidget()
        self._list_widget.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(2)
        self._list_layout.addStretch(1)

        self._scroll = _AutoScrollArea()
        if p:
            self._scroll.MAX_H = p.coh_list_height
        self._scroll.setMinimumHeight(min(self._scroll.MAX_H, 260))
        self._scroll.setWidget(self._list_widget)
        self._layout.addWidget(self._scroll)

        # ── footer ───────────────────────────────────────────────────────────
        self._filter_btn = _PlayerFilterButton()
        self._filter_btn.filter_changed.connect(self._on_filter_changed)
        self._footer = _LocalPlayerFooter(
            show_dps=True,
            show_hps=True,
            show_dtps=True,
            show_crit=True,
            value_size=(p.coh_footer_value_size if p else 9),
            filter_widget=self._filter_btn,
        )
        self._layout.addWidget(self._footer)

        # Apply saved font sizes from prefs
        if p:
            self.apply_name_size(p.coh_name_size)
            self.apply_stat_size(p.coh_stat_size)
            self.apply_text_size(p.coh_label_size)
        self._init_resize_debounce()

    # ── apply_* API (called by OverlayMasterWindow) ───────────────────────────

    def apply_win_width(self, v: int) -> None:
        self._min_content_width = v
        if self._prefs:
            self._prefs.coh_win_width = v
        self._resize_to_content()

    def apply_win_height(self, v: int) -> None:
        self._max_content_height = v
        if self._prefs:
            self._prefs.coh_win_height = v
        self._resize_to_content()

    def apply_win_bg_alpha(self, v: int) -> None:
        if self._prefs:
            self._prefs.coh_win_bg_alpha = v
        self.update()

    def apply_win_bg_color(self, c: str) -> None:
        if self._prefs:
            self._prefs.coh_win_bg_color = c
        self.update()

    def apply_name_size(self, v: int) -> None:
        if self._prefs:
            self._prefs.coh_name_size = v
        self._session_row.set_name_size(v)
        for row in self._fight_rows:
            row.set_name_size(v)
        if self._live_fight_row is not None:
            self._live_fight_row.set_name_size(v)

    def apply_name_color(self, c: str) -> None:
        if self._prefs:
            self._prefs.coh_name_color = c

    def apply_stat_size(self, v: int) -> None:
        if self._prefs:
            self._prefs.coh_stat_size = v
        self._session_row.set_stat_size(v)
        for row in self._fight_rows:
            row.set_stat_size(v)
        if self._live_fight_row is not None:
            self._live_fight_row.set_stat_size(v)
        for lbl in self._hdr_stat_labels:
            lbl.setStyleSheet(
                re.sub(r"font-size:\s*\d+px", f"font-size: {v}px", lbl.styleSheet())
            )

    def apply_me_bg_color(self, c: str) -> None:
        if self._prefs:
            self._prefs.coh_me_bg_color = c
        self._me_bg_color = c
        for row in self._fight_rows:
            row.set_me_bg_color(c)
        if self._live_fight_row is not None:
            self._live_fight_row.set_me_bg_color(c)

    def apply_footer_value_size(self, v: int) -> None:
        self._footer.set_value_size(v)
        if self._prefs:
            self._prefs.coh_footer_value_size = v

    def apply_list_height(self, v: int) -> None:
        self._scroll.MAX_H = v
        self._scroll.setMinimumHeight(min(v, 260))
        if self._prefs:
            self._prefs.coh_list_height = v
        self._scroll.updateGeometry()
        self._resize_to_content()

    def apply_text_size(self, v: int) -> None:
        if self._prefs:
            self._prefs.coh_label_size = v
        style = re.sub(r"font-size:\s*\d+px", f"font-size: {v}px", _LABEL_STYLE)
        self._sel_lbl.setStyleSheet(style)
        self._player_sel_lbl.setStyleSheet(style)
        self._hdr_fight_lbl.setStyleSheet(style)
        combo_style = re.sub(r"font-size:\s*\d+px", f"font-size: {v}px", _COMBO_STYLE)
        self._session_combo.setStyleSheet(combo_style)
        self._player_combo.setStyleSheet(combo_style)
        for lbl in self._hdr_stat_labels:
            lbl.setStyleSheet(
                re.sub(r"font-size:\s*\d+px", f"font-size: {v}px", lbl.styleSheet())
            )

    def apply_character_name(self, name: str) -> None:
        self._my_name = (name or "").strip() or None

        # In live mode, sync the player combo to the configured character name.
        if self._viewing_live and self._my_name:
            idx = next(
                (
                    i
                    for i in range(self._player_combo.count())
                    if player_name_matches(self._my_name, self._player_combo.itemText(i))
                ),
                -1,
            )
            if idx >= 0:
                # setCurrentIndex triggers _on_player_combo_changed which
                # updates _display_player and refreshes all rows.
                self._player_combo.setCurrentIndex(idx)
            else:
                # Player not in combo yet (no fights yet); update directly.
                self._display_player = self._my_name
                for row in self._fight_rows:
                    row.set_my_name(self._display_player)
                if self._live_fight_row is not None:
                    self._live_fight_row.set_my_name(self._display_player)
                self._rebuild_session_row()

        # Footer always shows the local player's stats for the selected fight.
        if self._selected_fight is not None and self._my_name is not None:
            stats = next(
                (
                    s
                    for s in self._selected_fight.player_stats.values()
                    if player_stats_matches(self._my_name, s)
                ),
                None,
            )
            self._footer.update_stats(stats, self._selected_fight.duration_s)
        else:
            self._footer.update_stats(None, 1.0)

        self._request_resize_to_content()

    # ── watcher API ──────────────────────────────────────────────────────────

    def receive_watcher(self, watcher: LogWatcher) -> None:
        self._watcher = watcher
        watcher.fight_opened.connect(self._on_fight_opened)
        watcher.fight_closed.connect(self._on_fight_closed)
        watcher.session_reset.connect(self._on_session_reset)
        watcher.fight_updated.connect(self._on_live_fight_updated)

    def receive_session_loader(self, loader: SessionLoader) -> None:
        self._session_loader = loader
        loader.sessions_changed.connect(self._rebuild_session_combo)

    def _on_fight_opened(self, fight: Fight) -> None:
        p = self._prefs
        self._my_name = (p.character_name if p and p.character_name else "") or None
        if not self._viewing_live:
            return
        self._remove_live_fight_row()
        # Collapse all existing rows silently before highlighting the new fight.
        for existing in self._fight_rows:
            existing.collapse(notify=False)
        self._selected_fight = None
        row = _FightRow(
            fight,
            self._display_player,
            on_select=self._on_fight_selected,
            me_bg_color=self._me_bg_color,
        )
        row.update_filter(self._filter_btn.hidden_players)
        if p:
            row.set_name_size(p.coh_name_size)
            row.set_stat_size(p.coh_stat_size)
        # Insert at the top so the current fight is always first.
        self._list_layout.insertWidget(0, row)
        row.expand()
        self._live_fight_row = row
        QTimer.singleShot(0, lambda: self._scroll.verticalScrollBar().setValue(0))
        self._request_resize_to_content()

    def _remove_live_fight_row(self) -> None:
        if self._live_fight_row is not None:
            self._live_fight_row.setParent(None)
            self._live_fight_row.deleteLater()
            self._live_fight_row = None

    def _on_fight_closed(self, fight: Fight) -> None:
        p = self._prefs
        self._my_name = (p.character_name if p and p.character_name else "") or None
        self._session = self._watcher.session
        # Remove the live row — the permanent row is added below
        self._remove_live_fight_row()

        # Only update the displayed list if we're watching the live session
        if not self._viewing_live:
            return

        # Rebuild player combo first so _display_player is current.
        self._rebuild_player_combo(self._session)

        # Collapse all existing rows silently before showing the finished fight.
        for existing in self._fight_rows:
            existing.collapse(notify=False)
        self._selected_fight = None

        row = _FightRow(
            fight,
            self._display_player,
            on_select=self._on_fight_selected,
            me_bg_color=self._me_bg_color,
        )
        row.update_filter(self._filter_btn.hidden_players)
        if p:
            row.set_name_size(p.coh_name_size)
            row.set_stat_size(p.coh_stat_size)
        # Insert at the top so the most recent fight is always first.
        self._list_layout.insertWidget(0, row)
        row.expand()
        self._fight_rows.insert(0, row)

        # Update filter player list
        self._update_filter_players()
        # Rebuild session row
        self._rebuild_session_row()
        QTimer.singleShot(0, lambda: self._scroll.verticalScrollBar().setValue(0))
        self._request_resize_to_content()

    def _on_live_fight_updated(self, fight: Fight) -> None:
        """Update footer and live fight row with current-fight stats."""
        if self._viewing_live and self._live_fight_row is not None:
            self._live_fight_row.update_live(fight)
        if self._selected_fight is None:
            p = self._prefs
            my_name = (
                (p.character_name if p and p.character_name else "") if p else None
            )
            if my_name:
                stats = next(
                    (s for s in fight.player_stats.values() if player_stats_matches(my_name, s)),
                    None,
                )
                self._footer.update_stats(stats, fight.duration_s)

    def _on_session_reset(self) -> None:
        self._remove_live_fight_row()
        self._rebuild_session_combo()  # live file changed → refresh prev sessions list
        if not self._viewing_live:
            return
        for row in list(self._fight_rows):
            row.setParent(None)
            row.deleteLater()
        self._fight_rows.clear()
        self._filter_btn.set_players([])
        # Clear player combo; it will repopulate as new fights come in.
        self._player_combo.blockSignals(True)
        self._player_combo.clear()
        self._display_player = self._my_name  # keep targeting local player
        self._player_combo.blockSignals(False)
        self._rebuild_session_row()
        self._footer.update_stats(None, 1.0)
        self._selected_fight = None
        self._request_resize_to_content()

    def _on_fight_selected(self, fight: Fight | None) -> None:
        """Called when a fight row is clicked; update footer for that fight."""
        self._selected_fight = fight
        p = self._prefs
        my_name = (p.character_name if p and p.character_name else "") if p else None
        if fight is None or my_name is None:
            self._footer.update_stats(None, 1.0)
        else:
            stats = next(
                (s for s in fight.player_stats.values() if player_stats_matches(my_name, s)),
                None,
            )
            self._footer.update_stats(stats, fight.duration_s)

    def _rebuild_session_row(self) -> None:
        session = (
            self._watcher.session if hasattr(self, "_watcher") else CombatSession()
        )
        new_row = _SessionRow(session, self._display_player)
        p = self._prefs
        if p:
            new_row.set_name_size(p.coh_name_size)
            new_row.set_stat_size(p.coh_stat_size)
        # Replace old row in layout
        idx = self._layout.indexOf(self._session_row)
        if idx >= 0:
            self._layout.removeWidget(self._session_row)
            self._session_row.deleteLater()
            self._layout.insertWidget(idx, new_row)
        self._session_row = new_row

    def _rebuild_session_combo(self) -> None:
        """Refresh the session selector combo with available historical sessions."""
        current = self._session_combo.currentText()
        self._session_combo.blockSignals(True)
        self._session_combo.clear()
        self._session_combo.addItem(_SCOPE_LIVE)
        if self._session_loader:
            for entry in self._session_loader.entries:
                self._session_combo.addItem(entry.label)
        idx = self._session_combo.findText(current)
        self._session_combo.setCurrentIndex(max(idx, 0))
        self._session_combo.blockSignals(False)

    def _on_session_combo_changed(self) -> None:
        """Called when the user picks a different session from the selector."""
        label = self._session_combo.currentText()
        if label == _SCOPE_LIVE:
            self._viewing_live = True
            self._load_session_into_list(
                self._watcher.session if hasattr(self, "_watcher") else CombatSession()
            )
        elif self._session_loader:
            for entry in self._session_loader.entries:
                if entry.label == label:
                    self._viewing_live = False
                    self._load_session_into_list(entry.session)
                    return

    def _load_session_into_list(self, session: CombatSession) -> None:
        """Replace the fight list with fights from the given session."""
        for row in list(self._fight_rows):
            row.setParent(None)
            row.deleteLater()
        self._fight_rows.clear()
        self._selected_fight = None
        self._footer.update_stats(None, 1.0)

        p = self._prefs
        # Populate the player combo from this session and determine _display_player.
        self._rebuild_player_combo(session)

        # Insert fights so the most recent appears at the top.
        # Each fight is inserted at position 0, so the last fight ends up first.
        for fight in session.fights:
            row = _FightRow(
                fight,
                self._display_player,
                on_select=self._on_fight_selected,
                me_bg_color=self._me_bg_color,
            )
            if p:
                row.set_name_size(p.coh_name_size)
                row.set_stat_size(p.coh_stat_size)
            self._list_layout.insertWidget(0, row)
            self._fight_rows.insert(0, row)

        # Update session summary row and filter
        new_row = _SessionRow(session, self._display_player)
        if p:
            new_row.set_name_size(p.coh_name_size)
            new_row.set_stat_size(p.coh_stat_size)
        idx = self._layout.indexOf(self._session_row)
        if idx >= 0:
            self._layout.removeWidget(self._session_row)
            self._session_row.deleteLater()
            self._layout.insertWidget(idx, new_row)
        self._session_row = new_row

        names: list[str] = []
        for aid in session.all_player_ids():
            agg = session.aggregate_player_stats(aid)
            if agg is not None:
                names.append(agg.name)
        self._filter_btn.set_players(names)
        hidden = self._filter_btn.hidden_players
        for row in self._fight_rows:
            row.update_filter(hidden)

        self._request_resize_to_content()

    def _rebuild_player_combo(self, session: CombatSession) -> None:
        """Rebuild the player selector combo with all players from the session."""
        names: list[str] = []
        for aid in session.all_player_ids():
            agg = session.aggregate_player_stats(aid)
            if agg is not None:
                names.append(agg.name)
        names.sort()

        self._player_combo.blockSignals(True)
        prev_text = self._player_combo.currentText()
        self._player_combo.clear()
        for name in names:
            self._player_combo.addItem(name)

        # Selection priority: previously selected player > local character name > first item.
        target = prev_text or self._my_name
        if target:
            idx = next(
                (
                    i
                    for i in range(self._player_combo.count())
                    if player_name_matches(target, self._player_combo.itemText(i))
                ),
                -1,
            )
            if idx >= 0:
                self._player_combo.setCurrentIndex(idx)
            elif self._player_combo.count() > 0:
                self._player_combo.setCurrentIndex(0)
        elif self._player_combo.count() > 0:
            self._player_combo.setCurrentIndex(0)

        self._display_player = self._player_combo.currentText() or None
        self._player_combo.blockSignals(False)

    def _on_player_combo_changed(self) -> None:
        """Called when the user picks a different player from the selector."""
        self._display_player = self._player_combo.currentText() or None
        for row in self._fight_rows:
            row.set_my_name(self._display_player)
        if self._live_fight_row is not None:
            self._live_fight_row.set_my_name(self._display_player)
        self._rebuild_session_row()
        self._request_resize_to_content()

    def _update_filter_players(self) -> None:
        """Sync the filter button's player list with the current session."""
        session = (
            self._watcher.session if hasattr(self, "_watcher") else CombatSession()
        )
        names: list[str] = []
        for aid in session.all_player_ids():
            agg = session.aggregate_player_stats(aid)
            if agg is not None:
                names.append(agg.name)
        self._filter_btn.set_players(names)

    def _on_filter_changed(self) -> None:
        """Apply updated filter to all fight rows."""
        hidden = self._filter_btn.hidden_players
        for row in self._fight_rows:
            row.update_filter(hidden)
        self._request_resize_to_content()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        p = self._prefs
        alpha = getattr(p, "coh_win_bg_alpha", 0) if p else 0
        if alpha > 0:
            c = QColor(getattr(p, "coh_win_bg_color", "#000000") if p else "#000000")
            c.setAlpha(max(0, min(255, alpha)))
        else:
            c = QColor(20, 20, 30, 200)
        painter.setBrush(c)
        painter.setPen(QPen(QColor("#6ab8ff"), 1))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 5, 5)
        super().paintEvent(event)

