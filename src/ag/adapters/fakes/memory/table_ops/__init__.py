"""The in-memory implementation of `TableOps`, one module per method group.

Membership test: a module here mirrors the ArcPy group module of the same name and holds
one group class with Protocol methods only; helpers are module-level functions that take
the store as an argument. The composed class has an empty body, and its conformance is
the assignment under `TYPE_CHECKING` below. ADR-0018 AR-D14.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ag.adapters.fakes.memory.table_ops.row_io import RowIO


class MemoryTableOps(RowIO):
    """`TableOps` over the in-memory store, composed from its method groups."""


if TYPE_CHECKING:
    from ag.adapters.fakes.memory.store import MemoryStore
    from ag.ports.table_ops import TableOps

    _conformance: TableOps = MemoryTableOps(store=MemoryStore())
