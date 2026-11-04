"""The in-memory adapter, in the same package shape as the ArcPy adapter.

The root holds `store.py`, `_base.py`, `support/` and the port packages, and nothing
else. Membership test: the code reads and writes rows only through the `MemoryStore` it
is handed, and computes no geometry. `capabilities` is what the adapter states about
itself at construction. ADR-0019 PC-D28.
"""

from __future__ import annotations

from ag.adapters.fakes.memory.store import MemoryStore
from ag.ports.capabilities import AdapterCapabilities
from ag.ports.geometry_ops import GeometryOps


def capabilities(*, store: MemoryStore) -> AdapterCapabilities:
    """The record for one fake: `explode_multipart` honours `parents=` over the store."""
    return AdapterCapabilities(parents_for=frozenset({GeometryOps.explode_multipart}))
