"""Main Charts overlay window."""

from __future__ import annotations

import re

from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QWidget

from app.combat_session import CombatSession, Fight, PlayerFightStats
from app.log_parser import APPLY_EFFECT, DAMAGE, HEAL, PLAYER
from app.log_watcher import LogWatcher
from app.overlays_shared.player_match import player_name_matches, player_stats_matches
from app.overlays_shared.widgets import _ComboArrowNav, _LocalPlayerFooter, _PlayerFilterButton
from app.session_loader import SessionLoader
from app.window import OverlayWindow

from .chart_widget import _ChartWidget
from .constants import (
    _CHART_TYPES,
    _COMBO_STYLE,
    _FIGHT_ALL,
    _LABEL_STYLE,
    _SCOPE_LIVE,
    _SCOPE_SESSION,
    _STAT_LABELS,
)
from .stats import _get_stat

class ChartsOverlay(OverlayWindow):
    title = "Charts"
    window_name = "Charts"
    _min_content_width = 300

    def _setup_content(self):
        p = self._prefs
        self._watcher: LogWatcher | None = None
        self._session_loader: SessionLoader | None = None
        self._my_name: str | None = None
        self._live_fight: Fight | None = None

        # Apply saved width/height from prefs
        if p:
            self._min_content_width = p.cht_win_width
            self._max_content_height = p.cht_win_height

        # ── Controls row ─────────────────────────────────────────────────────
        ctrl_row = QWidget()
        ctrl_row.setStyleSheet("background: transparent;")
        ctrl_l = QHBoxLayout(ctrl_row)
        ctrl_l.setContentsMargins(2, 2, 2, 2)
        ctrl_l.setSpacing(6)

        scope_lbl = QLabel("Scope:")
        scope_lbl.setStyleSheet(_LABEL_STYLE)
        self._scope_lbl = scope_lbl
        ctrl_l.addWidget(scope_lbl)

        self._scope_combo = QComboBox()
        self._scope_combo.setStyleSheet(_COMBO_STYLE)
        self._scope_combo.addItems([_SCOPE_SESSION, _SCOPE_LIVE])
        self._scope_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToContents
        )
        self._scope_combo.currentTextChanged.connect(self._on_scope_changed)
        ctrl_l.addWidget(self._scope_combo)
        ctrl_l.addWidget(_ComboArrowNav(self._scope_combo))

        ctrl_l.addSpacing(8)

        stat_lbl = QLabel("Stat:")
        stat_lbl.setStyleSheet(_LABEL_STYLE)
        self._stat_lbl = stat_lbl
        ctrl_l.addWidget(stat_lbl)

        self._stat_combo = QComboBox()
        self._stat_combo.setStyleSheet(_COMBO_STYLE)
        self._stat_combo.addItems(_STAT_LABELS)
        self._stat_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToContents
        )
        self._stat_combo.currentTextChanged.connect(self._refresh_chart)
        ctrl_l.addWidget(self._stat_combo)

        ctrl_l.addSpacing(8)

        chart_lbl = QLabel("Chart:")
        chart_lbl.setStyleSheet(_LABEL_STYLE)
        self._chart_lbl = chart_lbl
        ctrl_l.addWidget(chart_lbl)

        self._chart_type_combo = QComboBox()
        self._chart_type_combo.setStyleSheet(_COMBO_STYLE)
        self._chart_type_combo.addItems(_CHART_TYPES)
        self._chart_type_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToContents
        )
        self._chart_type_combo.currentTextChanged.connect(self._on_chart_type_changed)
        ctrl_l.addWidget(self._chart_type_combo)
        ctrl_l.addStretch(1)

        self._layout.addWidget(ctrl_row)

        # ── Fight selector row (Line chart only) ──────────────────────────────
        self._fight_row = QWidget()
        self._fight_row.setStyleSheet("background: transparent;")
        fight_l = QHBoxLayout(self._fight_row)
        fight_l.setContentsMargins(2, 0, 2, 2)
        fight_l.setSpacing(6)
        fight_lbl = QLabel("Fight:")
        fight_lbl.setStyleSheet(_LABEL_STYLE)
        self._fight_lbl = fight_lbl
        fight_l.addWidget(fight_lbl)
        self._fight_combo = QComboBox()
        self._fight_combo.setStyleSheet(_COMBO_STYLE)
        self._fight_combo.addItem(_FIGHT_ALL)
        self._fight_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToContents
        )
        self._fight_combo.currentTextChanged.connect(self._refresh_chart)
        fight_l.addWidget(self._fight_combo)
        fight_l.addWidget(_ComboArrowNav(self._fight_combo))
        fight_l.addStretch(1)
        self._fight_row.setVisible(True)
        self._layout.addWidget(self._fight_row)

        # ── Chart ────────────────────────────────────────────────────────────
        self._chart = _ChartWidget()
        if p:
            self._chart.set_name_size(p.cht_name_size)
            self._chart.set_val_size(p.cht_val_size)
            self._chart.set_me_color(QColor(p.cht_me_color))
            self._chart.set_other_color(QColor(p.cht_other_color))
            self._chart.set_name_color(
                QColor(p.cht_name_color), QColor(p.cht_name_color).darker(130)
            )
            self.apply_text_size(p.cht_label_size)
        self._layout.addWidget(self._chart)

        # ── Footer ───────────────────────────────────────────────────────────
        self._filter_btn = _PlayerFilterButton()
        self._filter_btn.filter_changed.connect(self._refresh_chart)
        self._footer = _LocalPlayerFooter(
            show_dps=True,
            show_hps=True,
            show_dtps=True,
            show_crit=True,
            filter_widget=self._filter_btn,
        )
        self._layout.addWidget(self._footer)

    # ── watcher API ──────────────────────────────────────────────────────────

    def receive_watcher(self, watcher: LogWatcher) -> None:
        self._watcher = watcher
        watcher.fight_opened.connect(self._on_fight_opened)
        watcher.fight_closed.connect(self._on_fight_closed)
        watcher.fight_updated.connect(self._on_live_fight_updated)
        watcher.session_reset.connect(self._on_session_reset)

        # Seed Live scope from current runtime state.
        if watcher.current_fight is not None:
            self._live_fight = watcher.current_fight
        elif watcher.session.fights:
            self._live_fight = watcher.session.fights[-1]

    def receive_session_loader(self, loader: SessionLoader) -> None:
        self._session_loader = loader
        loader.sessions_changed.connect(self._rebuild_scope_combo)

    def _on_fight_opened(self, fight: Fight) -> None:
        self._live_fight = fight
        if self._scope_combo.currentText() == _SCOPE_LIVE:
            self._refresh_chart()

    def _on_fight_closed(self, fight: Fight) -> None:
        # Keep _live_fight pointing at the finished fight so Live scope stays
        # populated until the next fight opens.
        self._live_fight = fight
        self._rebuild_scope_combo()  # also rebuilds fight combo
        self._refresh_chart()

    def _on_live_fight_updated(self, fight: Fight) -> None:
        self._live_fight = fight
        # Update footer regardless of scope
        p = self._prefs
        self._my_name = (
            (p.character_name if p and p.character_name else "") if p else None
        )
        if self._my_name:
            stats = next(
                (s for s in fight.player_stats.values() if player_stats_matches(self._my_name, s)),
                None,
            )
            self._footer.update_stats(stats, fight.duration_s)
        # Refresh chart only if live scope selected
        if self._scope_combo.currentText() == _SCOPE_LIVE:
            self._refresh_chart()

    def _on_session_reset(self) -> None:
        self._live_fight = None
        self._rebuild_scope_combo()  # also rebuilds fight combo
        self._footer.update_stats(None, 1.0)
        self._refresh_chart()

    def _rebuild_scope_combo(self) -> None:
        """Repopulate scope dropdown from current session fights + previous sessions."""
        session = self._watcher.session if self._watcher else CombatSession()
        current = self._scope_combo.currentText()
        self._scope_combo.blockSignals(True)
        self._scope_combo.clear()
        self._scope_combo.addItem(_SCOPE_SESSION)
        self._scope_combo.addItem(_SCOPE_LIVE)
        for f in session.fights:
            self._scope_combo.addItem(f"Fight {f.index}")
        # Previous sessions (oldest → newest)
        if self._session_loader:
            for entry in self._session_loader.entries:
                self._scope_combo.addItem(entry.label)
        # Restore previous selection if still valid
        idx = self._scope_combo.findText(current)
        self._scope_combo.setCurrentIndex(max(idx, 0))
        self._scope_combo.blockSignals(False)
        self._rebuild_fight_combo()
        self._apply_scope_ui_state()

    def _rebuild_fight_combo(self) -> None:
        """Repopulate the fight selector with fights from the currently-scoped session."""
        scope = self._scope_combo.currentText()
        session = self._get_session_for_line(scope)
        current = self._fight_combo.currentText()
        self._fight_combo.blockSignals(True)
        self._fight_combo.clear()
        self._fight_combo.addItem(_FIGHT_ALL)
        if scope != _SCOPE_LIVE:
            for f in session.fights:
                self._fight_combo.addItem(f"Fight {f.index}")
        idx = self._fight_combo.findText(current)
        self._fight_combo.setCurrentIndex(max(idx, 0))
        self._fight_combo.blockSignals(False)

    def _on_chart_type_changed(self, chart_type: str) -> None:
        self._chart.set_chart_type(chart_type)
        self._refresh_chart()
        self._resize_to_content()

    def _on_scope_changed(self, _scope: str) -> None:
        """Scope changed: rebuild fight combo then refresh chart."""
        self._rebuild_fight_combo()
        self._apply_scope_ui_state()
        self._refresh_chart()

    def _apply_scope_ui_state(self) -> None:
        is_live = self._scope_combo.currentText() == _SCOPE_LIVE
        self._fight_combo.setEnabled(not is_live)
        if is_live:
            idx = self._fight_combo.findText(_FIGHT_ALL)
            if idx >= 0:
                self._fight_combo.blockSignals(True)
                self._fight_combo.setCurrentIndex(idx)
                self._fight_combo.blockSignals(False)

    def _refresh_chart(self, _=None) -> None:
        chart_type = self._chart_type_combo.currentText()
        scope = self._scope_combo.currentText()
        stat_label = self._stat_combo.currentText()
        p = self._prefs
        self._my_name = (
            (p.character_name if p and p.character_name else "") if p else None
        )

        if chart_type == "Line":
            fight_sel = self._fight_combo.currentText()
            if scope == _SCOPE_LIVE:
                fight = self._live_fight
                if fight is None:
                    player_series, fight_labels = {}, []
                else:
                    player_series, fight_labels = self._build_intra_fight_series(
                        fight, stat_label
                    )
            else:
                session = self._get_session_for_line(scope)
                if fight_sel != _FIGHT_ALL:
                    # Single fight selected: per-second time series
                    try:
                        fi = int(fight_sel.split()[1]) - 1
                        fight = session.fights[fi]
                        player_series, fight_labels = self._build_intra_fight_series(
                            fight, stat_label
                        )
                    except (ValueError, IndexError):
                        player_series, fight_labels = {}, []
                else:
                    player_series, fight_labels = self._build_line_series(
                        session, stat_label, fight_sel
                    )
            self._filter_btn.set_players(list(player_series.keys()))
            visible = {
                n: v
                for n, v in player_series.items()
                if n not in self._filter_btn.hidden_players
            }
            self._chart.set_line_data(visible, fight_labels)
        else:
            fight_sel = self._fight_combo.currentText()
            all_entries = self._build_entries(scope, stat_label, fight_sel)
            # Keep filter player list in sync with available players
            self._filter_btn.set_players([name for name, _, _ in all_entries])
            visible_list = [
                (n, v, m)
                for n, v, m in all_entries
                if n not in self._filter_btn.hidden_players
            ]
            self._chart.set_data(visible_list)
        self._resize_to_content()

    def _get_session_for_line(self, scope: str) -> CombatSession:
        """Return the session to use for the Line chart time series."""
        live = self._watcher.session if self._watcher else CombatSession()
        if scope in (_SCOPE_SESSION, _SCOPE_LIVE) or scope.startswith("Fight "):
            return live
        if self._session_loader:
            for entry in self._session_loader.entries:
                if entry.label == scope:
                    return entry.session
        return live

    def _build_intra_fight_series(
        self,
        fight: Fight,
        stat_label: str,
    ) -> tuple[dict[str, tuple[bool, list[float | None]]], list[str]]:
        """Per-second cumulative stat series within a single fight."""
        if not fight.events:
            return {}, []

        duration_s = int(fight.duration_s) or 1
        running: dict[str, PlayerFightStats] = {}
        aid_to_name: dict[str, str] = {}
        for stats in fight.player_stats.values():
            aid_to_name[stats.account_id] = stats.name
            running[stats.name] = PlayerFightStats(
                name=stats.name, account_id=stats.account_id
            )

        events_sorted = sorted(fight.events, key=lambda e: e.timestamp_ms)
        series: dict[str, list[float | None]] = {n: [] for n in running}
        labels: list[str] = []

        event_idx = 0
        n_events = len(events_sorted)
        for sec in range(1, duration_s + 1):
            cutoff_ms = fight.start_ms + sec * 1000
            while (
                event_idx < n_events
                and events_sorted[event_idx].timestamp_ms <= cutoff_ms
            ):
                ev = events_sorted[event_idx]
                src = ev.source
                tgt = ev.target
                if ev.effect_type == APPLY_EFFECT:
                    if ev.effect_name == DAMAGE:
                        if (
                            src is not None
                            and src.kind == PLAYER
                            and src.account_id in aid_to_name
                        ):
                            s = running[aid_to_name[src.account_id]]
                            s.damage_out += ev.effective_amount
                            if ev.effective_amount > 0:
                                s.hit_count += 1
                                if ev.is_crit:
                                    s.crit_count += 1
                        if (
                            tgt is not None
                            and tgt.kind == PLAYER
                            and tgt.account_id in aid_to_name
                        ):
                            if src is None or src.kind != PLAYER:
                                running[
                                    aid_to_name[tgt.account_id]
                                ].damage_in += ev.effective_amount
                    elif ev.effect_name == HEAL:
                        if (
                            src is not None
                            and src.kind == PLAYER
                            and src.account_id in aid_to_name
                        ):
                            net = max(ev.amount - ev.mitigation, 0)
                            running[aid_to_name[src.account_id]].heal_out += net
                event_idx += 1
            elapsed = float(sec)
            for name, s in running.items():
                series[name].append(_get_stat(s, stat_label, elapsed))
            labels.append(str(sec))

        player_series: dict[str, tuple[bool, list[float | None]]] = {
            name: (player_name_matches(self._my_name, name), vals)
            for name, vals in series.items()
        }
        return player_series, labels

    def _build_line_series(
        self,
        session: CombatSession,
        stat_label: str,
        fight_sel: str = _FIGHT_ALL,
    ) -> tuple[dict[str, tuple[bool, list[float | None]]], list[str]]:
        """Build per-fight time series for all players across fights in the session."""
        fights = session.fights
        if not fights:
            return {}, []
        # Filter to a single fight when one is selected
        if fight_sel != _FIGHT_ALL:
            try:
                fi = int(fight_sel.split()[1]) - 1
                fights = [session.fights[fi]]
            except (ValueError, IndexError):
                pass
        fight_labels = [f"F{f.index}" for f in fights]
        # Collect all player names
        all_names: dict[str, bool] = {}
        for fight in fights:
            for stats in fight.player_stats.values():
                all_names[stats.name] = player_name_matches(self._my_name, stats.name)
        # Build per-player series
        player_series: dict[str, tuple[bool, list[float | None]]] = {}
        for name, is_me in all_names.items():
            values: list[float | None] = []
            for fight in fights:
                stats = next(
                    (s for s in fight.player_stats.values() if s.name == name), None
                )
                values.append(
                    _get_stat(stats, stat_label, fight.duration_s)
                    if stats is not None
                    else None
                )
            player_series[name] = (is_me, values)
        return player_series, fight_labels

    def _build_entries(
        self, scope: str, stat_label: str, fight_sel: str = _FIGHT_ALL
    ) -> list[tuple[str, float, bool]]:
        """Return [(name, value, is_me), ...] sorted descending."""
        session = self._watcher.session if self._watcher else CombatSession()

        # If a specific fight is selected in the fight combo, use it regardless of scope
        if fight_sel != _FIGHT_ALL and scope != _SCOPE_LIVE:
            try:
                fi = int(fight_sel.split()[1]) - 1
                # Resolve session (scope may point to a historical session)
                if scope not in (_SCOPE_SESSION, _SCOPE_LIVE) and not scope.startswith(
                    "Fight "
                ):
                    if self._session_loader:
                        for entry in self._session_loader.entries:
                            if entry.label == scope:
                                session = entry.session
                                break
                fight = session.fights[fi]
                return self._entries_from_fight(fight, stat_label)
            except (ValueError, IndexError):
                pass

        if scope == _SCOPE_SESSION:
            # Aggregate across all fights
            all_ids = session.all_player_ids()
            raw: list[tuple[str, float, bool]] = []
            for aid in all_ids:
                agg = session.aggregate_player_stats(aid)
                if agg is None:
                    continue
                total_dur = sum(
                    f.duration_s for f in session.fights if aid in f.player_stats
                )
                val = _get_stat(agg, stat_label, total_dur)
                is_me = player_name_matches(self._my_name, agg.name)
                raw.append((agg.name, val, is_me))
            raw.sort(key=lambda x: x[1], reverse=True)
            return raw

        if scope == _SCOPE_LIVE:
            fight = self._live_fight
            if fight is None:
                return []
            return self._entries_from_fight(fight, stat_label)

        # Named fight: "Fight N"
        if scope.startswith("Fight "):
            try:
                idx = int(scope.split()[1]) - 1
                fight = session.fights[idx]
                return self._entries_from_fight(fight, stat_label)
            except (ValueError, IndexError):
                return []

        # Previous session: match by label
        if self._session_loader:
            for entry in self._session_loader.entries:
                if entry.label == scope:
                    return self._entries_from_session(entry.session, stat_label)

        return []

    def _entries_from_fight(
        self, fight: Fight, stat_label: str
    ) -> list[tuple[str, float, bool]]:
        dur = fight.duration_s
        raw = []
        for stats in fight.player_stats.values():
            val = _get_stat(stats, stat_label, dur)
            raw.append((stats.name, val, player_name_matches(self._my_name, stats.name)))
        raw.sort(key=lambda x: x[1], reverse=True)
        return raw

    def _entries_from_session(
        self, session: CombatSession, stat_label: str
    ) -> list[tuple[str, float, bool]]:
        """Aggregate all fights in a (historical) session into one entry list."""
        all_ids = session.all_player_ids()
        raw: list[tuple[str, float, bool]] = []
        for aid in all_ids:
            agg = session.aggregate_player_stats(aid)
            if agg is None:
                continue
            total_dur = sum(
                f.duration_s for f in session.fights if aid in f.player_stats
            )
            val = _get_stat(agg, stat_label, total_dur)
            is_me = player_name_matches(self._my_name, agg.name)
            raw.append((agg.name, val, is_me))
        raw.sort(key=lambda x: x[1], reverse=True)
        return raw

    # ── apply_* API (called by OverlayMasterWindow) ───────────────────────────

    def apply_win_width(self, v: int) -> None:
        self._min_content_width = v
        if self._prefs:
            self._prefs.cht_win_width = v
        self._resize_to_content()

    def apply_win_height(self, v: int) -> None:
        self._max_content_height = v
        if self._prefs:
            self._prefs.cht_win_height = v
        self._resize_to_content()

    def apply_win_bg_alpha(self, v: int) -> None:
        if self._prefs:
            self._prefs.cht_win_bg_alpha = v
        self.update()

    def apply_win_bg_color(self, c: str) -> None:
        if self._prefs:
            self._prefs.cht_win_bg_color = c
        self.update()

    def apply_name_size(self, v: int) -> None:
        self._chart.set_name_size(v)
        if self._prefs:
            self._prefs.cht_name_size = v

    def apply_name_color(self, c: str) -> None:
        self._chart.set_name_color(QColor(c), QColor(c).darker(130))
        if self._prefs:
            self._prefs.cht_name_color = c

    def apply_me_color(self, c: str) -> None:
        self._chart.set_me_color(QColor(c))
        if self._prefs:
            self._prefs.cht_me_color = c

    def apply_other_color(self, c: str) -> None:
        self._chart.set_other_color(QColor(c))
        if self._prefs:
            self._prefs.cht_other_color = c

    def apply_val_size(self, v: int) -> None:
        self._chart.set_val_size(v)
        if self._prefs:
            self._prefs.cht_val_size = v

    def apply_text_size(self, v: int) -> None:
        if self._prefs:
            self._prefs.cht_label_size = v
        style = re.sub(r"font-size:\s*\d+px", f"font-size: {v}px", _LABEL_STYLE)
        for lbl in (self._scope_lbl, self._stat_lbl, self._chart_lbl, self._fight_lbl):
            lbl.setStyleSheet(style)
        combo_style = re.sub(r"font-size:\s*\d+px", f"font-size: {v}px", _COMBO_STYLE)
        for combo in (
            self._scope_combo,
            self._stat_combo,
            self._chart_type_combo,
            self._fight_combo,
        ):
            combo.setStyleSheet(combo_style)

    def apply_character_name(self, name: str) -> None:
        self._my_name = (name or "").strip() or None

        if self._live_fight is not None and self._my_name is not None:
            stats = next(
                (s for s in self._live_fight.player_stats.values() if player_stats_matches(self._my_name, s)),
                None,
            )
            self._footer.update_stats(stats, self._live_fight.duration_s)
        else:
            self._footer.update_stats(None, 1.0)

        self._refresh_chart()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        p = self._prefs
        alpha = getattr(p, "cht_win_bg_alpha", 0) if p else 0
        if alpha > 0:
            c = QColor(getattr(p, "cht_win_bg_color", "#000000") if p else "#000000")
            c.setAlpha(round(alpha * 255 / 100))
        else:
            c = QColor(20, 20, 30, 200)
        painter.setBrush(c)
        pen = QPen(QColor("#6ab8ff"), 1)
        painter.setPen(pen)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 5, 5)
        super().paintEvent(event)

