"""The selection group of the in-memory `GeometryOps`: `select`.

The predicate is checked once against the input's schema before any row is read, then
evaluated per row in three values; the TRUE rows are written with the input's schema,
so the output gets fresh native indices. ADR-0019 PC-D15.
"""

from __future__ import annotations

from ag.adapters.fakes.memory._base import MemoryPortBase
from ag.adapters.fakes.memory.support.preconditions import distinct_paths
from ag.adapters.fakes.memory.support.predicate_eval import Truth, check, evaluate
from ag.core.handles import ScratchHandle
from ag.ports.predicates import Predicate


class Selection(MemoryPortBase):
    """The selection methods of `GeometryOps`, over the store."""

    def select(
        self, *, input: ScratchHandle, where: Predicate, output: ScratchHandle
    ) -> None:
        """Writes the rows of `input` for which `where` is TRUE to `output`."""
        distinct_paths(handles=(input, output))
        dataset = self._store.read(input)
        check(where, schema=dataset.schema)
        kept = [
            row
            for row in dataset.rows.values()
            if evaluate(where, row=row, schema=dataset.schema) is Truth.TRUE
        ]
        self._store.write(output, schema=dataset.schema, rows=kept)
