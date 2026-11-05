"""The dataset-shape group of the ArcPy `GeometryOps`: `explode_multipart`.

How: the engine's multipart-to-singlepart tool writes one row per part and adds a field
holding each child's parent native index. That field is found by diffing the output's
field names against the input's, the engine's own fields left out, rather than assumed
by name, since what the tool calls it when the name is taken is the engine's business;
exactly one added field is expected, and anything else is an `EngineError`. The pairs
are read from it against the output's native index and written as the port's parents
table through the support writer when `parents` is given; the field is then dropped on
every call, so the output's schema is the input's whether or not parents were asked for. A null or empty shape is refused with
`EmptyGeometryError` before the tool runs, with its native indices in the context, and a
table input is a contract error, since it has no geometry to explode. ADR-0017 RS-D16.

Expected of the engine, confirmed by the first run under it: the tool keeps a GlobalID
field as it is, adds no field but the reference, and names the reference differently
when `ORIG_FID` is already taken.
"""

from __future__ import annotations

import os

from ag.adapters._shared.preconditions import distinct_paths
from ag.adapters.arcpy._base import ArcpyPortBase
from ag.adapters.arcpy.session import ArcpySession
from ag.adapters.arcpy.support.dataset_schema import (
    OID_TOKEN,
    DescribedDataset,
    describe,
)
from ag.adapters.arcpy.support.dataset_writer import create_table, insert_rows
from ag.adapters.arcpy.support.geometry_values import WKB_TOKEN, is_null_shape
from ag.core.errors import ErrorContext
from ag.core.handles import ScratchHandle
from ag.core.types import DataType
from ag.ports.attributes import FieldName
from ag.ports.columns import CHILD_ID, PARENT_ID
from ag.ports.errors import EmptyGeometryError, EngineError, PortContractError
from ag.ports.table_ops import PARENTS_SCHEMA

_EXPLODE = "management.MultipartToSinglepart"


class Shape(ArcpyPortBase):
    """The dataset-shape methods of `GeometryOps`, through the session."""

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
        source, target = os.fspath(input), os.fspath(output)
        before = describe(self._session, source)
        if before.schema.data_type is not DataType.FEATURE_CLASS:
            raise PortContractError(
                f"{source!r} is a {before.schema.data_type.value} and has no geometry to "
                "explode; explode_multipart takes a feature class.",
                context=ErrorContext(handle=source),
            )
        _refuse_null_shapes(self._session, path=source)
        self._session.run_tool(_EXPLODE, in_features=source, out_feature_class=target)
        after = describe(self._session, target)
        reference = _reference_field(before=before, after=after)
        if parents is not None:
            pairs = _read_pairs(self._session, path=target, reference=reference)
            _write_pairs(self._session, path=os.fspath(parents), pairs=pairs)
        self._session.run_tool(
            "management.DeleteField", in_table=target, drop_field=reference
        )


def _refuse_null_shapes(session: ArcpySession, *, path: str) -> None:
    """One pass over the shapes; a null or empty one is refused before the tool runs."""
    nulls: list[int] = []
    with session.guard("SearchCursor"):
        import arcpy

        with arcpy.da.SearchCursor(path, (OID_TOKEN, WKB_TOKEN)) as cursor:
            for index, shape in cursor:
                if is_null_shape(shape):
                    nulls.append(_as_index(index))
    if nulls:
        raise EmptyGeometryError(
            f"{len(nulls)} row(s) of {path!r} have a null geometry, which has no parts; "
            "explode_multipart refuses them rather than drop them.",
            context=ErrorContext(handle=path, row_indices=tuple(nulls)),
        )


def _reference_field(*, before: DescribedDataset, after: DescribedDataset) -> FieldName:
    """The one field the tool added: the output's names less the input's and less the
    output's own engine fields."""
    added = [
        name
        for name in after.all_fields
        if name not in before.all_fields and name not in after.engine_fields
    ]
    if len(added) != 1:
        raise EngineError(
            f"arcpy: {_EXPLODE} added {added} to {after.path!r}; one reference field was "
            "expected.",
            context=ErrorContext(
                tool=_EXPLODE,
                tool_messages=(
                    f"input fields {list(before.all_fields)}",
                    f"output fields {list(after.all_fields)}",
                ),
            ),
        )
    return added[0]


def _read_pairs(
    session: ArcpySession, *, path: str, reference: FieldName
) -> list[tuple[int, int]]:
    """(parent, child) native indices from the reference field and the output's index."""
    pairs: list[tuple[int, int]] = []
    with session.guard("SearchCursor"):
        import arcpy

        with arcpy.da.SearchCursor(path, (reference, OID_TOKEN)) as cursor:
            for parent, child in cursor:
                pairs.append((_as_index(parent), _as_index(child)))
    return pairs


def _write_pairs(
    session: ArcpySession, *, path: str, pairs: list[tuple[int, int]]
) -> None:
    """Creates the parents table with the port's schema and fills it."""
    create_table(session, path=path, fields=PARENTS_SCHEMA.fields)
    insert_rows(session, path=path, tokens=(PARENT_ID, CHILD_ID), rows=pairs)


def _as_index(value: object) -> int:
    """A native index from the cursor; anything but an int is an adapter defect."""
    if isinstance(value, int):
        return value
    raise TypeError(
        f"{value!r} is not a native index; the cursor token was {OID_TOKEN}."
    )
