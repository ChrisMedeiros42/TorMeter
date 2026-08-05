"""Persistent storage for Nihilus' Book of Grudges."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.combat_session import Fight
from app.log_parser import APPLY_EFFECT, DAMAGE, EVENT, HEAL, NPC, is_friendly_companion, is_friendly_player
from app.overlays_shared.player_match import player_stats_matches

_DATA_PATH = Path(__file__).resolve().parents[1] / "config" / "data" / "Grudges.json"


@dataclass(slots=True)
class EnemyGrudgeRecord:
    key: str
    name: str
    encounters: int = 0
    kills: int = 0
    deaths: int = 0
    damage_out: int = 0
    damage_in: int = 0
    hits: int = 0
    crit_hits: int = 0
    ttk_total_ms: int = 0
    ttk_samples: int = 0
    fastest_ttk_ms: int = 0
    slowest_ttk_ms: int = 0
    first_seen_ms: int = 0
    last_seen_ms: int = 0
    observed_ids: list[str] = field(default_factory=list)

    def absorb(self, *, name: str, enemy_id: str | None = None) -> None:
        if name and not self.name:
            self.name = name
        if enemy_id and enemy_id not in self.observed_ids:
            self.observed_ids.append(enemy_id)

    @property
    def avg_ttk_ms(self) -> float:
        return self.ttk_total_ms / self.ttk_samples if self.ttk_samples else 0.0

    @property
    def crit_rate(self) -> float:
        return self.crit_hits / self.hits if self.hits else 0.0

    @property
    def kill_rate(self) -> float:
        return self.kills / self.encounters if self.encounters else 0.0

    @property
    def avg_damage_out(self) -> float:
        return self.damage_out / self.encounters if self.encounters else 0.0

    @property
    def avg_damage_in(self) -> float:
        return self.damage_in / self.encounters if self.encounters else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "encounters": self.encounters,
            "kills": self.kills,
            "deaths": self.deaths,
            "damage_out": self.damage_out,
            "damage_in": self.damage_in,
            "hits": self.hits,
            "crit_hits": self.crit_hits,
            "ttk_total_ms": self.ttk_total_ms,
            "ttk_samples": self.ttk_samples,
            "fastest_ttk_ms": self.fastest_ttk_ms,
            "slowest_ttk_ms": self.slowest_ttk_ms,
            "first_seen_ms": self.first_seen_ms,
            "last_seen_ms": self.last_seen_ms,
            "observed_ids": list(self.observed_ids),
        }

    @classmethod
    def from_dict(cls, key: str, payload: dict[str, Any]) -> "EnemyGrudgeRecord":
        record = cls(
            key=key,
            name=str(payload.get("name", key) or key),
            encounters=int(payload.get("encounters", 0) or 0),
            kills=int(payload.get("kills", 0) or 0),
            deaths=int(payload.get("deaths", 0) or 0),
            damage_out=int(payload.get("damage_out", 0) or 0),
            damage_in=int(payload.get("damage_in", 0) or 0),
            hits=int(payload.get("hits", 0) or 0),
            crit_hits=int(payload.get("crit_hits", 0) or 0),
            ttk_total_ms=int(payload.get("ttk_total_ms", 0) or 0),
            ttk_samples=int(payload.get("ttk_samples", 0) or 0),
            fastest_ttk_ms=int(payload.get("fastest_ttk_ms", 0) or 0),
            slowest_ttk_ms=int(payload.get("slowest_ttk_ms", 0) or 0),
            first_seen_ms=int(payload.get("first_seen_ms", 0) or 0),
            last_seen_ms=int(payload.get("last_seen_ms", 0) or 0),
            observed_ids=[str(v) for v in payload.get("observed_ids", []) if v],
        )
        return record


@dataclass(slots=True)
class CharacterGrudgeBook:
    character_name: str
    updated_at_ms: int = 0
    fights: int = 0
    kills: int = 0
    enemies: dict[str, EnemyGrudgeRecord] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "character_name": self.character_name,
            "updated_at_ms": self.updated_at_ms,
            "fights": self.fights,
            "kills": self.kills,
            "enemies": {k: v.to_dict() for k, v in self.enemies.items()},
        }

    @classmethod
    def from_dict(cls, character_name: str, payload: dict[str, Any]) -> "CharacterGrudgeBook":
        enemies_raw = payload.get("enemies", {}) or {}
        enemies = {
            key: EnemyGrudgeRecord.from_dict(key, enemy_payload)
            for key, enemy_payload in enemies_raw.items()
            if isinstance(enemy_payload, dict)
        }
        return cls(
            character_name=character_name,
            updated_at_ms=int(payload.get("updated_at_ms", 0) or 0),
            fights=int(payload.get("fights", 0) or 0),
            kills=int(payload.get("kills", 0) or 0),
            enemies=enemies,
        )


class GrudgesStore:
    def __init__(self, path: Path | None = None):
        self._path = path or _DATA_PATH
        self._version = 1
        self._books: dict[str, CharacterGrudgeBook] = {}
        self._load()

    @property
    def path(self) -> Path:
        return self._path

    def _load(self) -> None:
        self._books = {}
        if not self._path.exists():
            return
        try:
            raw_text = self._path.read_text(encoding="utf-8").strip()
        except OSError:
            return
        if not raw_text:
            return
        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError:
            return
        self._version = int(payload.get("version", 1) or 1)
        characters = payload.get("characters", {}) or {}
        if isinstance(characters, dict):
            for character_name, book_payload in characters.items():
                if isinstance(book_payload, dict):
                    self._books[character_name] = CharacterGrudgeBook.from_dict(
                        character_name, book_payload
                    )

    def save(self) -> None:
        payload = {
            "version": self._version,
            "characters": {name: book.to_dict() for name, book in self._books.items()},
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def get_book(self, character_name: str) -> CharacterGrudgeBook | None:
        return self._books.get(character_name)

    def character_names(self) -> list[str]:
        return sorted(self._books.keys(), key=str.casefold)

    def clear_character(self, character_name: str, *, persist: bool = True) -> bool:
        key = (character_name or "").strip()
        if not key:
            return False
        removed = self._books.pop(key, None) is not None
        if removed and persist:
            self.save()
        return removed

    def clear_all(self, *, persist: bool = True) -> None:
        self._books.clear()
        if persist:
            self.save()

    def import_legacy_character(self, source_name: str, target_name: str, *, persist: bool = True) -> bool:
        source = (source_name or "").strip()
        target = (target_name or "").strip()
        if not source or not target or source.casefold() == target.casefold():
            return False

        source_book = self._books.get(source)
        if source_book is None:
            return False

        target_book = self._books.get(target)
        if target_book is None:
            source_book.character_name = target
            self._books[target] = source_book
        else:
            target_book.updated_at_ms = max(target_book.updated_at_ms, source_book.updated_at_ms)
            target_book.fights += source_book.fights
            target_book.kills += source_book.kills
            for enemy_key, source_record in source_book.enemies.items():
                target_record = target_book.enemies.get(enemy_key)
                if target_record is None:
                    target_book.enemies[enemy_key] = source_record
                    continue
                target_record.encounters += source_record.encounters
                target_record.kills += source_record.kills
                target_record.deaths += source_record.deaths
                target_record.damage_out += source_record.damage_out
                target_record.damage_in += source_record.damage_in
                target_record.hits += source_record.hits
                target_record.crit_hits += source_record.crit_hits
                target_record.ttk_total_ms += source_record.ttk_total_ms
                target_record.ttk_samples += source_record.ttk_samples
                target_record.fastest_ttk_ms = (
                    source_record.fastest_ttk_ms
                    if target_record.fastest_ttk_ms <= 0
                    else min(target_record.fastest_ttk_ms, source_record.fastest_ttk_ms or target_record.fastest_ttk_ms)
                )
                target_record.slowest_ttk_ms = max(target_record.slowest_ttk_ms, source_record.slowest_ttk_ms)
                target_record.first_seen_ms = (
                    source_record.first_seen_ms
                    if target_record.first_seen_ms <= 0
                    else min(target_record.first_seen_ms, source_record.first_seen_ms or target_record.first_seen_ms)
                )
                target_record.last_seen_ms = max(target_record.last_seen_ms, source_record.last_seen_ms)
                for enemy_id in source_record.observed_ids:
                    if enemy_id not in target_record.observed_ids:
                        target_record.observed_ids.append(enemy_id)

        if source.casefold() != target.casefold():
            self._books.pop(source, None)
        if persist:
            self.save()
        return True

    def _enemy_key(self, entity) -> str | None:
        if entity is None or getattr(entity, "kind", None) != NPC:
            return None
        return (getattr(entity, "name", "") or "").strip() or None

    def _friendly_match(self, character_name: str, fight: Fight) -> bool:
        return any(
            player_stats_matches(character_name, stats)
            for stats in fight.player_stats.values()
        )

    def record_fight(self, character_name: str, fight: Fight) -> bool:
        character_name = (character_name or "").strip()
        if not character_name or character_name.casefold() == "me":
            return False
        if not fight.player_stats or not self._friendly_match(character_name, fight):
            return False

        book = self._books.setdefault(character_name, CharacterGrudgeBook(character_name))
        book.fights += 1
        book.updated_at_ms = fight.end_ms

        encounter_seen: set[str] = set()
        first_seen_ms: dict[str, int] = {}
        kill_recorded: set[str] = set()

        def _mark_seen(enemy_key: str, enemy_name: str, enemy_id: str | None, ts: int) -> None:
            encounter_seen.add(enemy_key)
            first_seen_ms.setdefault(enemy_key, ts)
            record = book.enemies.get(enemy_key)
            if record is None:
                record = EnemyGrudgeRecord(key=enemy_key, name=enemy_name)
                book.enemies[enemy_key] = record
            record.absorb(name=enemy_name, enemy_id=enemy_id)
            if record.first_seen_ms <= 0:
                record.first_seen_ms = ts
            record.last_seen_ms = max(record.last_seen_ms, ts)

        for event in sorted(fight.events, key=lambda e: e.timestamp_ms):
            src = event.source
            tgt = event.target
            ts = event.timestamp_ms
            src_key = self._enemy_key(src)
            tgt_key = self._enemy_key(tgt)

            if event.effect_type == APPLY_EFFECT and event.effect_name == DAMAGE:
                if (is_friendly_player(src) or is_friendly_companion(src)) and tgt_key is not None:
                    _mark_seen(tgt_key, tgt.name, tgt.account_id, ts)
                    record = book.enemies[tgt_key]
                    record.damage_out += event.effective_amount
                    if event.effective_amount > 0:
                        record.hits += 1
                        if event.is_crit:
                            record.crit_hits += 1
                elif src_key is not None and (is_friendly_player(tgt) or is_friendly_companion(tgt)):
                    _mark_seen(src_key, src.name, src.account_id, ts)
                    record = book.enemies[src_key]
                    record.damage_in += event.effective_amount

            elif event.effect_type == EVENT and event.effect_name == "Death":
                if tgt_key is not None and (is_friendly_player(src) or is_friendly_companion(src)):
                    if tgt_key not in kill_recorded:
                        _mark_seen(tgt_key, tgt.name, tgt.account_id, ts)
                        record = book.enemies[tgt_key]
                        record.kills += 1
                        if tgt_key in first_seen_ms:
                            ttk_ms = max(0, ts - first_seen_ms[tgt_key])
                            record.ttk_total_ms += ttk_ms
                            record.ttk_samples += 1
                            if record.fastest_ttk_ms <= 0 or ttk_ms < record.fastest_ttk_ms:
                                record.fastest_ttk_ms = ttk_ms
                            if ttk_ms > record.slowest_ttk_ms:
                                record.slowest_ttk_ms = ttk_ms
                        kill_recorded.add(tgt_key)
                elif src_key is not None and (is_friendly_player(tgt) or is_friendly_companion(tgt)):
                    _mark_seen(src_key, src.name, src.account_id, ts)
                    record = book.enemies[src_key]
                    record.deaths += 1

        for enemy_key in encounter_seen:
            record = book.enemies[enemy_key]
            record.encounters += 1

        book.kills += len(kill_recorded)
        self.save()
        return True

    def snapshot(self, character_name: str) -> CharacterGrudgeBook | None:
        return self._books.get(character_name)
