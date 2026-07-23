"""Row widgets and scroll container for combat history overlay."""

from __future__ import annotations

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from app.combat_session import CombatSession, Fight, PlayerFightStats
from app.constants import fmt_num
from app.parsing.logs.constants import PLAYER
from app.overlays_shared.player_match import player_stats_matches

from .constants import _FIGHT_BG, _HEADER_STYLE, _LABEL_STYLE, _MAX_LIST_H

class _StatCell(QLabel):
    def __init__(self, text: str = "—", color: str = "white"):
        super().__init__(text)
        self._color = color
        self._font_size = 8
        self._apply_style()
        self.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.setFixedWidth(40)

    def _apply_style(self):
        self.setStyleSheet(
            f"color: {self._color}; font-size: {self._font_size}px; background: transparent;"
        )

    def set_font_size(self, pt: int) -> None:
        self._font_size = pt
        self._apply_style()


def _empty_stats(name: str, account_id: str) -> PlayerFightStats:
    return PlayerFightStats(name=name, account_id=account_id)


def _aggregate_ability_stats(fight: Fight, account_id: str) -> list[tuple[str, PlayerFightStats]]:
    by_ability: dict[str, PlayerFightStats] = {}
    for event in fight.events:
        src = event.source
        if (
            src is None
            or src.kind != PLAYER
            or (src.account_id or src.name) != account_id
            or event.effect_name not in {"Damage", "Heal"}
        ):
            continue

        ability = event.ability_name.strip() or "(unknown)"
        stats = by_ability.get(ability)
        if stats is None:
            stats = _empty_stats(ability, ability)
            by_ability[ability] = stats

        net = max(event.amount - event.mitigation, 0)
        if event.effect_name == "Damage":
            stats.damage_out += net
            if net > 0:
                stats.hit_count += 1
                if event.is_crit:
                    stats.crit_count += 1
        else:
            stats.heal_out += net

    return list(by_ability.items())


class _AbilityDetailRow(QWidget):
    """Indented row showing one ability used by a player in a fight."""

    def __init__(self, ability_name: str, stats: PlayerFightStats, duration_s: float):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(16)
        self._ability_name = ability_name

        layout = QHBoxLayout(self)
        layout.setContentsMargins(32, 0, 4, 0)
        layout.setSpacing(4)

        self._name_lbl = QLabel(ability_name)
        self._name_lbl.setStyleSheet(_LABEL_STYLE)
        self._name_lbl.setFixedWidth(104)
        layout.addWidget(self._name_lbl)

        layout.addStretch(1)

        self._stat_cells: list[_StatCell] = []
        for val, color in (
            (fmt_num(stats.dps(duration_s)), "#FF8C00"),
            (fmt_num(stats.dtps(duration_s)), "#4169E1"),
            (fmt_num(stats.hps(duration_s)), "#32CD32"),
            (f"{stats.crit_rate:.0%}", "#FFD700"),
        ):
            cell = _StatCell(val, color)
            self._stat_cells.append(cell)
            layout.addWidget(cell)

    def set_name_size(self, pt: int) -> None:
        self._name_lbl.setStyleSheet(
            f"color: rgba(255,255,255,185); font-size: {pt}px; background: transparent;"
        )

    def set_stat_size(self, pt: int) -> None:
        for cell in self._stat_cells:
            cell.set_font_size(pt)

    def mousePressEvent(self, event):
        # Keep clicks inside ability rows from toggling the parent fight row.
        event.accept()


