"""Engine-neutral fixture cases: the rows a test seeds, and what it expects back.

What: `DatasetCase`, a schema and its rows under a name; the cases the tests share, as
functions so every test gets fresh values; `parts_children`, the geometries each row of
the multipart case explodes to, keyed by the row's 1-based position.

Why: the same case runs under the in-memory adapter now and under an engine once the
conformance suite exists, so nothing here names an engine or a store, and nothing assumes
the order an engine writes rows in.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ag.core.types import DataType
from ag.ports import Field, FieldType, Geometry, GeometryKind, Row, Schema

CRS = "EPSG:25833"


@dataclass(frozen=True)
class DatasetCase:
    """One dataset to seed: its name, its schema and its rows in order."""

    name: str
    schema: Schema
    rows: tuple[Row, ...]


def roads() -> DatasetCase:
    """Four lines with a NULL in each nullable column, for the predicate cases."""
    schema = Schema(
        fields=(
            Field("name", FieldType.TEXT, 20),
            Field("rank", FieldType.LONG),
            Field("width_m", FieldType.DOUBLE),
            Field("surveyed", FieldType.DATE),
        ),
        geometry_crs=CRS,
    )
    line = Geometry.linestring(((0.0, 0.0), (1.0, 1.0)), crs=CRS)
    return DatasetCase(
        name="roads",
        schema=schema,
        rows=(
            Row(
                {
                    "name": "Alpha road",
                    "rank": 1,
                    "width_m": 2.5,
                    "surveyed": datetime(2024, 1, 1),
                },
                line,
            ),
            Row(
                {"name": "beta_road", "rank": None, "width_m": 3.0, "surveyed": None},
                line,
            ),
            Row(
                {
                    "name": "Gamma",
                    "rank": 3,
                    "width_m": None,
                    "surveyed": datetime(2024, 6, 1),
                },
                line,
            ),
            Row(
                {
                    "name": "delta",
                    "rank": 2,
                    "width_m": 4.0,
                    "surveyed": datetime(2023, 12, 31),
                },
                None,
            ),
        ),
    )


def parts() -> DatasetCase:
    """A line, a three-part multiline, a two-part multipoint and a point, in that order."""
    schema = Schema(fields=(Field("name", FieldType.TEXT, 5),), geometry_crs=CRS)
    return DatasetCase(
        name="parts",
        schema=schema,
        rows=(
            Row({"name": "a"}, Geometry.linestring(((0.0, 0.0), (1.0, 0.0)), crs=CRS)),
            Row(
                {"name": "b"},
                Geometry(
                    GeometryKind.MULTILINESTRING,
                    (
                        ((0.0, 1.0), (1.0, 1.0)),
                        ((2.0, 1.0), (3.0, 1.0)),
                        ((4.0, 1.0), (5.0, 1.0)),
                    ),
                    CRS,
                ),
            ),
            Row(
                {"name": "c"},
                Geometry(GeometryKind.MULTIPOINT, (((0.0, 2.0),), ((1.0, 2.0),)), CRS),
            ),
            Row({"name": "d"}, Geometry.point(0.0, 3.0, crs=CRS)),
        ),
    )


def parts_children() -> dict[int, frozenset[Geometry]]:
    """The child geometries each row of `parts()` explodes to, by 1-based position.

    Keyed by input row and unordered, so a test matches it through the pairs table and
    the two datasets' native indices and assumes nothing about the order an engine
    writes children in.
    """
    return {
        1: frozenset({Geometry.linestring(((0.0, 0.0), (1.0, 0.0)), crs=CRS)}),
        2: frozenset(
            {
                Geometry.linestring(((0.0, 1.0), (1.0, 1.0)), crs=CRS),
                Geometry.linestring(((2.0, 1.0), (3.0, 1.0)), crs=CRS),
                Geometry.linestring(((4.0, 1.0), (5.0, 1.0)), crs=CRS),
            }
        ),
        3: frozenset(
            {Geometry.point(0.0, 2.0, crs=CRS), Geometry.point(1.0, 2.0, crs=CRS)}
        ),
        4: frozenset({Geometry.point(0.0, 3.0, crs=CRS)}),
    }


def lookup() -> DatasetCase:
    """A two-row table with no geometry."""
    schema = Schema(
        fields=(Field("code", FieldType.SHORT), Field("label", FieldType.TEXT, 10)),
        data_type=DataType.TABLE,
    )
    return DatasetCase(
        name="lookup",
        schema=schema,
        rows=(Row({"code": 1, "label": "one"}), Row({"code": 2, "label": "two"})),
    )
