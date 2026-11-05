"""The ArcPy adapter: the session, the base class and one package per port.

The root holds `session.py`, `_base.py`, `support/` and the port packages, and nothing
else. Membership test: the code needs ArcPy. Any module here may import `arcpy` for the
non-tool names declared in `stubs/arcpy_constrained/`, and uses them inside the
session's guard; tools, `arcpy.env` and vendor exceptions are reached through
`session.py` only. A module imports `arcpy` inside the function that reaches it, under
the guard, so the module imports without the engine and the unit tests stand a fake in
through `sys.modules`. `capabilities` is what the adapter states about itself at
construction. ADR-0019 PC-D28.
"""

from __future__ import annotations

from ag.adapters.arcpy.session import ArcpySession
from ag.ports.capabilities import AdapterCapabilities
from ag.ports.geometry_ops import GeometryOps


def capabilities(*, session: ArcpySession) -> AdapterCapabilities:
    """The record for one session: `explode_multipart` honours `parents=` from the
    engine's own reference field. The session is where a later probe runs."""
    return AdapterCapabilities(parents_for=frozenset({GeometryOps.explode_multipart}))
