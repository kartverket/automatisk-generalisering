"""The ArcPy implementation of `CartographicOps`, one module per method group.

Membership test: a module here holds one group class with Protocol methods of
`CartographicOps` only, plus module-level private helpers that take the session as an
argument. No group exists yet, so the composed class is the base alone; its conformance
is the assignment under `TYPE_CHECKING` below. ADR-0018 AR-D14.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ag.adapters.arcpy._base import ArcpyPortBase


class ArcpyCartographicOps(ArcpyPortBase):
    """`CartographicOps` through the ArcPy session; no methods until the port has one."""


if TYPE_CHECKING:
    from types import ModuleType

    from ag.adapters.arcpy.session import ArcpySession
    from ag.ports.cartographic_ops import CartographicOps

    _conformance: CartographicOps = ArcpyCartographicOps(
        session=ArcpySession(engine=ModuleType("arcpy"))
    )
