"""The in-memory implementation of `CartographicOps`, one module per method group.

Membership test: a module here mirrors the ArcPy group module of the same name and holds
one group class with Protocol methods only; helpers are module-level functions that take
the store as an argument. No group exists yet, so the composed class is the base alone;
its conformance is the assignment under `TYPE_CHECKING` below. ADR-0018 AR-D14.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ag.adapters.fakes.memory._base import MemoryPortBase


class MemoryCartographicOps(MemoryPortBase):
    """`CartographicOps` over the in-memory store; no methods until the port has one."""


if TYPE_CHECKING:
    from ag.adapters.fakes.memory.store import MemoryStore
    from ag.ports.cartographic_ops import CartographicOps

    _conformance: CartographicOps = MemoryCartographicOps(store=MemoryStore())
