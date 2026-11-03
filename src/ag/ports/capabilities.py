"""The capability record: what an adapter states about itself at construction.

What: `AdapterCapabilities`, the set of `MINT` port methods for which the adapter
honours `parents=`, held as the Protocol's own method objects; `PortMethod`, the type of
one such member.

Why: the layer above asks for parents and does not care how they are produced, so the
record names methods and never mechanisms, and the composition root receives it as data
rather than probing an engine. The members are the Protocol's function objects, not
their names, so a renamed method is a type error at the record and not a string that
drifts; a consumer tests membership with the method it is about to call. The record
lives under `ports/` because adapters publish it and may not import the layer that reads
it. ADR-0019 PC-D28.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeAlias

PortMethod: TypeAlias = Callable[..., object]
"""A method read from a port Protocol class, such as `GeometryOps.explode_multipart`."""


@dataclass(frozen=True, slots=True)
class AdapterCapabilities:
    """What an adapter states about itself at construction: methods, never mechanisms."""

    parents_for: frozenset[PortMethod]
    """The `MINT` methods for which `parents=` is honoured; a request for parents on any
    other raises `ParentsUnavailableError`, never an empty table. ADR-0019 PC-D29."""
