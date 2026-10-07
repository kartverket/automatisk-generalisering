"""The `Geometry` value type: its two construction rules and its shape."""

from __future__ import annotations

import pytest

from ag.ports import Geometry, GeometryKind

CRS = "EPSG:25833"


def test_parts_is_always_a_sequence_of_rings() -> None:
    point = Geometry.point(1.0, 2.0, crs=CRS)
    line = Geometry.linestring(((0.0, 0.0), (1.0, 1.0)), crs=CRS)
    polygon = Geometry(
        GeometryKind.POLYGON, (((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 0.0)),), CRS
    )
    assert point.parts == (((1.0, 2.0),),)
    assert line.coords == ((0.0, 0.0), (1.0, 1.0))
    assert line.coords[0] == (0.0, 0.0) and line.coords[-1] == (1.0, 1.0)
    assert len(polygon.parts) == 1


def test_an_empty_geometry_is_refused() -> None:
    """A null geometry is `Row.geometry is None`, never a `Geometry` with no parts."""
    with pytest.raises(ValueError, match="null geometry"):
        Geometry(GeometryKind.LINESTRING, (), CRS)


def test_a_point_is_exactly_one_coordinate() -> None:
    with pytest.raises(ValueError, match="POINT must be exactly one part"):
        Geometry(GeometryKind.POINT, (((0.0, 0.0), (1.0, 1.0)),), CRS)
    with pytest.raises(ValueError, match="POINT must be exactly one part"):
        Geometry(GeometryKind.POINT, (((0.0, 0.0),), ((1.0, 1.0),)), CRS)


def test_geometry_is_an_immutable_hashable_value() -> None:
    first = Geometry.point(1.0, 2.0, crs=CRS)
    second = Geometry.point(1.0, 2.0, crs=CRS)
    assert first == second
    assert len({first, second}) == 1
    with pytest.raises(AttributeError):
        first.crs = "EPSG:4326"  # type: ignore[misc]


def test_the_kinds_are_ogc_names_without_a_collection() -> None:
    assert [kind.value for kind in GeometryKind] == [
        "Point",
        "LineString",
        "Polygon",
        "MultiPoint",
        "MultiLineString",
        "MultiPolygon",
    ]
