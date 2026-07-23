"""Base player-list overlay class."""

from __future__ import annotations

import time

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from app.combat_session import Fight, PlayerFightStats
from app.constants import fmt_num
from app.overlays_shared.player_match import player_name_matches, player_stats_matches
from app.overlays_shared.widgets import _LocalPlayerFooter
from app.window import OverlayWindow

from ..helpers import _RotatedLabel
from .rows import PlayerRow, _SummaryPlayerRow

class _PlayerListOverlay(OverlayWindow):
    """Base class for overlays that display a sorted list of PlayerRow items."""

    bar_color: str = "#444444"
    prefs_prefix: str = ""  # "dps", "def", "heal"

    def _setup_content(self):
        p = self._prefs
        g = self.prefs_prefix
        my_name = (p.character_name if p and p.character_name else "") or "Me"

        # Read per-group display settings from prefs (fall back to defaults if not set)
        def _pv(attr, default):
            return getattr(p, attr, default) if p and g else default

        name_size = _pv(f"{g}_name_size", 9)
        name_color = _pv(f"{g}_name_color", "#FFFFFF")
        name_col_color = _pv(f"{g}_name_col_color", "transparent")
        win_width = _pv(f"{g}_win_width", 300)
        stat_show = _pv(f"{g}_{g}_show", True)
        stat_size = _pv(f"{g}_{g}_size", 8)
        stat_color = _pv(f"{g}_{g}_color", "#FFFFFF")
        avg_show = _pv(f"{g}_avg_show", True)
        total_show = _pv(f"{g}_total_show", True)
        border_show = _pv(f"{g}_bar_border_show", False)
        border_size = _pv(f"{g}_bar_border_size", 1)
        border_color = _pv(f"{g}_bar_border_color", "#FFFFFF")
        bar_bg_show = _pv(f"{g}_bar_bg_show", True)
        bar_bg_size = _pv(f"{g}_bar_bg_size", 12)
        bar_bg_color = _pv(f"{g}_bar_bg_color", "#FFFFFF")
        bar_fg_show = _pv(f"{g}_bar_fg_show", True)
        bar_fg_size = _pv(f"{g}_bar_fg_size", 71)
        bar_fg_color = _pv(f"{g}_bar_fg_color", self.bar_color)
        score_show = _pv(f"{g}_score_show", True)
        score_size = _pv(f"{g}_score_size", 9)
        score_color = _pv(f"{g}_score_color", "#FFD700")
        outline_show = _pv(f"{g}_outline_show", True)
        outline_size = _pv(f"{g}_outline_size", 1)
        outline_color = _pv(f"{g}_outline_color", "#000000")
        row_height = _pv(f"{g}_row_height", 24)

        self._min_content_width = win_width
        self._win_bg_alpha: int = _pv(f"{g}_win_bg_alpha", 0)
        self._win_bg_color: str = _pv(f"{g}_win_bg_color", "#000000")
        self._avg_show: bool = avg_show
        self._total_show: bool = total_show

        players: list[tuple[str, float, float, float]] = (
            [(my_name, 0.0, 0.0, 0.0)] if my_name and my_name != "Me" else []
        )

        # Inner widget holding all player rows
        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        inner_l = QVBoxLayout(inner)
        inner_l.setContentsMargins(0, 0, 0, 0)
        inner_l.setSpacing(2)
        self._inner_layout = inner_l

        self._rows: list[PlayerRow] = []
        for name, value, total, score in players:
            row = PlayerRow(
                name=name,
                value=value,
                total=total,
                score=score,
                is_me=player_name_matches(my_name, name),
                name_size=name_size,
                name_color=name_color,
                score_show=score_show,
                score_size=score_size,
                score_color=score_color,
                stat_show=stat_show,
                stat_size=stat_size,
                stat_color=stat_color,
                avg_show=avg_show,
                total_show=total_show,
                border_show=border_show,
                border_size=border_size,
                border_color=border_color,
                bar_color=bar_fg_color,
                bar_bg_show=bar_bg_show,
                bar_bg_size=bar_bg_size,
                bar_bg_color=bar_bg_color,
                bar_fg_show=bar_fg_show,
                bar_fg_size=bar_fg_size,
                outline_show=outline_show,
                outline_size=outline_size,
                outline_color=outline_color,
                row_height=row_height,
            )
            row.set_name_col_color(name_col_color)
            self._rows.append(row)
            inner_l.addWidget(row)

        # Rotated title label at 20% opacity
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

        # ── Local-player stat footer ──────────────────────────────────────────
        self._footer = _LocalPlayerFooter(
            show_dps=True,
            show_hps=(self.prefs_prefix == "heal"),
            show_dtps=True,
            show_crit=True,
            value_size=_pv(f"{g}_footer_value_size", 9),
        )
        self._layout.addWidget(self._footer)

        # State for live updates
        self._my_account_id: str | None = None
        self._show_companions: bool = _pv(f"{g}_show_companions", False)
        self._last_fight: Fight | None = None
        self._player_last_seen_wall: dict[str, float] = {}  # account_id → monotonic
        self._timeout_timer = QTimer(self)
        self._timeout_timer.setInterval(2000)
        self._timeout_timer.timeout.connect(self._prune_timed_out_players)
        self._timeout_timer.start()

    # ── live data API ─────────────────────────────────────────────────────────

    def paintEvent(self, event):
        alpha = getattr(self, "_win_bg_alpha", 0)
        if alpha > 0:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            c = QColor(getattr(self, "_win_bg_color", "#000000"))
            c.setAlpha(max(0, min(255, alpha)))
            painter.setBrush(c)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 4, 4)
        super().paintEvent(event)

    def apply_win_bg_alpha(self, v: int) -> None:
        self._win_bg_alpha = v
        self.update()

    def apply_win_bg_color(self, c: str) -> None:
        self._win_bg_color = c
        self.update()

    def apply_footer_value_size(self, v: int) -> None:
        self._footer.set_value_size(v)
        if self._prefs:
            setattr(self._prefs, f"{self.prefs_prefix}_footer_value_size", v)

    def receive_watcher(self, watcher) -> None:
        """Connect to a LogWatcher instance to receive live updates."""
        watcher.fight_updated.connect(self._on_fight_updated)
        watcher.fight_closed.connect(self._on_fight_closed)
        watcher.session_reset.connect(self._on_session_reset)
        self._watcher = watcher

    def _get_stat_value(
        self, stats: "PlayerFightStats", duration_s: float
    ) -> tuple[float, float]:
        """Return (value, score) for this overlay's stat type."""
        if self.prefs_prefix == "dps":
            return stats.dps(duration_s), stats.damage_out
        if self.prefs_prefix == "def":
            return stats.dtps(duration_s), stats.damage_in
        if self.prefs_prefix == "heal":
            return stats.hps(duration_s), stats.heal_out
        return 0.0, 0.0

    def _on_fight_updated(self, fight: "Fight") -> None:
        """
        Refresh player rows and footer from the current live fight.
        """
        self._last_fight = fight
        p = self._prefs
        my_name = (p.character_name if p and p.character_name else "") or None

        duration_s = fight.duration_s

        # Sync last-seen times from the watcher's per-event tracking so that
        # only players who actually generated log events recently are kept alive.
        watcher_seen = getattr(self._watcher, "player_last_seen", {}) if hasattr(self, "_watcher") else {}
        for aid in fight.player_stats:
            if aid in watcher_seen:
                self._player_last_seen_wall[aid] = watcher_seen[aid]
            elif aid not in self._player_last_seen_wall:
                self._player_last_seen_wall[aid] = time.monotonic()

        now = time.monotonic()
        keep_ms = self._effective_keep_ms()

        def _is_recent(aid: str) -> bool:
            ts = self._player_last_seen_wall.get(aid)
            return ts is not None and (now - ts) * 1000 < keep_ms

        entries: list[tuple[str, str, float, float, float]] = []
        avg_show = getattr(self, "_avg_show", True)
        total_show = getattr(self, "_total_show", True)
        for aid, stats in fight.player_stats.items():
            if not _is_recent(aid):
                continue
            val, raw_total = self._get_stat_value(stats, duration_s)
            if avg_show and total_show:
                score = val + raw_total
            elif avg_show:
                score = val
            else:
                score = raw_total
            if score > 0:
                entries.append((aid, stats.name, val, raw_total, score))
                
        # Include companion stats when enabled
        if getattr(self, "_show_companions", False):
            for aid, stats in getattr(fight, "companion_stats", {}).items():
                if aid in watcher_seen:
                    self._player_last_seen_wall[aid] = watcher_seen[aid]
                elif aid not in self._player_last_seen_wall:
                    self._player_last_seen_wall[aid] = time.monotonic()
                if not _is_recent(aid):
                    continue
                val, raw_total = self._get_stat_value(stats, duration_s)
                if avg_show and total_show:
                    score = val + raw_total
                elif avg_show:
                    score = val
                else:
                    score = raw_total
                if score > 0:
                    entries.append((aid, stats.name, val, raw_total, score))

        # Sort descending by score; hide rows not in active entries
        entries.sort(key=lambda x: x[4], reverse=True)
        active_names = {e[1] for e in entries}
        active_ids = {e[0] for e in entries}
        total_score = sum(e[4] for e in entries) or 1.0

        # Keep recently-seen players visible even when score is currently zero.
        for row in self._rows:
            aid = getattr(row, "_account_id", row._name_lbl.text())
            row.setVisible(row._name_lbl.text() in active_names or _is_recent(aid))

        # Update or add rows, then reorder layout to match sorted order
        inner = getattr(self, "_inner_layout", None)
        row_scores: dict[object, float] = {}
        for aid, name, val, raw_total, score in entries:
            is_me = player_name_matches(my_name, name)
            row = next(
                (
                    r
                    for r in self._rows
                    if getattr(r, "_account_id", r._name_lbl.text()) == aid
                    or r._name_lbl.text() == name
                ),
                None,
            )
            if row is None:
                row = self._add_player_row(name, account_id=aid, is_me=is_me)
            row.setVisible(True)
            row._bar.update_data(val, raw_total, fill_value=score, fill_total=total_score)
            row._score_lbl.setText(fmt_num(score))
            row_scores[row] = score

        # Keep recent-but-inactive rows visible with a zero score so list order
        # always matches the right-side value used for sorting.
        for row in self._rows:
            aid = getattr(row, "_account_id", row._name_lbl.text())
            if aid in active_ids:
                continue
            if row.isVisible():
                row._bar.update_data(0.0, 0.0, fill_value=0.0, fill_total=total_score)
                row._score_lbl.setText(fmt_num(0.0))
            row_scores[row] = 0.0

        # Reorder all visible rows each tick by the same score shown on the right.
        if inner is not None:
            visible_rows = [r for r in self._rows if r.isVisible()]
            visible_rows.sort(key=lambda r: row_scores.get(r, 0.0), reverse=True)
            for row in visible_rows:
                inner.removeWidget(row)
                inner.addWidget(row)

        # Update footer for local player
        if my_name:
            my_stats = next(
                (s for s in fight.player_stats.values() if player_stats_matches(my_name, s)),
                None,
            )
            self._footer.update_stats(my_stats, duration_s)
        self._resize_to_content()

    def _on_fight_closed(self, fight: "Fight") -> None:
        self._on_fight_updated(fight)

    def _on_session_reset(self) -> None:
        p = self._prefs
        my_name = (p.character_name if p and p.character_name else "") if p else None
        for row in list(self._rows):
            if player_name_matches(my_name, row._name_lbl.text()):
                # Keep the local player row; just blank its values
                row._bar.update_data(0.0, 1.0)
                row._score_lbl.setText("")
                continue
            row.setParent(None)
            row.deleteLater()
            self._rows.remove(row)
        self._player_last_seen_wall.clear()
        self._last_fight = None
        # Keep footer visible with last known stats; they'll update on next fight
        self._resize_to_content()

    def _add_player_row(
        self, name: str, account_id: str | None = None, is_me: bool = False
    ) -> "PlayerRow":
        """Dynamically add a new player row to the inner layout."""
        p = self._prefs
        g = self.prefs_prefix

        def _pv(attr, default):
            return getattr(p, attr, default) if p and g else default

        row = PlayerRow(
            name=name,
            is_me=is_me,
            name_size=_pv(f"{g}_name_size", 9),
            name_color=_pv(f"{g}_name_color", "#FFFFFF"),
            score_show=_pv(f"{g}_score_show", True),
            score_size=_pv(f"{g}_score_size", 9),
            score_color=_pv(f"{g}_score_color", "#FFD700"),
            stat_show=_pv(f"{g}_{g}_show", True),
            stat_size=_pv(f"{g}_{g}_size", 8),
            stat_color=_pv(f"{g}_{g}_color", "#FFFFFF"),
            avg_show=_pv(f"{g}_avg_show", True),
            total_show=_pv(f"{g}_total_show", True),
            border_show=_pv(f"{g}_bar_border_show", False),
            border_size=_pv(f"{g}_bar_border_size", 1),
            border_color=_pv(f"{g}_bar_border_color", "#FFFFFF"),
            bar_color=_pv(f"{g}_bar_fg_color", self.bar_color),
            bar_bg_show=_pv(f"{g}_bar_bg_show", True),
            bar_bg_size=_pv(f"{g}_bar_bg_size", 12),
            bar_bg_color=_pv(f"{g}_bar_bg_color", "#FFFFFF"),
            bar_fg_show=_pv(f"{g}_bar_fg_show", True),
            bar_fg_size=_pv(f"{g}_bar_fg_size", 71),
            outline_show=_pv(f"{g}_outline_show", True),
            outline_size=_pv(f"{g}_outline_size", 1),
            outline_color=_pv(f"{g}_outline_color", "#000000"),
            row_height=_pv(f"{g}_row_height", 24),
        )
        row._account_id = account_id or name
        row.set_name_col_color(_pv(f"{g}_name_col_color", "transparent"))
        # Insert before the footer — find the container widget's inner layout
        # The inner widget is the second child of the container's HBoxLayout.
        # We stored it as self._inner_layout in setup.
        if hasattr(self, "_inner_layout"):
            self._inner_layout.addWidget(row)
        self._rows.append(row)
        return row

    def _prune_timed_out_players(self) -> None:
        """Remove rows for players we haven't seen in PLAYER_TIMEOUT_MS."""
        now = time.monotonic()
        keep_ms = self._effective_keep_ms()
        to_remove = [
            aid
            for aid, ts in self._player_last_seen_wall.items()
            if (now - ts) * 1000 >= keep_ms
        ]
        if not to_remove:
            return
        # Map name → aid so we can find matching rows
        p = self._prefs
        my_name = (p.character_name if p and p.character_name else "") if p else None
        for row in list(self._rows):
            name = row._name_lbl.text()
            # Never prune the local player row
            if name == my_name:
                continue
            # If this row's player has timed out, remove it
            # We stored account_id on the row during _add_player_row; fall back to name lookup
            aid = getattr(row, "_account_id", name)
            if aid in to_remove:
                row.setParent(None)
                row.deleteLater()
                self._rows.remove(row)
                self._player_last_seen_wall.pop(aid, None)
        if to_remove:
            self._resize_to_content()

    def _display_keep_ms(self) -> int:
        p = self._prefs
        keep_s = int(getattr(p, "display_keep_seconds", 120) if p else 120)
        keep_s = max(30, min(600, keep_s))
        return keep_s * 1000

    def _effective_keep_ms(self) -> int:
        from app.log_watcher import PLAYER_TIMEOUT_MS

        return max(PLAYER_TIMEOUT_MS, self._display_keep_ms())

    # ── bulk apply methods (called by OverlayMasterWindow) ───────────────────
    def _apply_to_rows(self, method_name: str, value) -> None:
        for row in getattr(self, "_rows", []):
            fn = getattr(row, method_name, None)
            if fn:
                fn(value)

    def apply_name_size(self, v: int) -> None:
        self._apply_to_rows("set_name_size", v)

    def apply_name_color(self, c: str) -> None:
        self._apply_to_rows("set_name_color", c)

    def apply_name_col_color(self, c: str) -> None:
        self._apply_to_rows("set_name_col_color", c)

    def apply_win_width(self, v: int) -> None:
        self._min_content_width = v
        self._resize_to_content()

    def apply_stat_show(self, b: bool) -> None:
        self._apply_to_rows("set_stat_show", b)

    def apply_stat_size(self, v: int) -> None:
        self._apply_to_rows("set_stat_size", v)

    def apply_stat_color(self, c: str) -> None:
        self._apply_to_rows("set_stat_color", c)

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

    def apply_bar_fg_show(self, b: bool) -> None:
        self._apply_to_rows("set_bar_fg_show", b)

    def apply_bar_fg_size(self, v: int) -> None:
        self._apply_to_rows("set_bar_fg_size", v)

    def apply_bar_fg_color(self, c: str) -> None:
        self._apply_to_rows("set_bar_fg_color", c)

    def apply_score_show(self, b: bool) -> None:
        self._apply_to_rows("set_score_show", b)

    def apply_score_size(self, v: int) -> None:
        self._apply_to_rows("set_score_size", v)

    def apply_score_color(self, c: str) -> None:
        self._apply_to_rows("set_score_color", c)

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

    def apply_character_name(self, name: str) -> None:
        my_name = (name or "").strip() or None
        for row in getattr(self, "_rows", []):
            row.set_is_me(player_name_matches(my_name, row._name_lbl.text()))

        watcher = getattr(self, "_watcher", None)
        fight = getattr(watcher, "current_fight", None) if watcher is not None else None
        if fight is None and watcher is not None and watcher.session.fights:
            fight = watcher.session.fights[-1]
        if fight is None:
            fight = getattr(self, "_last_fight", None)

        if fight is not None:
            self._on_fight_updated(fight)
        else:
            self._footer.update_stats(None, 1.0)
            self._resize_to_content()



