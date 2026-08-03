# ◢▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧◣
# ▧ - Lunar Edge Games                                          ▧
# ▧ - Tor Meter                                                 ▧
# ▧▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▧
# ▧ - Module: App                                               ▧
# ▧ - Sub-Module: Observable                                    ▧
# ◥▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧◤

"""
Lightweight observable value — single source of truth for shared UI state.
"""

from __future__ import annotations

from typing import Callable, Generic, TypeVar

T = TypeVar("T")


class ObservableValue(Generic[T]):
    """
    A typed value that notifies subscribers when it changes.

    Reentrancy-safe: a ``set()`` call made from within a listener callback is
    silently ignored (the guard prevents infinite loops).
    """

    def __init__(self, value: T) -> None:
        self._value: T = value
        self._listeners: list[Callable[[T], None]] = []
        self._notifying: bool = False

    # ── value access ─────────────────────────────────────────────────────────

    @property
    def value(self) -> T:
        return self._value

    def set(self, new_value: T) -> None:
        """
        Update the value and notify all subscribers (no-op if unchanged or re-entrant).
        """
        if self._value == new_value or self._notifying:
            return
        self._value = new_value
        self._notifying = True
        try:
            for cb in list(self._listeners):
                cb(new_value)
        finally:
            self._notifying = False

    # ── subscription ─────────────────────────────────────────────────────────

    def subscribe(self, cb: Callable[[T], None], call_immediately: bool = False) -> None:
        """
        Register *cb* to be called on every value change.

        If *call_immediately* is True, *cb* is called once right now with the
        current value (useful for initialising UI controls).
        """
        if cb not in self._listeners:
            self._listeners.append(cb)
        if call_immediately:
            cb(self._value)

    def unsubscribe(self, cb: Callable[[T], None]) -> None:
        """
        Remove a previously registered callback.
        """
        self._listeners = [c for c in self._listeners if c is not cb]

    def dispose(self) -> None:
        """
        Clear all listeners (call this when tearing down the observable).
        """
        self._listeners.clear()
