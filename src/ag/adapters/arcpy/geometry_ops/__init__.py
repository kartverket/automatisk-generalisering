"""The ArcPy implementation of `GeometryOps`, one module per method group.

Membership test: a module here holds one group class with Protocol methods of
`GeometryOps` only, plus module-level private helpers that take the session as an
argument. `__init__` composes the groups into `ArcpyGeometryOps` with an empty body, and
its conformance is the assignment under `TYPE_CHECKING` below. Group modules never
import each other. ADR-0018 AR-D14.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ag.adapters.arcpy.geometry_ops.selection import Selection
from ag.adapters.arcpy.geometry_ops.shape import Shape


class ArcpyGeometryOps(Selection, Shape):
    """`GeometryOps` through the ArcPy session, composed from its method groups."""


if TYPE_CHECKING:
    from types import ModuleType

    from ag.adapters.arcpy.session import ArcpySession
    from ag.ports.geometry_ops import GeometryOps

    _conformance: GeometryOps = ArcpyGeometryOps(
        session=ArcpySession(engine=ModuleType("arcpy"))
    )