class _PlayerDetailRow(QWidget):
    """One player summary row with an optional per-ability breakdown."""

    _SORT_OPTIONS = ("Total", "Damage", "Healing", "Crit")

    @staticmethod
    def _default_sort_mode(stats: PlayerFightStats) -> str:
        if stats.heal_out > stats.damage_out:
            return "Healing"
        if stats.damage_out > stats.heal_out:
            return "Damage"
        return "Total"

    def __init__(self, fight: Fight, stats: PlayerFightStats, is_me: bool = False):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._is_me = is_me
        self._player_name = stats.name
        self._fight = fight
        self._account_id = stats.account_id
        self._expanded = False

        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(14, 0, 4, 0)  # match fight row indent
        self._outer.setSpacing(0)

        hdr = QWidget()
        hdr.setStyleSheet("background: transparent;")
        hdr_l = QHBoxLayout(hdr)
        hdr_l.setContentsMargins(0, 0, 0, 0)
        hdr_l.setSpacing(4)

        self._arrow = QLabel("▶")
        self._arrow.setStyleSheet(
            "color: rgba(255,255,255,120); font-size: 7px; background: transparent;"
        )
        self._arrow.setFixedWidth(10)
        hdr_l.addWidget(self._arrow)

        self._name_lbl = QLabel(stats.name)
        self._name_lbl.setStyleSheet(_LABEL_STYLE)
        self._name_lbl.setFixedWidth(72)
        hdr_l.addWidget(self._name_lbl)

        self._sort_combo = QComboBox()
        self._sort_combo.addItems(self._SORT_OPTIONS)
        self._sort_combo.setFixedWidth(56)
        self._sort_combo.setCurrentText(self._default_sort_mode(stats))
        self._sort_combo.setStyleSheet(
            "QComboBox { color: white; background: rgba(255,255,255,18);"
            " border: 1px solid rgba(255,255,255,45); border-radius: 2px;"
            " font-size: 7px; padding: 0 2px; }"
            "QComboBox::drop-down { width: 10px; border: none; }"
            "QComboBox QAbstractItemView { background: rgba(20,20,30,240);"
            " color: white; selection-background-color: rgba(30,144,255,180);"
            " border: 1px solid rgba(255,255,255,60); font-size: 7px; }"
        )
        self._sort_combo.currentTextChanged.connect(self._rebuild_abilities)
        hdr_l.addWidget(self._sort_combo)

        hdr_l.addStretch(1)

        self._stat_cells: list[_StatCell] = []
        for val, color in self._summary_vals(stats, fight.duration_s):
            cell = _StatCell(val, color)
            self._stat_cells.append(cell)
            hdr_l.addWidget(cell)

        self._outer.addWidget(hdr)

        self._detail = QWidget()
        self._detail.setStyleSheet("background: transparent;")
        detail_l = QVBoxLayout(self._detail)
        detail_l.setContentsMargins(0, 0, 0, 0)
        detail_l.setSpacing(0)

        self._ability_rows: list[_AbilityDetailRow] = []
        self._ability_data = _aggregate_ability_stats(self._fight, self._account_id)
        self._populate_abilities(detail_l)
        self._detail.setVisible(False)
        self._outer.addWidget(self._detail)

    def _sort_ability_items(self) -> list[tuple[str, PlayerFightStats]]:
        mode = self._sort_combo.currentText()

        def _key(item: tuple[str, PlayerFightStats]):
            name, stats = item
            total = stats.damage_out + stats.heal_out
            if mode == "Damage":
                primary = stats.damage_out
            elif mode == "Healing":
                primary = stats.heal_out
            elif mode == "Crit":
                primary = stats.crit_count
            else:
                primary = total
            secondary = stats.damage_out if mode != "Healing" else stats.heal_out
            return (-primary, -secondary, name)

        return sorted(self._ability_data, key=_key)

    def _rebuild_abilities(self, *_ignored) -> None:
        detail_l = self._detail.layout()
        while detail_l.count():
            item = detail_l.takeAt(0)
            if item and item.widget():
                item.widget().setParent(None)
        self._ability_rows.clear()
        self._populate_abilities(detail_l)

    def _summary_vals(self, stats: PlayerFightStats, duration_s: float):
        return [
            (fmt_num(stats.dps(duration_s)), "#FF8C00"),
            (fmt_num(stats.dtps(duration_s)), "#4169E1"),
            (fmt_num(stats.hps(duration_s)), "#32CD32"),
            (f"{stats.crit_rate:.0%}", "#FFD700"),
        ]

    def _populate_abilities(self, layout: QVBoxLayout) -> None:
        for ability_name, stats in self._sort_ability_items():
            row = _AbilityDetailRow(ability_name, stats, self._fight.duration_s)
            self._ability_rows.append(row)
            layout.addWidget(row)

    def set_name_size(self, pt: int) -> None:
        self._name_lbl.setStyleSheet(
            f"color: rgba(255,255,255,200); font-size: {pt}px; background: transparent;"
        )
        for row in self._ability_rows:
            row.set_name_size(pt)

    def set_stat_size(self, pt: int) -> None:
        for cell in self._stat_cells:
            cell.set_font_size(pt)
        for row in self._ability_rows:
            row.set_stat_size(pt)

    def _toggle(self) -> None:
        self._expanded = not self._expanded
        self._detail.setVisible(self._expanded)
        self._arrow.setText("▼" if self._expanded else "▶")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle()
            # Do not bubble to parent _FightRow; that would collapse the fight.
            event.accept()
            return
        super().mousePressEvent(event)

    def paintEvent(self, event):
        if self._is_me:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setBrush(QColor(30, 144, 255, 30))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(self.rect().adjusted(1, 0, -1, 0), 2, 2)
        super().paintEvent(event)


