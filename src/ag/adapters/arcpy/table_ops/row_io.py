"""The bulk row IO group of the ArcPy `TableOps`: `read_rows`.

How: the fields are checked against the input's described schema before any row is
read, then the rows stream from one cursor under one guard: the guard encloses the
whole iteration, so an engine failure at any row leaves as `EngineError`, and a caller
that stops early closes the cursor through the generator. Each attribute is narrowed to
the port's value union as it is read, the shape through the WKB codec; a value of any
other type is an adapter defect. A date is read to its field's store grain
(`DescribedDataset.date_grains`), a second or a millisecond, rounded, because the engine
encodes a date as a double and about one value in eight at the second and one in five
at the millisecond reads back a few microseconds off the value it holds; rounding
restores the stored value, and no encoding noise crosses the port. The engine's own
equality on the rounded literal selects the same rows (the probe of 2026-11-09), so
`select` and `read_rows` agree (ADR-0019 PC-D17; A33). An empty field list reads the native index and drops
it, since the engine refuses a cursor with no field. ADR-0019 PC-D22.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Iterator
from datetime import datetime, timedelta

from ag.adapters.arcpy._base import ArcpyPortBase
from ag.adapters.arcpy.session import ArcpySession
from ag.adapters.arcpy.support.dataset_schema import (
    OID_TOKEN,
    DateGrain,
    DescribedDataset,
    declared_field,
    describe,
)
from ag.adapters.arcpy.support.geometry_values import WKB_TOKEN, geometry_from_wkb
from ag.core.handles import ScratchHandle
from ag.ports.attributes import AttributeValue, FieldName
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
    grains = dataset.date_grains
    with session.guard("SearchCursor"):
        import arcpy

        with arcpy.da.SearchCursor(dataset.path, tokens) as cursor:
            for position, values in enumerate(cursor):
                where = f"{dataset.path!r} row {position}"
                attributes = {
                    name: _attribute(
                        values[column], where=where, grain=grains.get(name)
                    )
                    for column, name in enumerate(fields)
                }
                geometry = None
                if crs is not None:
                    geometry = geometry_from_wkb(values[width], crs=crs, where=where)
                yield Row(attributes=attributes, geometry=geometry)


_MICROSECOND = timedelta(microseconds=1)


def _attribute(value: object, *, where: str, grain: DateGrain | None) -> AttributeValue:
    """A cell narrowed to the port's union; a date is read to its store's nearest grain,
    and a value of any other type is an adapter defect."""
    if isinstance(value, datetime):
        if grain is not None and value.microsecond:
            return _rounded(value, grain)
        return value
    if value is None or isinstance(value, int | float | str):
        return value
    raise TypeError(
        f"{where}: {value!r} is a {type(value).__name__}, which no field type holds."
    )


def _rounded(value: datetime, grain: DateGrain) -> datetime:
    """`value` at the nearest multiple of `grain`, which divides a second."""
    unit = grain.value // _MICROSECOND
    shifted = value + grain.value / 2
    return shifted.replace(microsecond=shifted.microsecond - shifted.microsecond % unit)
