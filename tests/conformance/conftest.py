"""The adapter fixture of the conformance suite: one `Adapter` per parameter.

What: `Adapter`, what a conformance case needs from an adapter beyond its port classes:
a handle in the adapter's workspace, a case seeded with the native indices it got, a
non-dense seeding, and a dataset's native indices read back. `adapter` yields the
in-memory adapter always and the ArcPy adapter under the `arcpy` marker, each with a
fresh store or a fresh file geodatabase per test.

How: the ArcPy builders are imported inside the fixture body, never at module level,
since collection imports this module where there is no ArcPy. Native indices are read
outside the port on purpose: no port method exposes them, and the cases assert the port's
contract about them. The non-dense seeding differs by adapter and the assertion does not:
the engine's indices get a gap through deleted rows; the in-memory store has no delete
and takes a contiguous range from one counter, so a throwaway write first moves the
case's indices above one. Either way the indices are not the rows' positions, which is
what the case needs to tell a pre-call index from a position or a renumbering.
"""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import pytest

from ag.adapters.fakes.memory import capabilities as memory_capabilities
from ag.adapters.fakes.memory.geometry_ops import MemoryGeometryOps
from ag.adapters.fakes.memory.store import MemoryStore
from ag.adapters.fakes.memory.table_ops import MemoryTableOps
from ag.core.handles import ScratchHandle
from ag.core.types import DataType
from ag.ports.capabilities import AdapterCapabilities
from ag.ports.geometry_ops import GeometryOps
from ag.ports.table_ops import TableOps
from tests.support import memory
from tests.support.cases import DatasetCase, Seeded


class Adapter(Protocol):
    """One adapter under test, with the test-side access the cases need."""

    @property
    def geometry_ops(self) -> GeometryOps: ...
    @property
    def table_ops(self) -> TableOps: ...
    @property
    def capabilities(self) -> AdapterCapabilities: ...
    def handle(
        self, name: str, data_type: DataType = DataType.FEATURE_CLASS
    ) -> ScratchHandle: ...
    def seed(self, case: DatasetCase) -> Seeded: ...
    def seed_non_dense(self, case: DatasetCase, *, drop: Collection[int]) -> Seeded:
        """`case` without the rows at the 1-based positions in `drop`, seeded so that
        the remaining rows' native indices are not their positions."""
        ...

    def indices(self, handle: ScratchHandle) -> tuple[int, ...]: ...


@dataclass(frozen=True)
class _Memory:
    store: MemoryStore

    @property
    def geometry_ops(self) -> GeometryOps:
        return MemoryGeometryOps(store=self.store)

    @property
    def table_ops(self) -> TableOps:
        return MemoryTableOps(store=self.store)

    @property
    def capabilities(self) -> AdapterCapabilities:
        return memory_capabilities(store=self.store)

    def handle(
        self, name: str, data_type: DataType = DataType.FEATURE_CLASS
    ) -> ScratchHandle:
        return memory.memory_handle(name, data_type)

    def seed(self, case: DatasetCase) -> Seeded:
        return memory.seed(self.store, case)

    def seed_non_dense(self, case: DatasetCase, *, drop: Collection[int]) -> Seeded:
        memory.seed(self.store, DatasetCase("throwaway", case.schema, case.rows))
        kept = tuple(
            row
            for position, row in enumerate(case.rows, start=1)
            if position not in drop
        )
        return memory.seed(self.store, DatasetCase(case.name, case.schema, kept))

    def indices(self, handle: ScratchHandle) -> tuple[int, ...]:
        return tuple(self.store.read(handle).rows)


def _arcpy(directory: Path) -> Adapter:
    """The ArcPy adapter on a fresh file geodatabase under `directory`."""
    from ag.adapters.arcpy import capabilities as arcpy_capabilities
    from ag.adapters.arcpy.geometry_ops import ArcpyGeometryOps
    from ag.adapters.arcpy.session import ArcpySession, open_session
    from ag.adapters.arcpy.table_ops import ArcpyTableOps
    from tests.support import gdb_cases
    from tests.support.arcpy import gdb

    @dataclass(frozen=True)
    class Arcpy:
        session: ArcpySession
        workspace: str

        @property
        def geometry_ops(self) -> GeometryOps:
            return ArcpyGeometryOps(session=self.session)

        @property
        def table_ops(self) -> TableOps:
            return ArcpyTableOps(session=self.session)

        @property
        def capabilities(self) -> AdapterCapabilities:
            return arcpy_capabilities(session=self.session)

        def handle(
            self, name: str, data_type: DataType = DataType.FEATURE_CLASS
        ) -> ScratchHandle:
            return gdb_cases.handle_at(self.workspace, name, data_type)

        def seed(self, case: DatasetCase) -> Seeded:
            return gdb_cases.seed_case(
                self.session, workspace=self.workspace, case=case
            )

        def seed_non_dense(self, case: DatasetCase, *, drop: Collection[int]) -> Seeded:
            seeded = self.seed(case)
            dropped = {seeded.index_of(position) for position in drop}
            gdb.delete_rows(self.session, path=str(seeded.handle.path), indices=dropped)
            kept = tuple(index for index in seeded.indices if index not in dropped)
            return Seeded(handle=seeded.handle, indices=kept)

        def indices(self, handle: ScratchHandle) -> tuple[int, ...]:
            return gdb.indices(self.session, path=str(handle.path))

    session = open_session()
    workspace = gdb.file_gdb(session, directory=str(directory), name="conformance")
    return Arcpy(session=session, workspace=workspace)


@pytest.fixture(
    params=[
        pytest.param("memory", id="memory"),
        pytest.param("arcpy", id="arcpy", marks=pytest.mark.arcpy),
    ]
)
def adapter(request: pytest.FixtureRequest, tmp_path: Path) -> Adapter:
    """The adapter under test: the in-memory one always, ArcPy under the marker."""
    if request.param == "memory":
        return _Memory(store=MemoryStore())
    return _arcpy(tmp_path)
