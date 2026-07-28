"""Stat utility helpers for charts overlay."""

from app.combat_session import PlayerFightStats


def _get_stat(stats: PlayerFightStats, stat_label: str, duration_s: float) -> float:
    if stat_label == "DPS":
        return stats.dps(duration_s)
    if stat_label == "HPS":
        return stats.hps(duration_s)
    if stat_label == "DTPS":
        return stats.dtps(duration_s)
    if stat_label == "Damage Out":
        return float(stats.damage_out)
    if stat_label == "Damage In":
        return float(stats.damage_in)
    if stat_label == "Heal Out":
        return float(stats.heal_out)
    return 0.0
