"""The bulk row IO group of the in-memory `TableOps`: `read_rows`.

The rows come back materialised as a tuple, since the store already holds them; a caller
written against the Protocol sees an `Iterable[Row]` and may not rely on that. A field
the dataset does not declare is a contract error. ADR-0019 PC-D22.
"""

from __future__ import annotations

import os
from collections.abc import Iterable

from ag.adapters.fakes.memory._base import MemoryPortBase
from ag.core.errors import ErrorContext
from ag.core.handles import ScratchHandle
from ag.ports.attributes import FieldName
from ag.ports.errors import PortContractError
from ag.ports.table_ops import Row


class RowIO(MemoryPortBase):
    """The bulk row methods of `TableOps`, over the store."""

    def read_rows(
        self, *, input: ScratchHandle, fields: tuple[FieldName, ...]
    ) -> Iterable[Row]:
        """Every row of `input`, with exactly the named fields and its geometry."""
        dataset = self._store.read(input)
        declared = {field.name for field in dataset.schema.fields}
        unknown = [name for name in fields if name not in declared]
        if unknown:
            path = os.fspath(input)
            raise PortContractError(
                f"{unknown} are not fields of {path!r}, whose fields are "
                f"{sorted(declared)}.",
                context=ErrorContext(handle=path),
            )
        return tuple(
            Row(
                attributes={name: row.attributes[name] for name in fields},
                geometry=row.geometry,
            )
            for row in dataset.rows.values()
        )
