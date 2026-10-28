"""The dataset-shape group of the in-memory `GeometryOps`: `explode_multipart`.

How: a multi kind yields one row per part, each the single kind over that one part with
the input row's attributes; a single kind yields its row unchanged. The pairs are the
input row's native index against the index the store assigned to each child, written as
a table when `parents` is given and not built otherwise. A null geometry is refused
before anything is written, and a table input is a contract error, since it has no
geometry to explode. Limit: `Geometry.parts` holds one ring per member of a multi kind,
so a multipolygon member with holes is not representable and never reaches this method
as one row. ADR-0017 RS-D16.
"""

from __future__ import annotations

import os

from ag.adapters.fakes.memory._base import MemoryPortBase
from ag.adapters.fakes.memory.store import Dataset
from ag.adapters.fakes.memory.support.preconditions import distinct_paths
from ag.core.errors import ErrorContext
from ag.core.handles import ScratchHandle
from ag.core.types import DataType
from ag.ports.attributes import Field, FieldType
from ag.ports.columns import CHILD_ID, PARENT_ID
from ag.ports.errors import EmptyGeometryError, PortContractError
from ag.ports.geometry import Geometry, GeometryKind
from ag.ports.table_ops import Row, Schema

_SINGLE_KIND = {
    GeometryKind.MULTIPOINT: GeometryKind.POINT,
    GeometryKind.MULTILINESTRING: GeometryKind.LINESTRING,
    GeometryKind.MULTIPOLYGON: GeometryKind.POLYGON,
}

PARENTS_SCHEMA = Schema(
    fields=(Field(PARENT_ID, FieldType.LONG), Field(CHILD_ID, FieldType.LONG)),
    data_type=DataType.TABLE,
)
"""The schema of a parents table: both native indices, as `LONG`."""


class Shape(MemoryPortBase):
    """The dataset-shape methods of `GeometryOps`, over the store."""

    def explode_multipart(
        self,
        *,
        input: ScratchHandle,
        output: ScratchHandle,
        parents: ScratchHandle | None = None,
    ) -> None:
        """Writes one row per part of every row of `input` to `output`."""
        handles = (input, output) if parents is None else (input, output, parents)
        distinct_paths(handles=handles)
        dataset = self._store.read(input)
        children: list[Row] = []
        origins: list[int] = []
        for index, row, geometry in _subject_rows(
            dataset=dataset, path=os.fspath(input)
        ):
            for part in _single_parts(geometry):
                children.append(Row(attributes=row.attributes, geometry=part))
                origins.append(index)
        assigned = self._store.write(output, schema=dataset.schema, rows=children)
        if parents is None:
            return
        pairs = [
            Row(attributes={PARENT_ID: parent, CHILD_ID: child})
            for parent, child in zip(origins, assigned, strict=True)
        ]
        self._store.write(parents, schema=PARENTS_SCHEMA, rows=pairs)


def _subject_rows(*, dataset: Dataset, path: str) -> list[tuple[int, Row, Geometry]]:
    """Every row with its geometry; a table input or a null geometry is refused first."""
    if dataset.schema.data_type is not DataType.FEATURE_CLASS:
        raise PortContractError(
            f"{path!r} is a {dataset.schema.data_type.value} and has no geometry to "
            "explode; explode_multipart takes a feature class.",
            context=ErrorContext(handle=path),
        )
    found: list[tuple[int, Row, Geometry]] = []
    nulls: list[int] = []
    for index, row in dataset.rows.items():
        if row.geometry is None:
            nulls.append(index)
        else:
            found.append((index, row, row.geometry))
    if nulls:
        raise EmptyGeometryError(
            f"{len(nulls)} row(s) of {path!r} have a null geometry, which has no parts; "
            "explode_multipart refuses them rather than drop them.",
            context=ErrorContext(handle=path, row_indices=tuple(nulls)),
        )
    return found


def _single_parts(geometry: Geometry) -> tuple[Geometry, ...]:
    """The single-kind geometries of `geometry`: one per part of a multi kind, else it."""
    single = _SINGLE_KIND.get(geometry.kind)
    if single is None:
        return (geometry,)
    return tuple(
        Geometry(kind=single, parts=(part,), crs=geometry.crs)
        for part in geometry.parts
    )
