"""The ArcPy implementation of `TableOps`, one module per method group.

Membership test: a module here holds one group class with Protocol methods of `TableOps`
only, plus module-level private helpers that take the session as an argument. `__init__`
composes the groups into `ArcpyTableOps` with an empty body, and its conformance is the
assignment under `TYPE_CHECKING` below. Group modules never import each other.
ADR-0018 AR-D14.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ag.adapters.arcpy.table_ops.row_io import RowIO


class ArcpyTableOps(RowIO):
    """`TableOps` through the ArcPy session, composed from its method groups."""


if TYPE_CHECKING:
    from types import ModuleType

    from ag.adapters.arcpy.session import ArcpySession
    from ag.ports.table_ops import TableOps

    _conformance: TableOps = ArcpyTableOps(
        session=ArcpySession(engine=ModuleType("arcpy"))
    )