class _FightRow(QWidget):
    """Clickable row for one completed fight; expands to show per-player detail."""

    def __init__(
        self,
        fight: Fight,
        my_name: str | None,
        on_select=None,
        parent=None,
    ):
        super().__init__(parent)
        self._fight = fight
        self._my_name = my_name
        self._on_select = on_select
        self._expanded = False
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(0, 1, 0, 1)
        self._outer.setSpacing(0)

        # Header row
        hdr = QWidget()
        hdr.setStyleSheet("background: transparent;")
        hdr_l = QHBoxLayout(hdr)
        hdr_l.setContentsMargins(14, 2, 4, 2)
        hdr_l.setSpacing(4)

        self._arrow = QLabel("▶")
        self._arrow.setStyleSheet(
            "color: rgba(255,255,255,120); font-size: 7px; background: transparent;"
        )
        self._arrow.setFixedWidth(10)
        hdr_l.addWidget(self._arrow)

        self._name_lbl = QLabel(f"Fight {fight.index}  {fight.duration_s:.0f}s")
        self._name_lbl.setStyleSheet(_HEADER_STYLE)
        hdr_l.addWidget(self._name_lbl, 1)

        self._summary_stat_cells: list[_StatCell] = []
        for val, color in self._summary_vals():
            cell = _StatCell(val, color)
            self._summary_stat_cells.append(cell)
            hdr_l.addWidget(cell)

        self._outer.addWidget(hdr)

        # Detail panel (hidden initially)
        self._detail = QWidget()
        self._detail.setStyleSheet("background: transparent;")
        detail_l = QVBoxLayout(self._detail)
        detail_l.setContentsMargins(0, 0, 0, 0)
        detail_l.setSpacing(0)
        self._detail_rows: list[_PlayerDetailRow] = []
        self._populate_detail(detail_l)
        self._detail.setVisible(False)
        self._outer.addWidget(self._detail)

    def _summary_vals(self):
        """Return [(text, color), ...] for the fight summary columns."""
        dur = self._fight.duration_s
        # Use the selected local player when provided.
        if self._my_name:
            stats = next(
                (
                    s
                    for s in self._fight.player_stats.values()
                    if player_stats_matches(self._my_name, s)
                ),
                None,
            )
        else:
            stats = None
        # Only fall back when no local player is selected (historical browsing).
        if stats is None and not self._my_name and self._fight.player_stats:
            stats = next(iter(self._fight.player_stats.values()))
        if stats:
            return [
                (fmt_num(stats.dps(dur)), "#FF8C00"),
                (fmt_num(stats.dtps(dur)), "#4169E1"),
                (fmt_num(stats.hps(dur)), "#32CD32"),
                (f"{stats.crit_rate:.0%}", "#FFD700"),
            ]
        return [("—", "white")] * 4

    def _populate_detail(self, layout: QVBoxLayout) -> None:
        dur = self._fight.duration_s
        for stats in sorted(
            self._fight.player_stats.values(),
            key=lambda s: s.damage_out,
            reverse=True,
        ):
            is_me = stats.name == self._my_name
            row = _PlayerDetailRow(self._fight, stats, is_me=is_me)
            self._detail_rows.append(row)
            layout.addWidget(row)

    def update_live(self, fight: Fight) -> None:
        """Refresh summary stats from an in-progress fight (called on fight_updated)."""
        self._fight = fight
        self._name_lbl.setText(f"Fight {fight.index}  {fight.duration_s:.0f}s  ◉")
        for cell, (text, _color) in zip(self._summary_stat_cells, self._summary_vals()):
            cell.setText(text)
        if self._expanded:
            self._rebuild_detail()

    def set_my_name(self, my_name: str | None) -> None:
        self._my_name = my_name
        for cell, (text, _color) in zip(self._summary_stat_cells, self._summary_vals()):
            cell.setText(text)
        self._rebuild_detail()

    def _rebuild_detail(self) -> None:
        detail_l = self._detail.layout()
        for row in self._detail_rows:
            row.setParent(None)
        self._detail_rows.clear()
        while detail_l.count():
            item = detail_l.takeAt(0)
            if item and item.widget():
                item.widget().setParent(None)
        self._populate_detail(detail_l)

    def set_name_size(self, pt: int) -> None:
        self._name_lbl.setStyleSheet(
            f"color: white; font-size: {pt}px; font-weight: bold; background: transparent;"
        )
        for row in self._detail_rows:
            row.set_name_size(pt)

    def set_stat_size(self, pt: int) -> None:
        for cell in self._summary_stat_cells:
            cell.set_font_size(pt)
        for row in self._detail_rows:
            row.set_stat_size(pt)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._expanded = not self._expanded
            self._detail.setVisible(self._expanded)
            self._arrow.setText("▼" if self._expanded else "▶")
            if self._on_select:
                self._on_select(self._fight if self._expanded else None)
        super().mousePressEvent(event)

    def update_filter(self, hidden: set[str]) -> None:
        """Show/hide per-player detail rows based on the active filter."""
        layout = self._detail.layout()
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item is None:
                continue
            w = item.widget()
            if isinstance(w, _PlayerDetailRow):
                w.setVisible(getattr(w, "_player_name", None) not in hidden)
        self.updateGeometry()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(_FIGHT_BG)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(self.rect().adjusted(2, 1, -2, -1), 3, 3)
        super().paintEvent(event)


