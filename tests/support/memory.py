"""Seeding the in-memory store from the engine-neutral cases.

What: `memory_handle`, a handle materialised to a `memory:/` path; `seed`, which writes a
case to a store and returns a `Seeded` holding the handle and the native indices the
store assigned, so a test maps a case's 1-based positions through `index_of` instead of
assuming the numbering.
"""

from __future__ import annotations

from dataclasses import dataclass

from ag.adapters.fakes.memory.store import MemoryStore
from ag.core.handles import ScratchHandle
from ag.core.types import DataType
from tests.support.cases import DatasetCase

NAMESPACE = "tests.support.memory"


def memory_handle(
    name: str, data_type: DataType = DataType.FEATURE_CLASS
) -> ScratchHandle:
    """A declared-and-materialised handle whose path is `memory:/<name>`."""
    return ScratchHandle(
        name=name, data_type=data_type, namespace=NAMESPACE
    ).materialize(f"memory:/{name}")


@dataclass(frozen=True)
class Seeded:
    """What a seed produced: the handle, and the native index of each row in order."""

    handle: ScratchHandle
    indices: tuple[int, ...]

    def index_of(self, position: int) -> int:
        """The native index of the row at 1-based `position` in the case."""
        return self.indices[position - 1]


def seed(store: MemoryStore, case: DatasetCase) -> Seeded:
    """Writes `case` to `store` under a handle named for it."""
    handle = memory_handle(case.name, case.schema.data_type)
    indices = store.write(handle, schema=case.schema, rows=case.rows)
    return Seeded(handle=handle, indices=indices)
