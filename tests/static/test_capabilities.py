"""Each adapter's capability record names every `MINT` method the adapter implements
and no other, as the Protocol's own method objects. ADR-0019 PC-D28.

Why: the record is what the layer above trusts without asking how, so a method the
adapter honours `parents=` for and leaves out, or one it names and does not implement,
is a contract defect the engine run would surface late. Read from the Protocols, so a
method declared `MINT` later lands here as a failing test until its adapter names it.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable

import pytest

from ag.adapters.arcpy import capabilities as arcpy_capabilities
from ag.adapters.arcpy.cartographic_ops import ArcpyCartographicOps
from ag.adapters.arcpy.geometry_ops import ArcpyGeometryOps
from ag.adapters.arcpy.session import ArcpySession
from ag.adapters.arcpy.table_ops import ArcpyTableOps
from ag.adapters.fakes.memory import capabilities as memory_capabilities
from ag.adapters.fakes.memory.cartographic_ops import MemoryCartographicOps
from ag.adapters.fakes.memory.geometry_ops import MemoryGeometryOps
from ag.adapters.fakes.memory.store import MemoryStore
from ag.adapters.fakes.memory.table_ops import MemoryTableOps
from ag.ports.capabilities import AdapterCapabilities, PortMethod
from ag.ports.cartographic_ops import CartographicOps
from ag.ports.geometry_ops import GeometryOps
from ag.ports.row_shape import Ids, declared_rows
from ag.ports.table_ops import TableOps
from tests.support.fake_arcpy import FakeEngine

PORTS: tuple[type, ...] = (GeometryOps, TableOps, CartographicOps)

ADAPTERS: dict[str, tuple[Callable[[], AdapterCapabilities], tuple[type, ...]]] = {
    "arcpy": (
        lambda: arcpy_capabilities(session=ArcpySession(engine=FakeEngine())),
        (ArcpyGeometryOps, ArcpyTableOps, ArcpyCartographicOps),
    ),
    "memory": (
        lambda: memory_capabilities(store=MemoryStore()),
        (MemoryGeometryOps, MemoryTableOps, MemoryCartographicOps),
    ),
}
"""Adapter to its record at construction and its composed classes."""


def mint_methods(protocol: type) -> set[PortMethod]:
    """The Protocol's methods whose row shape declares `MINT` on any output."""
    found: set[PortMethod] = set()
    for name, member in vars(protocol).items():
        if not inspect.isfunction(member) or name.startswith("_"):
            continue
        rows = declared_rows(member)
        if rows and any(r.ids is Ids.MINT for r in rows.values()):
            found.add(member)
    return found


def implemented(composed: tuple[type, ...], method: PortMethod) -> bool:
    return any(
        method.__name__ in vars(base) for cls in composed for base in cls.__mro__
    )


@pytest.mark.parametrize("adapter", sorted(ADAPTERS), ids=sorted(ADAPTERS))
def test_the_record_names_every_mint_method_the_adapter_implements_and_no_other(
    adapter: str,
) -> None:
    build, composed = ADAPTERS[adapter]
    expected = {
        m for port in PORTS for m in mint_methods(port) if implemented(composed, m)
    }
    assert build().parents_for == expected


def test_the_mint_methods_are_seen() -> None:
    assert {m.__name__ for m in mint_methods(GeometryOps)} == {"explode_multipart"}
    assert mint_methods(TableOps) == set()
