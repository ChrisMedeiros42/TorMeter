"""Concrete player-list overlay window types."""

from __future__ import annotations

import time

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from app.combat_session import Fight
from app.constants import fmt_num
from app.overlays_shared.widgets import _LocalPlayerFooter

from ..helpers import _RotatedLabel
from .base import _PlayerListOverlay
from .rows import _SummaryPlayerRow

class SummaryWindow(_PlayerListOverlay):
    title = "Summary"
    window_name = "Summary"
    bar_color = "#6B6B00"

    def _setup_content(self):  # noqa: C901
        p = self._prefs

        def _pv(attr, default):
            return getattr(p, attr, default) if p else default

        my_name = (p.character_name if p and p.character_name else "") or "Me"
        name_size = _pv("sum_name_size", 9)
        name_color = _pv("sum_name_color", "#FFFFFF")
        name_col_color = _pv("sum_name_col_color", "transparent")
        win_width = _pv("sum_win_width", 300)
        avg_show = _pv("sum_avg_show", True)
        total_show = _pv("sum_total_show", True)
        border_show = _pv("sum_bar_border_show", False)
        border_size = _pv("sum_bar_border_size", 1)
        border_color = _pv("sum_bar_border_color", "#FFFFFF")
        score_show = _pv("sum_score_show", True)
        score_size = _pv("sum_score_size", 9)
        score_color = _pv("sum_score_color", "#FFD700")
        bar_bg_show = _pv("sum_bar_bg_show", True)
        bar_bg_size = _pv("sum_bar_bg_size", 12)
        bar_bg_color = _pv("sum_bar_bg_color", "#FFFFFF")
        outline_show = _pv("sum_outline_show", True)
        outline_size = _pv("sum_outline_size", 1)
        outline_color = _pv("sum_outline_color", "#000000")
        row_height = _pv("sum_row_height", 24)
        dps_stat_show = _pv("sum_dps_show", True)
        dps_stat_size = _pv("sum_dps_size", 8)
        dps_stat_color = _pv("sum_dps_color", "#FF8C00")
        dps_fg_show = _pv("sum_dps_bar_fg_show", True)
        dps_fg_size = _pv("sum_dps_bar_fg_size", 71)
        dps_fg_color = _pv("sum_dps_bar_fg_color", "#7A2020")
        def_stat_show = _pv("sum_def_show", True)
        def_stat_size = _pv("sum_def_size", 8)
        def_stat_color = _pv("sum_def_color", "#4169E1")
        def_fg_show = _pv("sum_def_bar_fg_show", True)
        def_fg_size = _pv("sum_def_bar_fg_size", 71)
        def_fg_color = _pv("sum_def_bar_fg_color", "#1E3A7A")
        heal_stat_show = _pv("sum_heal_show", True)
        heal_stat_size = _pv("sum_heal_size", 8)
        heal_stat_color = _pv("sum_heal_color", "#32CD32")
        heal_fg_show = _pv("sum_heal_bar_fg_show", True)
        heal_fg_size = _pv("sum_heal_bar_fg_size", 71)
        heal_fg_color = _pv("sum_heal_bar_fg_color", "#1E6B1E")

        self._min_content_width = win_width
        self._win_bg_alpha: int = _pv("sum_win_bg_alpha", 0)
        self._win_bg_color: str = _pv("sum_win_bg_color", "#000000")
        self._avg_show: bool = avg_show
        self._total_show: bool = total_show

        players = (
            [(my_name, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)]
            if my_name and my_name != "Me"
            else []
        )

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        inner_l = QVBoxLayout(inner)
        inner_l.setContentsMargins(0, 0, 0, 0)
        inner_l.setSpacing(2)
        self._inner_layout = inner_l

        self._rows: list[_SummaryPlayerRow] = []
        for nm, dv, dt, efv, eft, hv, ht, sc in players:
            row = _SummaryPlayerRow(
                name=nm,
                dps_value=dv,
                dps_total=dt,
                def_value=efv,
                def_total=eft,
                heal_value=hv,
                heal_total=ht,
                score=sc,
                is_me=(nm == my_name),
                name_size=name_size,
                name_color=name_color,
                score_show=score_show,
                score_size=score_size,
                score_color=score_color,
                dps_stat_show=dps_stat_show,
                dps_stat_size=dps_stat_size,
                dps_stat_color=dps_stat_color,
                dps_avg_show=avg_show,
                dps_total_show=total_show,
                dps_bar_fg_show=dps_fg_show,
                dps_bar_fg_size=dps_fg_size,
                dps_bar_fg_color=dps_fg_color,
                def_stat_show=def_stat_show,
                def_stat_size=def_stat_size,
                def_stat_color=def_stat_color,
                def_avg_show=avg_show,
                def_total_show=total_show,
                def_bar_fg_show=def_fg_show,
                def_bar_fg_size=def_fg_size,
                def_bar_fg_color=def_fg_color,
                heal_stat_show=heal_stat_show,
                heal_stat_size=heal_stat_size,
                heal_stat_color=heal_stat_color,
                heal_avg_show=avg_show,
                heal_total_show=total_show,
                heal_bar_fg_show=heal_fg_show,
                heal_bar_fg_size=heal_fg_size,
                heal_bar_fg_color=heal_fg_color,
                bar_bg_show=bar_bg_show,
                bar_bg_size=bar_bg_size,
                bar_bg_color=bar_bg_color,
                border_show=border_show,
                border_size=border_size,
                border_color=border_color,
                outline_show=outline_show,
                outline_size=outline_size,
                outline_color=outline_color,
                row_height=row_height,
            )
            row.set_name_col_color(name_col_color)
            self._rows.append(row)
            inner_l.addWidget(row)

        bg = QColor(self.bar_color)
        bg.setAlpha(51)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        container_l = QHBoxLayout(container)
        container_l.setContentsMargins(2, 2, 2, 2)
        container_l.setSpacing(4)
        container_l.addWidget(_RotatedLabel(self.title, bg, parent=container))
        container_l.addWidget(inner, 1)

        self._layout.addWidget(container)

        # ── footer: local-player effective stats ──────────────────────────────
        self._footer = _LocalPlayerFooter(
            show_dps=True, show_hps=True, show_dtps=True, show_crit=True
        )
        self._layout.addWidget(self._footer)

        # State for live updates
        self._player_last_seen_wall: dict[str, float] = {}
        self._show_companions: bool = _pv("sum_show_companions", False)
        self._timeout_timer = QTimer(self)
        self._timeout_timer.setInterval(2000)
        self._timeout_timer.timeout.connect(self._prune_timed_out_players)
        self._timeout_timer.start()

    # ── live data API (mirrors _PlayerListOverlay) ────────────────────────────

    def receive_watcher(self, watcher) -> None:
        watcher.fight_updated.connect(self._on_fight_updated)
        watcher.fight_closed.connect(self._on_fight_closed)
        watcher.session_reset.connect(self._on_session_reset)
        self._watcher = watcher

    def _on_fight_updated(self, fight: "Fight") -> None:
        p = self._prefs
        my_name = (p.character_name if p and p.character_name else "") if p else None
        duration_s = fight.duration_s

        all_stats = dict(fight.player_stats)
        if getattr(self, "_show_companions", False):
            all_stats.update(getattr(fight, "companion_stats", {}))

        # Sync last-seen times from the watcher's per-event tracking.
        watcher_seen = getattr(self._watcher, "player_last_seen", {}) if hasattr(self, "_watcher") else {}
        now = time.monotonic()
        keep_ms = self._effective_keep_ms()

        def _is_recent(aid: str) -> bool:
            ts = self._player_last_seen_wall.get(aid)
            return ts is not None and (now - ts) * 1000 < keep_ms

        scored: list[tuple[float, str, object, object]] = []
        for aid, stats in all_stats.items():
            if aid in watcher_seen:
                self._player_last_seen_wall[aid] = watcher_seen[aid]
            elif aid not in self._player_last_seen_wall:
                self._player_last_seen_wall[aid] = time.monotonic()
            if not _is_recent(aid):
                continue
            avg_show = getattr(self, "_avg_show", True)
            total_show = getattr(self, "_total_show", True)
            if avg_show and total_show:
                score = (stats.dps(duration_s) + stats.damage_out +
                         stats.dtps(duration_s) + stats.damage_in +
                         stats.hps(duration_s) + stats.heal_out)
            elif avg_show:
                score = stats.dps(duration_s) + stats.dtps(duration_s) + stats.hps(duration_s)
            else:
                score = stats.damage_out + stats.damage_in + stats.heal_out
            if score <= 0:
                continue
            row = next(
                (
                    r
                    for r in self._rows
                    if getattr(r, "_account_id", r._name_lbl.text()) == aid
                    or r._name_lbl.text() == stats.name
                ),
                None,
            )
            if row is None:
                row = self._add_summary_row(
                    stats.name, account_id=aid, is_me=(stats.name == my_name)
                )
            row.setVisible(True)
            row._score_lbl.setText(fmt_num(score))
            scored.append((score, aid, stats, row))

        # Keep recently-seen players visible even when score is currently zero.
        active_names = {stats.name for _, _, stats, _ in scored}
        active_ids = {aid for _, aid, _, _ in scored}

        for row in self._rows:
            aid = getattr(row, "_account_id", row._name_lbl.text())
            row.setVisible(row._name_lbl.text() in active_names or _is_recent(aid))

        total_score = sum(s for s, _, _, _ in scored) or 1.0
        row_scores: dict[object, float] = {}

        for score, _aid, stats, row in scored:
            row._bar.update_data(
                stats.dps(duration_s),
                stats.damage_out,
                stats.dtps(duration_s),
                stats.damage_in,
                stats.hps(duration_s),
                stats.heal_out,
                fill_frac=score / total_score,
            )
            row_scores[row] = score

        # Keep recent-but-inactive rows visible with a zero score so list order
        # always matches the right-side value used for sorting.
        for row in self._rows:
            aid = getattr(row, "_account_id", row._name_lbl.text())
            if aid in active_ids:
                continue
            if row.isVisible():
                row._bar.update_data(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, fill_frac=0.0)
                row._score_lbl.setText(fmt_num(0.0))
            row_scores[row] = 0.0

        # Reorder layout by score descending
        inner = getattr(self, "_inner_layout", None)
        if inner is not None:
            visible_rows = [r for r in self._rows if r.isVisible()]
            visible_rows.sort(key=lambda r: row_scores.get(r, 0.0), reverse=True)
            for row in visible_rows:
                inner.removeWidget(row)
                inner.addWidget(row)

        if my_name:
            my_stats = next(
                (s for s in fight.player_stats.values() if s.name == my_name), None
            )
            self._footer.update_stats(my_stats, duration_s)

        self._resize_to_content()

    def _on_fight_closed(self, fight: "Fight") -> None:
        self._on_fight_updated(fight)

    def _on_session_reset(self) -> None:
        p = self._prefs
        my_name = (p.character_name if p and p.character_name else "") if p else None
        for row in list(self._rows):
            if row._name_lbl.text() == my_name:
                row._bar.update_data(0.0, 1.0, 0.0, 1.0, 0.0, 1.0)
                row._score_lbl.setText("")
                continue
            row.setParent(None)
            row.deleteLater()
            self._rows.remove(row)
        self._player_last_seen_wall.clear()
        self._resize_to_content()

    def _add_summary_row(
        self, name: str, account_id: str | None = None, is_me: bool = False
    ) -> "_SummaryPlayerRow":
        p = self._prefs

        def _pv(attr, default):
            return getattr(p, attr, default) if p else default

        row = _SummaryPlayerRow(
            name=name,
            is_me=is_me,
            name_size=_pv("sum_name_size", 9),
            name_color=_pv("sum_name_color", "#FFFFFF"),
            score_show=_pv("sum_score_show", True),
            score_size=_pv("sum_score_size", 9),
            score_color=_pv("sum_score_color", "#FFD700"),
            dps_stat_show=_pv("sum_dps_show", True),
            dps_stat_size=_pv("sum_dps_size", 8),
            dps_stat_color=_pv("sum_dps_color", "#FF8C00"),
            dps_avg_show=_pv("sum_avg_show", True),
            dps_total_show=_pv("sum_total_show", True),
            dps_bar_fg_show=_pv("sum_dps_bar_fg_show", True),
            dps_bar_fg_size=_pv("sum_dps_bar_fg_size", 71),
            dps_bar_fg_color=_pv("sum_dps_bar_fg_color", "#7A2020"),
            def_stat_show=_pv("sum_def_show", True),
            def_stat_size=_pv("sum_def_size", 8),
            def_stat_color=_pv("sum_def_color", "#4169E1"),
            def_avg_show=_pv("sum_avg_show", True),
            def_total_show=_pv("sum_total_show", True),
            def_bar_fg_show=_pv("sum_def_bar_fg_show", True),
            def_bar_fg_size=_pv("sum_def_bar_fg_size", 71),
            def_bar_fg_color=_pv("sum_def_bar_fg_color", "#1E3A7A"),
            heal_stat_show=_pv("sum_heal_show", True),
            heal_stat_size=_pv("sum_heal_size", 8),
            heal_stat_color=_pv("sum_heal_color", "#32CD32"),
            heal_avg_show=_pv("sum_avg_show", True),
            heal_total_show=_pv("sum_total_show", True),
            heal_bar_fg_show=_pv("sum_heal_bar_fg_show", True),
            heal_bar_fg_size=_pv("sum_heal_bar_fg_size", 71),
            heal_bar_fg_color=_pv("sum_heal_bar_fg_color", "#1E6B1E"),
            bar_bg_show=_pv("sum_bar_bg_show", True),
            bar_bg_size=_pv("sum_bar_bg_size", 12),
            bar_bg_color=_pv("sum_bar_bg_color", "#FFFFFF"),
            border_show=_pv("sum_bar_border_show", False),
            border_size=_pv("sum_bar_border_size", 1),
            border_color=_pv("sum_bar_border_color", "#FFFFFF"),
            outline_show=_pv("sum_outline_show", True),
            outline_size=_pv("sum_outline_size", 1),
            outline_color=_pv("sum_outline_color", "#000000"),
            row_height=_pv("sum_row_height", 24),
        )
        row._account_id = account_id or name
        row.set_name_col_color(_pv("sum_name_col_color", "transparent"))
        self._inner_layout.addWidget(row)
        self._rows.append(row)
        return row

    def _prune_timed_out_players(self) -> None:
        p = self._prefs
        my_name = (p.character_name if p and p.character_name else "") if p else None
        now = time.monotonic()
        keep_ms = self._effective_keep_ms()
        to_remove_ids = {
            aid
            for aid, ts in list(self._player_last_seen_wall.items())
            if (now - ts) * 1000 >= keep_ms
        }
        for row in list(self._rows):
            name = row._name_lbl.text()
            if name == my_name:
                continue
            aid = getattr(row, "_account_id", name)
            if aid in to_remove_ids:
                row.setParent(None)
                row.deleteLater()
                self._rows.remove(row)
                self._player_last_seen_wall.pop(aid, None)
        if to_remove_ids:
            self._resize_to_content()

    # ── bulk apply methods ────────────────────────────────────────────────────
    def apply_name_size(self, v: int) -> None:
        self._apply_to_rows("set_name_size", v)

    def apply_name_color(self, c: str) -> None:
        self._apply_to_rows("set_name_color", c)

    def apply_avg_show(self, b: bool) -> None:
        self._avg_show = b
        self._apply_to_rows("set_avg_show", b)

    def apply_total_show(self, b: bool) -> None:
        self._total_show = b
        self._apply_to_rows("set_total_show", b)

    def apply_border_show(self, b: bool) -> None:
        self._apply_to_rows("set_border_show", b)

    def apply_border_size(self, v: int) -> None:
        self._apply_to_rows("set_border_size", v)

    def apply_border_color(self, c: str) -> None:
        self._apply_to_rows("set_border_color", c)

    def apply_bar_bg_show(self, b: bool) -> None:
        self._apply_to_rows("set_bar_bg_show", b)

    def apply_bar_bg_size(self, v: int) -> None:
        self._apply_to_rows("set_bar_bg_size", v)

    def apply_bar_bg_color(self, c: str) -> None:
        self._apply_to_rows("set_bar_bg_color", c)

    def apply_score_show(self, b: bool) -> None:
        self._apply_to_rows("set_score_show", b)

    def apply_score_size(self, v: int) -> None:
        self._apply_to_rows("set_score_size", v)

    def apply_score_color(self, c: str) -> None:
        self._apply_to_rows("set_score_color", c)

    def apply_dps_stat_show(self, b: bool) -> None:
        self._apply_to_rows("set_dps_stat_show", b)

    def apply_dps_stat_size(self, v: int) -> None:
        self._apply_to_rows("set_dps_stat_size", v)

    def apply_dps_stat_color(self, c: str) -> None:
        self._apply_to_rows("set_dps_stat_color", c)

    def apply_dps_bar_fg_show(self, b: bool) -> None:
        self._apply_to_rows("set_dps_bar_fg_show", b)

    def apply_dps_bar_fg_size(self, v: int) -> None:
        self._apply_to_rows("set_dps_bar_fg_size", v)

    def apply_dps_bar_fg_color(self, c: str) -> None:
        self._apply_to_rows("set_dps_bar_fg_color", c)

    def apply_def_stat_show(self, b: bool) -> None:
        self._apply_to_rows("set_def_stat_show", b)

    def apply_def_stat_size(self, v: int) -> None:
        self._apply_to_rows("set_def_stat_size", v)

    def apply_def_stat_color(self, c: str) -> None:
        self._apply_to_rows("set_def_stat_color", c)

    def apply_def_bar_fg_show(self, b: bool) -> None:
        self._apply_to_rows("set_def_bar_fg_show", b)

    def apply_def_bar_fg_size(self, v: int) -> None:
        self._apply_to_rows("set_def_bar_fg_size", v)

    def apply_def_bar_fg_color(self, c: str) -> None:
        self._apply_to_rows("set_def_bar_fg_color", c)

    def apply_heal_stat_show(self, b: bool) -> None:
        self._apply_to_rows("set_heal_stat_show", b)

    def apply_heal_stat_size(self, v: int) -> None:
        self._apply_to_rows("set_heal_stat_size", v)

    def apply_heal_stat_color(self, c: str) -> None:
        self._apply_to_rows("set_heal_stat_color", c)

    def apply_heal_bar_fg_show(self, b: bool) -> None:
        self._apply_to_rows("set_heal_bar_fg_show", b)

    def apply_heal_bar_fg_size(self, v: int) -> None:
        self._apply_to_rows("set_heal_bar_fg_size", v)

    def apply_heal_bar_fg_color(self, c: str) -> None:
        self._apply_to_rows("set_heal_bar_fg_color", c)

    def apply_show_companions(self, b: bool) -> None:
        self._show_companions = b

    def apply_outline_show(self, b: bool) -> None:
        self._apply_to_rows("set_outline_show", b)

    def apply_outline_size(self, v: int) -> None:
        self._apply_to_rows("set_outline_size", v)

    def apply_outline_color(self, c: str) -> None:
        self._apply_to_rows("set_outline_color", c)

    def apply_row_height(self, v: int) -> None:
        self._apply_to_rows("set_row_height", v)
        self._resize_to_content()


class DpsWindow(_PlayerListOverlay):
    title = "DPS"
    window_name = "DPS"
    bar_color = "#7A2020"
    prefs_prefix = "dps"


class DefenseWindow(_PlayerListOverlay):
    title = "Defense"
    window_name = "Defense"
    bar_color = "#1E3A7A"
    prefs_prefix = "def"


class HealWindow(_PlayerListOverlay):
    title = "Heal"
    window_name = "Heal"
    bar_color = "#1E6B1E"
    prefs_prefix = "heal"


