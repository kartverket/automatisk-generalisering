"""Small `.gdb` fixtures written with the engine: the builders behind the ArcPy half of
the conformance suite and the engine tests.

What: `file_gdb`, a file geodatabase through the engine's tool; `GEOMETRY_TYPES` and
`geometry_type_of`, the engine's feature-class geometry type for the kinds a case holds;
`seed`, a dataset created from a port `Schema` and filled from cell tuples, returning the
native indices in row order; `indices`, a dataset's native indices; `read_cells`, one
search cursor's rows as cell tuples; `delete_rows`, chosen rows removed so that a native
index is non-dense.

How: a table goes through the adapter's own `create_table`; a feature class through
`management.CreateFeatureclass` with the geometry type of the rows' kind, then the
adapter's `add_fields`, so the AddField vocabulary is spelled once, in the adapter. Rows
go through the adapter's `insert_rows` as cell tuples in field order, a feature class
with the geometry as its last cell, already encoded as well-known binary by the caller:
this module imports `ag` and the engine only, so the test-side encoder stays with the
case that uses it. The geometry type is the one family the rows' kinds belong to, single
and multi forms together; mixed families are refused here as the engine refuses them, and
a dataset with no geometry to read the type from needs it given. `CreateFeatureclass`
and `GEOMETRY_TYPES` live here until the adapter writes feature classes itself through
`TableOps.write_rows` (ADR-0019 PC-D22); the builders then call that and this copy goes.

Why: no port method writes yet, and the engine-neutral cases need an engine dataset. The
probe, `read_cells` with a bad token or clause, provokes the cursor failures the session's
guard wraps, which no port path reaches because every field is checked before a cursor
opens (ADR-0018 AR-D23).
"""

from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping, Sequence
from types import MappingProxyType

from ag.adapters.arcpy.session import ArcpySession
from ag.adapters.arcpy.support.dataset_schema import OID_TOKEN
from ag.adapters.arcpy.support.dataset_writer import (
    add_fields,
    create_table,
    insert_rows,
)
from ag.adapters.arcpy.support.geometry_values import WKB_TOKEN
from ag.core.types import DataType
from ag.ports.geometry import CRS, GeometryKind
from ag.ports.table_ops import Schema

GEOMETRY_TYPES: Mapping[GeometryKind, str] = MappingProxyType(
    {
        GeometryKind.POINT: "POINT",
        GeometryKind.MULTIPOINT: "MULTIPOINT",
        GeometryKind.LINESTRING: "POLYLINE",
        GeometryKind.MULTILINESTRING: "POLYLINE",
        GeometryKind.POLYGON: "POLYGON",
        GeometryKind.MULTIPOLYGON: "POLYGON",
    }
)
"""The engine's feature-class geometry type that holds each kind."""


def file_gdb(session: ArcpySession, *, directory: str, name: str) -> str:
    """A new file geodatabase `name` under `directory`; returns its path."""
    session.run_tool(
        "management.CreateFileGDB", out_folder_path=directory, out_name=name
    )
    return f"{directory}/{name}.gdb"


def geometry_type_of(kinds: Iterable[GeometryKind]) -> str:
    """The one engine geometry type the `kinds` share; mixed families are refused, as
    the engine refuses them, and no kind at all needs the type given instead."""
    found = {GEOMETRY_TYPES[kind] for kind in kinds}
    if len(found) != 1:
        raise ValueError(
            f"a feature class holds one geometry type, and these rows need {sorted(found)}; "
            "give geometry_type= for a dataset whose rows do not decide it."
        )
    return found.pop()


def seed(
    session: ArcpySession,
    *,
    workspace: str,
    name: str,
    schema: Schema,
    cells: Sequence[Sequence[object]],
    geometry_type: str | None = None,
) -> tuple[int, ...]:
    """Creates `workspace/name` from `schema`, inserts `cells` and returns the native
    indices in row order. A feature class takes the geometry as the last cell of each row,
    as well-known binary or None, and needs `geometry_type`."""
    path = f"{workspace}/{name}"
    names = tuple(field.name for field in schema.fields)
    if schema.data_type is DataType.TABLE:
        create_table(session, path=path, fields=schema.fields)
        tokens = names
    else:
        if geometry_type is None or schema.geometry_crs is None:
            raise ValueError(
                f"{path!r} is a feature class and needs its geometry type."
            )
        session.run_tool(
            "management.CreateFeatureclass",
            out_path=workspace,
            out_name=name,
            geometry_type=geometry_type,
            spatial_reference=_epsg(schema.geometry_crs),
        )
        add_fields(session, path=path, fields=schema.fields)
        tokens = (*names, WKB_TOKEN)
    insert_rows(session, path=path, tokens=tokens, rows=cells)
    return indices(session, path=path)


def indices(session: ArcpySession, *, path: str) -> tuple[int, ...]:
    """The native indices of `path`, in the engine's cursor order."""
    return tuple(
        _as_index(cell[0])
        for cell in read_cells(session, path=path, tokens=(OID_TOKEN,))
    )


def read_cells(
    session: ArcpySession,
    *,
    path: str,
    tokens: tuple[str, ...],
    where: str | None = None,
) -> list[tuple[object, ...]]:
    """One search cursor over `path` as cell tuples; a bad token or clause fails inside
    the guard, which is the point when a test passes one."""
    cells: list[tuple[object, ...]] = []
    with session.guard("SearchCursor"):
        import arcpy

        cursor = (
            arcpy.da.SearchCursor(path, tokens)
            if where is None
            else arcpy.da.SearchCursor(path, tokens, where_clause=where)
        )
        with cursor:
            for row in cursor:
                cells.append(tuple(row))
    return cells


def delete_rows(session: ArcpySession, *, path: str, indices: Collection[int]) -> None:
    """Deletes the rows of `path` whose native index is in `indices`."""
    with session.guard("UpdateCursor"):
        import arcpy

        with arcpy.da.UpdateCursor(path, (OID_TOKEN,)) as cursor:
            for row in cursor:
                if _as_index(row[0]) in indices:
                    cursor.deleteRow()


def _epsg(crs: CRS) -> int:
    """The code of an `EPSG:nnnn` CRS, as the engine's spatial reference parameter takes
    it."""
    prefix, _, code = crs.partition(":")
    if prefix != "EPSG" or not code.isdigit():
        raise ValueError(f"{crs!r} is not an EPSG:<code> CRS.")
    return int(code)


def _as_index(value: object) -> int:
    """A native index from the cursor; anything but an int is an adapter defect."""
    if isinstance(value, int):
        return value
    raise TypeError(
        f"{value!r} is not a native index; the cursor token was {OID_TOKEN}."
    )
