"""Describe to the port's `Schema`: what a dataset declares, read before a tool runs.

What: `DescribedDataset`, the port-visible schema of one dataset plus what the port does
not carry: the fields whose engine type has no `FieldType`, by name and engine type;
every field name the engine reports; the engine's own field names, the native index,
the shape, and the length and area it maintains; and the grain each date field's store
holds, a second or a millisecond, which `read_rows` rounds to. `describe(session, path)` builds
it inside the session's guard; `declared_field(dataset, name)` is the one lookup that
`read_rows` and the predicate compiler share. `OID_TOKEN` is the cursor token for the
native index, and `FIELD_TYPES`, `DATA_TYPES` and `SHAPE_TYPES` the engine's type names
against the port's, each spelled here and nowhere else.

How: the engine's `SmallInteger`, `Integer`, `Double`, `String` and `Date` map to the
five `FieldType` members. A `Date` field's engine `precision` is 0 or 1: at 0 the file
geodatabase holds whole seconds in a double of days, and one in eight reads back a
microsecond off its stored second (the probe of 2026-11-08, all four production fields,
every stray part within a millisecond of a whole second); at 1 it holds milliseconds,
with the same noise one grain finer (the probe of 2026-11-09, a fifth of the
millisecond-aligned values a few microseconds off). `date_grains` names each date
field's grain, so the reader restores the stored value and no encoding noise crosses the
port (A33). The memory workspace reports 0 and holds milliseconds regardless, and
refuses the migration tool (the marked run of 2026-11-09), so a date field there is at
the millisecond grain: `in_memory_workspace` reads the workspace's
`workspaceFactoryProgID`, the one place that spelling lives, and `describe` consults it
only when a date field at 0 is present, so a dataset without one costs no second
Describe. The workspace is found by walking a dataset's `path` upward until a Describe
reports `dataType` `Workspace`, at most `WORKSPACE_DEPTH` steps, since a feature class
sits in its workspace or in one feature dataset inside it and feature datasets do not
nest; a walk that reaches no workspace within that is a `PortContractError` naming the
path, not a loop or a failure on an unrelated Describe. Every other type, `BigInteger`, `Single`, `GUID`, `GlobalID`,
`Blob`, `Raster`, `DateOnly`, `TimeOnly`, `TimestampOffset` and any later one, is
unrepresentable and recorded rather than refused: a dataset carrying such a field is
read and selected over as long as no call names the field, and naming one is a
`PortContractError` that says which engine type it is, the rule `ag.ports.attributes`
states. The engine's own fields are left out by the names Describe reports for them,
which is exact where a test on the field type is not. `BigInteger` is unrepresentable
here because `FieldType` has no 64-bit member; nothing here decides whether it gets one.

A dataset with Z or M values is refused with `PortContractError` before any row is read.
The port carries planar coordinates only: heights and depths are delivered as field
values on points, and Z is not a gap this project fills. A team that needs Z on this
engine owns that support. ADR-0019 PC-D27.

The CRS is the dataset's own, from its spatial reference's EPSG code, never the
session's environment: whether an input conforms to the standard is settled elsewhere.
A dataset whose spatial reference has no EPSG code is refused, since a `Schema` needs a
CRS, and so is a feature class whose `shapeType` is none of the four the port's families
name, since a `Schema` needs a family. Expected of the engine and confirmed by the first
run under it: `lengthFieldName` and `areaFieldName` are empty strings where a feature
class has no such field.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from types import MappingProxyType

from ag.adapters.arcpy.session import ArcpySession
from ag.core.errors import ErrorContext
from ag.core.types import DataType
from ag.ports.attributes import Field, FieldName, FieldType
from ag.ports.errors import PortContractError
from ag.ports.geometry import CRS, GeometryFamily
from ag.ports.table_ops import Schema

FIELD_TYPES: Mapping[str, FieldType] = MappingProxyType(
    {
        "SmallInteger": FieldType.SHORT,
        "Integer": FieldType.LONG,
        "Double": FieldType.DOUBLE,
        "String": FieldType.TEXT,
        "Date": FieldType.DATE,
    }
)
"""Engine field type to the port's; anything else is unrepresentable."""

OID_TOKEN = "OID@"
"""The cursor token for a row's native index."""

DATA_TYPES: Mapping[str, DataType] = MappingProxyType(
    {"FeatureClass": DataType.FEATURE_CLASS, "Table": DataType.TABLE}
)
"""Engine `dataType` to the port's; anything else is not a dataset a port method takes."""

