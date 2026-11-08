"""Engine-neutral fixture cases: the rows a test seeds, and what it expects back.

What: `DatasetCase`, a schema and its rows under a name; the cases the tests share, as
functions so every test gets fresh values; the `*_children` functions, the geometries
each row of a multipart case explodes to, keyed by the row's 1-based position; `Seeded`,
what a seed produced, whichever store or engine produced it.

Why: the same case runs under the in-memory adapter and under an engine in the
conformance suite, so nothing here names an engine or a store, and nothing assumes the
order an engine writes rows in. A case's schema names its geometry family, because a
feature class holds one: a line case may mix single and multipart lines, a polygon case
single and multipart polygons, a multipoint case member counts, and nothing mixes
families.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ag.core.handles import ScratchHandle
from ag.core.types import DataType
from ag.ports import (
    Field,
    FieldType,
    Geometry,
    GeometryFamily,
    GeometryKind,
    Row,
    Schema,
)

CRS = "EPSG:25833"


@dataclass(frozen=True)
class DatasetCase:
    """One dataset to seed: its name, its schema and its rows in order."""

    name: str
    schema: Schema
    rows: tuple[Row, ...]


@dataclass(frozen=True)
class Seeded:
    """What a seed produced: the handle, and the native index of each row in order."""

    handle: ScratchHandle
    indices: tuple[int, ...]

    def index_of(self, position: int) -> int:
        """The native index of the row at 1-based `position` in the case."""
        return self.indices[position - 1]


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
        geometry_family=GeometryFamily.LINE,
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


def _named(family: GeometryFamily) -> Schema:
    return Schema(
        fields=(Field("name", FieldType.TEXT, 5),),
        geometry_crs=CRS,
        geometry_family=family,
    )


def multilines() -> DatasetCase:
    """A line, a three-part multiline and a two-part multiline, in that order."""
    return DatasetCase(
        name="multilines",
        schema=_named(GeometryFamily.LINE),
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
                {"name": "e"},
                Geometry(
                    GeometryKind.MULTILINESTRING,
                    (((6.0, 1.0), (7.0, 1.0)), ((8.0, 1.0), (9.0, 1.0))),
                    CRS,
                ),
            ),
        ),
    )


def multilines_children() -> dict[int, frozenset[Geometry]]:
    """The child geometries each row of `multilines()` explodes to, by 1-based position.

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
            {
                Geometry.linestring(((6.0, 1.0), (7.0, 1.0)), crs=CRS),
                Geometry.linestring(((8.0, 1.0), (9.0, 1.0)), crs=CRS),
            }
        ),
    }


def multipoints() -> DatasetCase:
    """A two-part multipoint and a one-member multipoint, in that order."""
    return DatasetCase(
        name="multipoints",
        schema=_named(GeometryFamily.MULTIPOINT),
        rows=(
            Row(
                {"name": "c"},
                Geometry(GeometryKind.MULTIPOINT, (((0.0, 2.0),), ((1.0, 2.0),)), CRS),
            ),
            Row(
                {"name": "d"}, Geometry(GeometryKind.MULTIPOINT, (((0.0, 3.0),),), CRS)
            ),
        ),
    )


def multipoints_children() -> dict[int, frozenset[Geometry]]:
    """The child geometries each row of `multipoints()` explodes to, by 1-based position."""
    return {
        1: frozenset(
            {Geometry.point(0.0, 2.0, crs=CRS), Geometry.point(1.0, 2.0, crs=CRS)}
        ),
        2: frozenset({Geometry.point(0.0, 3.0, crs=CRS)}),
    }


def points() -> DatasetCase:
    """Two single points."""
    return DatasetCase(
        name="points",
        schema=_named(GeometryFamily.POINT),
        rows=(
            Row({"name": "p"}, Geometry.point(0.0, 4.0, crs=CRS)),
            Row({"name": "q"}, Geometry.point(1.0, 4.0, crs=CRS)),
        ),
    )


def polygons() -> DatasetCase:
    """A square with a hole and a two-member multipolygon, in that order.

    Rings are written in the canonical orientation, exterior counter-clockwise and hole
    clockwise, so the literals read as the value holds them.
    """
    square = ((0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0), (0.0, 0.0))
    hole = ((1.0, 1.0), (1.0, 2.0), (2.0, 2.0), (2.0, 1.0), (1.0, 1.0))
    east = ((6.0, 0.0), (7.0, 0.0), (7.0, 1.0), (6.0, 1.0), (6.0, 0.0))
    west = ((8.0, 0.0), (9.0, 0.0), (9.0, 1.0), (8.0, 1.0), (8.0, 0.0))
    return DatasetCase(
        name="polygons",
        schema=_named(GeometryFamily.POLYGON),
        rows=(
            Row({"name": "s"}, Geometry(GeometryKind.POLYGON, (square, hole), CRS)),
            Row({"name": "t"}, Geometry(GeometryKind.MULTIPOLYGON, (east, west), CRS)),
        ),
    )


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
