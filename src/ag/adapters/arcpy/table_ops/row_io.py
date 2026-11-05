"""The bulk row IO group of the ArcPy `TableOps`: `read_rows`.

How: the fields are checked against the input's described schema before any row is
read, then the rows stream from one cursor under one guard: the guard encloses the
whole iteration, so an engine failure at any row leaves as `EngineError`, and a caller
that stops early closes the cursor through the generator. Each attribute is narrowed to
the port's value union as it is read, the shape through the WKB codec; a value of any
other type is an adapter defect. A date with a sub-second part is refused rather than
truncated, naming the field and the row, since the port carries dates to the whole
second and truncation would change data on a round trip (ADR-0019 PC-D17). An empty
field list reads the native index and drops it, since the engine refuses a cursor with
no field. ADR-0019 PC-D22.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Iterator
from datetime import datetime

from ag.adapters.arcpy._base import ArcpyPortBase
from ag.adapters.arcpy.session import ArcpySession
from ag.adapters.arcpy.support.dataset_schema import (
    OID_TOKEN,
    DescribedDataset,
    declared_field,
    describe,
)
from ag.adapters.arcpy.support.geometry_values import WKB_TOKEN, geometry_from_wkb
from ag.core.handles import ScratchHandle
from ag.ports.attributes import AttributeValue, FieldName
from ag.ports.errors import PortContractError
from ag.ports.table_ops import Row


class RowIO(ArcpyPortBase):
    """The bulk row methods of `TableOps`, through the session."""

    def read_rows(
        self, *, input: ScratchHandle, fields: tuple[FieldName, ...]
    ) -> Iterable[Row]:
        """Every row of `input`, with exactly the named fields and its geometry."""
        dataset = describe(self._session, os.fspath(input))
        for name in fields:
            declared_field(dataset, name)
        return _rows(self._session, dataset=dataset, fields=fields)


def _rows(
    session: ArcpySession, *, dataset: DescribedDataset, fields: tuple[FieldName, ...]
) -> Iterator[Row]:
    """The rows, lazily, under one guard around the cursor and its consumption."""
    crs = dataset.schema.geometry_crs
    tokens: tuple[str, ...] = (*fields, WKB_TOKEN) if crs is not None else fields
    if not tokens:
        tokens = (OID_TOKEN,)
    width = len(fields)
    with session.guard("SearchCursor"):
        import arcpy

        with arcpy.da.SearchCursor(dataset.path, tokens) as cursor:
            for position, values in enumerate(cursor):
                where = f"{dataset.path!r} row {position}"
                attributes = {
                    name: _attribute(values[column], name=name, where=where)
                    for column, name in enumerate(fields)
                }
                geometry = None
                if crs is not None:
                    geometry = geometry_from_wkb(values[width], crs=crs, where=where)
                yield Row(attributes=attributes, geometry=geometry)


def _attribute(value: object, *, name: FieldName, where: str) -> AttributeValue:
    """A cell narrowed to the port's union; a sub-second date is refused, and any other
    type is an adapter defect."""
    if isinstance(value, datetime) and value.microsecond:
        raise PortContractError(
            f"{where}: {name!r} holds {value!r}, which has a sub-second part; the port "
            "carries dates to the whole second."
        )
    if value is None or isinstance(value, int | float | str | datetime):
        return value
    raise TypeError(
        f"{where}: {value!r} is a {type(value).__name__}, which no field type holds."
    )