SHAPE_TYPES: Mapping[str, GeometryFamily] = MappingProxyType(
    {
        "Point": GeometryFamily.POINT,
        "Multipoint": GeometryFamily.MULTIPOINT,
        "Polyline": GeometryFamily.LINE,
        "Polygon": GeometryFamily.POLYGON,
    }
)
"""Engine `shapeType` to the port's family. `Point`, `Polyline` and `Polygon` were read
from the raw sources in the timing run of 2026-11-06 and all four, `Multipoint` included,
from the marked run of 2026-11-08 in both workspaces (W23)."""


@dataclass(frozen=True, slots=True)
class DescribedDataset:
    """One dataset as the port sees it, plus what the engine reports that it does not."""

    path: str
    schema: Schema
    unrepresentable: Mapping[FieldName, str]
    """Field name to engine type, for every field no `FieldType` represents."""
    all_fields: tuple[FieldName, ...]
    """Every field name the engine reports, in its order, the engine's own included."""
    engine_fields: frozenset[FieldName]
    """The native index, the shape, and the length and area the engine maintains."""
    date_grains: Mapping[FieldName, DateGrain] = MappingProxyType({})
    """The grain each declared date field's store holds, which `read_rows` rounds to."""


class DateGrain(Enum):
    """What a date store holds: whole seconds, or milliseconds. Each reads back with the
    double encoding's microsecond noise, so a reader rounds to the grain and a writer
    truncates to it (A33)."""

    SECOND = timedelta(seconds=1)
    MILLISECOND = timedelta(milliseconds=1)


WHOLE_SECOND_PRECISION = 0
"""The engine `precision` of a date field that holds whole seconds; 1 holds milliseconds."""

MEMORY_WORKSPACE_PROG_ID = "esriDataSourcesGDB.MemoryWorkspaceFactory"
"""The `workspaceFactoryProgID` of the engine's in-memory workspace, which keeps a date's
fraction at any `precision` and takes no migration."""

WORKSPACE_DATA_TYPE = "Workspace"
"""The engine `dataType` of a workspace's Describe, where `workspaceFactoryProgID` lives."""

WORKSPACE_DEPTH = 2
"""How many `path` steps up a dataset's workspace is at most: one for a dataset in its
workspace, two for a feature class in a feature dataset, which do not nest."""


@dataclass(frozen=True, slots=True)
class _Raw:
    """What one Describe call read, carried out of the guard before any port rule runs."""

    data_type: DataType | None
    engine_data_type: str
    fields: tuple[tuple[str, str, int, int], ...]
    """Each field as (name, engine type, length, precision)."""
    engine_fields: tuple[str, ...]
    has_z: bool
    has_m: bool
    epsg: int | None
    shape_type: str | None
    workspace: str
    """The path of the dataset's workspace, for `in_memory_workspace`."""


def describe(session: ArcpySession, path: str, /) -> DescribedDataset:
    """The dataset at `path`, as the port sees it; refused if it is not a table or feature
    class, carries Z or M, has no EPSG code, or has a shape type outside the families."""
    raw = _read(session, path)
    data_type = raw.data_type
    if data_type is None:
        raise PortContractError(
            f"{path!r} is a {raw.engine_data_type}, not a table or a feature class.",
            context=ErrorContext(handle=path),
        )
    if raw.has_z or raw.has_m:
        raise PortContractError(
            f"{path!r} carries {'Z' if raw.has_z else 'M'} values; the port carries "
            "planar coordinates only, and heights and depths travel as field values.",
            context=ErrorContext(handle=path),
        )
    crs: CRS | None = None
    family: GeometryFamily | None = None
    if data_type is DataType.FEATURE_CLASS:
        if not raw.epsg:
            raise PortContractError(
                f"{path!r} has a spatial reference with no EPSG code; a schema needs a CRS.",
                context=ErrorContext(handle=path),
            )
        crs = f"EPSG:{raw.epsg}"
        family = SHAPE_TYPES.get(raw.shape_type or "")
        if family is None:
            raise PortContractError(
                f"{path!r} has shape type {raw.shape_type!r}, which none of the port's "
                f"geometry families holds; the families are {sorted(SHAPE_TYPES)}.",
                context=ErrorContext(handle=path),
            )
    engine_fields = frozenset(name for name in raw.engine_fields if name)
    declared: list[Field] = []
    unrepresentable: dict[FieldName, str] = {}
    grains: dict[FieldName, DateGrain] = {}
    for name, engine_type, length, precision in raw.fields:
        if name in engine_fields:
            continue
        field_type = FIELD_TYPES.get(engine_type)
        if field_type is None:
            unrepresentable[name] = engine_type
        elif field_type is FieldType.TEXT:
            declared.append(Field(name, field_type, length))
        else:
            declared.append(Field(name, field_type))
            if field_type is FieldType.DATE:
                grains[name] = (
                    DateGrain.SECOND
                    if precision == WHOLE_SECOND_PRECISION
                    else DateGrain.MILLISECOND
                )
    if DateGrain.SECOND in grains.values():
        prog_id = _workspace_prog_id(session, raw.workspace, dataset=path)
        if prog_id == MEMORY_WORKSPACE_PROG_ID:
            grains = dict.fromkeys(grains, DateGrain.MILLISECOND)
    return DescribedDataset(
        path=path,
        schema=Schema(
            fields=tuple(declared),
            data_type=data_type,
            geometry_crs=crs,
            geometry_family=family,
        ),
        unrepresentable=MappingProxyType(unrepresentable),
        all_fields=tuple(name for name, _, _, _ in raw.fields),
        engine_fields=engine_fields,
        date_grains=MappingProxyType(grains),
    )


