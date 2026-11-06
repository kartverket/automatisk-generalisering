"""Describe to the port's `Schema`: what a dataset declares, read before a tool runs.

What: `DescribedDataset`, the port-visible schema of one dataset plus what the port does
not carry: the fields whose engine type has no `FieldType`, by name and engine type;
every field name the engine reports; and the engine's own field names, the native
index, the shape, and the length and area it maintains. `describe(session, path)` builds
it inside the session's guard; `declared_field(dataset, name)` is the one lookup that
`read_rows` and the predicate compiler share. `OID_TOKEN` is the cursor token for the
native index, and `FIELD_TYPES` and `DATA_TYPES` the engine's type names against the port's,
each spelled here and nowhere else.

How: the engine's `SmallInteger`, `Integer`, `Double`, `String` and `Date` map to the
five `FieldType` members. Every other type, `BigInteger`, `Single`, `GUID`, `GlobalID`,
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
CRS. Expected of the engine and confirmed by the first run under it: `lengthFieldName`
and `areaFieldName` are empty strings where a feature class has no such field.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from ag.adapters.arcpy.session import ArcpySession
from ag.core.errors import ErrorContext
from ag.core.types import DataType
from ag.ports.attributes import Field, FieldName, FieldType
from ag.ports.errors import PortContractError
from ag.ports.geometry import CRS
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


@dataclass(frozen=True, slots=True)
class _Raw:
    """What one Describe call read, carried out of the guard before any port rule runs."""

    data_type: str
    fields: tuple[tuple[str, str, int], ...]
    engine_fields: tuple[str, ...]
    has_z: bool
    has_m: bool
    epsg: int | None


def describe(session: ArcpySession, path: str, /) -> DescribedDataset:
    """The dataset at `path`, as the port sees it; refused if it is not a table or feature
    class, carries Z or M, or has no EPSG code."""
    raw = _read(session, path)
    data_type = DATA_TYPES.get(raw.data_type)
    if data_type is None:
        raise PortContractError(
            f"{path!r} is a {raw.data_type}, not a table or a feature class.",
            context=ErrorContext(handle=path),
        )
    if raw.has_z or raw.has_m:
        raise PortContractError(
            f"{path!r} carries {'Z' if raw.has_z else 'M'} values; the port carries "
            "planar coordinates only, and heights and depths travel as field values.",
            context=ErrorContext(handle=path),
        )
    crs: CRS | None = None
    if data_type is DataType.FEATURE_CLASS:
        if not raw.epsg:
            raise PortContractError(
                f"{path!r} has a spatial reference with no EPSG code; a schema needs a CRS.",
                context=ErrorContext(handle=path),
            )
        crs = f"EPSG:{raw.epsg}"
    engine_fields = frozenset(name for name in raw.engine_fields if name)
    declared: list[Field] = []
    unrepresentable: dict[FieldName, str] = {}
    for name, engine_type, length in raw.fields:
        if name in engine_fields:
            continue
        field_type = FIELD_TYPES.get(engine_type)
        if field_type is None:
            unrepresentable[name] = engine_type
        elif field_type is FieldType.TEXT:
            declared.append(Field(name, field_type, length))
        else:
            declared.append(Field(name, field_type))
    return DescribedDataset(
        path=path,
        schema=Schema(fields=tuple(declared), data_type=data_type, geometry_crs=crs),
        unrepresentable=MappingProxyType(unrepresentable),
        all_fields=tuple(name for name, _, _ in raw.fields),
        engine_fields=engine_fields,
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
    """One Describe call under the guard; a feature class reads its shape names too."""
    with session.guard("Describe"):
        import arcpy

        described = arcpy.Describe(path)
        data_type = described.dataType
        fields = tuple((f.name, f.type, f.length) for f in described.fields)
        engine_fields = [described.OIDFieldName]
        has_z = has_m = False
        epsg: int | None = None
        if data_type == "FeatureClass":
            engine_fields += [
                described.shapeFieldName,
                described.lengthFieldName,
                described.areaFieldName,
            ]
            has_z, has_m = described.hasZ, described.hasM
            epsg = described.spatialReference.factoryCode
    return _Raw(
        data_type=data_type,
        fields=fields,
        engine_fields=tuple(engine_fields),
        has_z=has_z,
        has_m=has_m,
        epsg=epsg,
    )
