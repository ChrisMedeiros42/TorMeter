# ◢▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧◣
# ▧ - Lunar Edge Games                                          ▧
# ▧ - Tor Meter                                                 ▧
# ▧▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▧
# ▧ - Module: App                                               ▧
# ▧ - Sub-Module: Overlays                                      ▧
# ◥▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧◤


"""Compatibility shim for refactored overlay modules."""

from app.overlays_core import (
    DefenseWindow,
    DpsWindow,
    HealWindow,
    OverlayMasterWindow,
    NihilusBookOfGrudgesOverlay,
    PlayerRow,
    SummaryWindow,
    _AutoScrollArea,
    _ColorButton,
    _OutlineLabel,
    _RotatedLabel,
    _SectionFrame,
    _add_grid_row,
    _make_section_inner,
    _make_show_hide_wrapper,
    _section,
)
from app.overlays_shared import _ComboArrowNav, _LocalPlayerFooter, _PlayerFilterButton, _Separator

__all__ = [
    "OverlayMasterWindow",
    "SummaryWindow",
    "DpsWindow",
    "DefenseWindow",
    "HealWindow",
    "NihilusBookOfGrudgesOverlay",
    "PlayerRow",
    "_RotatedLabel",
    "_SectionFrame",
    "_AutoScrollArea",
    "_ColorButton",
    "_OutlineLabel",
    "_add_grid_row",
    "_make_section_inner",
    "_make_show_hide_wrapper",
    "_section",
    "_Separator",
    "_ComboArrowNav",
    "_PlayerFilterButton",
    "_LocalPlayerFooter",
]