def in_memory_workspace(session: ArcpySession, path: str, /) -> bool:
    """Whether the dataset at `path` lives in the engine's in-memory workspace."""
    with session.guard("Describe"):
        import arcpy

        parent = arcpy.Describe(path).path
    return _workspace_prog_id(session, parent, dataset=path) == MEMORY_WORKSPACE_PROG_ID


def _workspace_prog_id(session: ArcpySession, parent: str, /, *, dataset: str) -> str:
    """The `workspaceFactoryProgID` of the workspace that holds `dataset`, starting from
    its `parent` path and walking up at most `WORKSPACE_DEPTH` Describes."""
    path = parent
    for _ in range(WORKSPACE_DEPTH):
        with session.guard("Describe"):
            import arcpy

            described = arcpy.Describe(path)
            if described.dataType == WORKSPACE_DATA_TYPE:
                return described.workspaceFactoryProgID
            path = described.path
    raise PortContractError(
        f"{dataset!r} has no workspace within {WORKSPACE_DEPTH} levels of its path; a "
        "dataset sits in its workspace or in one feature dataset inside it.",
        context=ErrorContext(handle=dataset),
    )


def declared_field(dataset: DescribedDataset, name: FieldName, /) -> Field:
    """The declared field `name` of `dataset`; an unrepresentable or undeclared name is a
    `PortContractError` that says which."""
    for field in dataset.schema.fields:
        if field.name == name:
            return field
    declared = [field.name for field in dataset.schema.fields]
    engine_type = dataset.unrepresentable.get(name)
    if engine_type is not None:
        raise PortContractError(
            f"{name!r} is a {engine_type} field of {dataset.path!r}, which no FieldType "
            f"represents; the declared fields are {declared}.",
            context=ErrorContext(handle=dataset.path),
        )
    raise PortContractError(
        f"{name!r} is not a field of {dataset.path!r}, whose fields are {declared}.",
        context=ErrorContext(handle=dataset.path),
    )


def _read(session: ArcpySession, path: str, /) -> _Raw:
    """One Describe call under the guard; a feature class reads its shape names, its
    shape type and its spatial reference too."""
    with session.guard("Describe"):
        import arcpy

        described = arcpy.Describe(path)
        engine_data_type = described.dataType
        data_type = DATA_TYPES.get(engine_data_type)
        fields = tuple(
            (f.name, f.type, f.length, f.precision) for f in described.fields
        )
        engine_fields = [described.OIDFieldName]
        workspace = described.path
        has_z = has_m = False
        epsg: int | None = None
        shape_type: str | None = None
        if data_type is DataType.FEATURE_CLASS:
            engine_fields += [
                described.shapeFieldName,
                described.lengthFieldName,
                described.areaFieldName,
            ]
            has_z, has_m = described.hasZ, described.hasM
            epsg = described.spatialReference.factoryCode
            shape_type = described.shapeType
    return _Raw(
        data_type=data_type,
        engine_data_type=engine_data_type,
        fields=fields,
        engine_fields=tuple(engine_fields),
        has_z=has_z,
        has_m=has_m,
        epsg=epsg,
        shape_type=shape_type,
        workspace=workspace,
    )
