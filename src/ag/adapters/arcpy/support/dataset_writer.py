"""Datasets created and rows inserted on the engine: the write side of the cursor rule.

What: `ADD_FIELD_TYPES`, the engine's field-type vocabulary for its AddField tool against
the port's types, and `GEOMETRY_TYPES`, its geometry-type vocabulary for CreateFeatureclass
against the port's families, each spelled here and nowhere else;
`create_table(session, path=, fields=)`,
a table with the declared fields; `add_fields(session, path=, fields=)`, the declared
fields on an existing dataset, a date field migrated to the engine's high precision as
it is added; `insert_rows(session, path=, tokens=, rows=)`, cell tuples
through one insert cursor under the session's guard; `split_path`, a dataset path as the
workspace and the name the engine's create tools take.

How: AddField's vocabulary (`LONG`, `TEXT`) is not the vocabulary Describe reports
(`Integer`, `String`), and CreateFeatureclass's (`POLYLINE`) is not Describe's
(`Polyline`), so these tables are a second direction and not the inverses of
`dataset_schema.FIELD_TYPES` and `SHAPE_TYPES`: the engine spells each type two ways,
and each table sits with the call that speaks it. A TEXT field carries its length. A DATE field is added at the engine's default
precision, a store of whole seconds that rounds what it is given, and then migrated by
`MIGRATION_TOOL` to precision 1, which holds the fraction and matches a fractional
literal (the probe of 2026-11-08), so every date field this adapter creates holds what
the port carries and nothing the adapter writes is reduced (A33). The in-memory
workspace keeps the fraction as it is and refuses the tool (the marked run of
2026-11-09), so a dataset there is not migrated. The engine's own
documentation gives that store milliseconds; the marked test holds a value written with
microseconds to within a millisecond. The rows are cell tuples in
the order of `tokens`, a geometry already encoded as the `WKB_TOKEN` cell where there is
one; nothing here holds a cell to its field, which is the caller's rule (ADR-0019
PC-D26). Every engine call runs inside the session's guard or through `run_tool`
(ADR-0018 AR-D23).

Second caller: `TableOps.write_rows`, ADR-0019 PC-D22, not yet landed; the parents table
of `explode_multipart` is the first, and the test-side builders create feature classes
with `GEOMETRY_TYPES` until `write_rows` does.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from types import MappingProxyType

from ag.adapters.arcpy.session import ArcpySession
from ag.adapters.arcpy.support.dataset_schema import in_memory_workspace
from ag.ports.attributes import Field, FieldType
from ag.ports.geometry import GeometryFamily

ADD_FIELD_TYPES: Mapping[FieldType, str] = MappingProxyType(
    {
        FieldType.SHORT: "SHORT",
        FieldType.LONG: "LONG",
        FieldType.DOUBLE: "DOUBLE",
        FieldType.TEXT: "TEXT",
        FieldType.DATE: "DATE",
    }
)
"""The port's field types as the engine's AddField tool spells them."""

GEOMETRY_TYPES: Mapping[GeometryFamily, str] = MappingProxyType(
    {
        GeometryFamily.POINT: "POINT",
        GeometryFamily.MULTIPOINT: "MULTIPOINT",
        GeometryFamily.LINE: "POLYLINE",
        GeometryFamily.POLYGON: "POLYGON",
    }
)
"""The port's geometry families as the engine's CreateFeatureclass tool spells them. All
four were confirmed on the image on 2026-11-05: every conformance case seeded through
them, the multipoints case among them."""

MIGRATION_TOOL = "management.MigrateDateFieldToHighPrecision"
"""The engine's tool that switches a date field from whole seconds to the fraction;
`(in_table, date_fields)` on the image, one field per call here."""


def create_table(
    session: ArcpySession, *, path: str, fields: tuple[Field, ...]
) -> None:
    """A table at `path` with `fields` declared, through the engine's tools."""
    workspace, name = split_path(path)
    session.run_tool("management.CreateTable", out_path=workspace, out_name=name)
    add_fields(session, path=path, fields=fields)


def add_fields(session: ArcpySession, *, path: str, fields: tuple[Field, ...]) -> None:
    """Declares `fields` on the dataset at `path`, one tool call each, and migrates each
    date field to the precision that holds the fraction, outside the in-memory workspace,
    which holds it already."""
    migrate = any(field.type is FieldType.DATE for field in fields) and (
        not in_memory_workspace(session, path)
    )
    for field in fields:
        arguments: dict[str, object] = {
            "in_table": path,
            "field_name": field.name,
            "field_type": ADD_FIELD_TYPES[field.type],
        }
        if field.length is not None:
            arguments["field_length"] = field.length
        session.run_tool("management.AddField", **arguments)
        if migrate and field.type is FieldType.DATE:
            session.run_tool(MIGRATION_TOOL, in_table=path, date_fields=field.name)


def insert_rows(
    session: ArcpySession,
    *,
    path: str,
    tokens: tuple[str, ...],
    rows: Iterable[Sequence[object]],
) -> None:
    """Inserts `rows`, one cell per token in order, through one cursor under the guard."""
    with session.guard("InsertCursor"):
        import arcpy

        with arcpy.da.InsertCursor(path, tokens) as cursor:
            for row in rows:
                cursor.insertRow(row)


def split_path(path: str) -> tuple[str, str]:
    """A dataset path as (workspace, name), on either separator, as the engine joins
    them; the workspace keeps the separators it was given."""
    cut = max(path.rfind("/"), path.rfind("\\"))
    return path[:cut], path[cut + 1 :]
