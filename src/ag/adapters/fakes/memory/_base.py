"""`MemoryPortBase`, the one class of the in-memory adapter that holds the store.

Every group class subclasses it, so `self._store` is typed in each, and it is the only
class in the adapter that assigns an instance attribute: the group classes hold Protocol
methods and no state.
"""

from __future__ import annotations

from ag.adapters.fakes.memory.store import MemoryStore


class MemoryPortBase:
    """Holds the store every port class of one fake shares."""

    def __init__(self, *, store: MemoryStore) -> None:
        self._store = store