class _SessionRow(QWidget):
    """Top row showing aggregate stats across all fights."""

    def __init__(self, session: CombatSession, my_name: str | None):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(22)
        self._name_lbl: QLabel | None = None
        self._stat_cells: list[_StatCell] = []
        self._build(session, my_name)

    def _build(self, session: CombatSession, my_name: str | None) -> None:
        # Clear existing children
        old = self.layout()
        if old:
            while old.count():
                item = old.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        self._stat_cells = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        self._name_lbl = QLabel(f"Session  ({session.fight_count} fights)")
        self._name_lbl.setStyleSheet(_HEADER_STYLE)
        layout.addWidget(self._name_lbl, 1)

        total_dur = sum(f.duration_s for f in session.fights)
        if my_name:
            agg = session.aggregate_player_stats(
                next(
                    (
                        aid
                        for f in session.fights
                        for aid, s in f.player_stats.items()
                        if player_stats_matches(my_name, s)
                    ),
                    "",
                )
            )
        else:
            agg = None

        # Only fall back when no local player is selected (historical browsing).
        if agg is None and not my_name and session.fights:
            all_aids = {aid for f in session.fights for aid in f.player_stats}
            best_aid = max(
                all_aids,
                key=lambda aid: sum(
                    f.player_stats[aid].damage_out
                    for f in session.fights
                    if aid in f.player_stats
                ),
                default=None,
            )
            if best_aid:
                agg = session.aggregate_player_stats(best_aid)

        if agg and total_dur > 0:
            for val, color in (
                (fmt_num(agg.dps(total_dur)), "#FF8C00"),
                (fmt_num(agg.dtps(total_dur)), "#4169E1"),
                (fmt_num(agg.hps(total_dur)), "#32CD32"),
                (f"{agg.crit_rate:.0%}", "#FFD700"),
            ):
                cell = _StatCell(val, color)
                self._stat_cells.append(cell)
                layout.addWidget(cell)
        else:
            for _ in range(4):
                cell = _StatCell()
                self._stat_cells.append(cell)
                layout.addWidget(cell)

    def set_name_size(self, pt: int) -> None:
        if self._name_lbl:
            self._name_lbl.setStyleSheet(
                f"color: white; font-size: {pt}px; font-weight: bold; background: transparent;"
            )

    def set_stat_size(self, pt: int) -> None:
        for cell in self._stat_cells:
            cell.set_font_size(pt)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(30, 144, 255, 25))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(self.rect().adjusted(1, 0, -1, 0), 3, 3)
        super().paintEvent(event)


class _AutoScrollArea(QScrollArea):
    MAX_H = _MAX_LIST_H

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setWidgetResizable(True)
        self.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { background: rgba(255,255,255,15); width: 6px;"
            " border-radius: 3px; margin: 0; }"
            "QScrollBar::handle:vertical { background: rgba(255,255,255,70);"
            " border-radius: 3px; min-height: 20px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )

    def sizeHint(self) -> QSize:
        w = self.widget()
        if w is None:
            return super().sizeHint()
        inner = w.sizeHint()
        sb_w = self.verticalScrollBar().sizeHint().width()
        h = min(inner.height(), self.MAX_H)
        return QSize(inner.width() + sb_w, h)



