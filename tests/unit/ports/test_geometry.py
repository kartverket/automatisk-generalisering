"""The `Geometry` value type: its construction rules, its canonical ring orientation,
its shape, and the family each kind belongs to. ADR-0019 PC-D25."""

from __future__ import annotations

import pytest

from ag.ports import Geometry, GeometryFamily, GeometryKind
from ag.ports.geometry import Ring

CRS = "EPSG:25833"
SQUARE_CCW: Ring = ((0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0), (0.0, 0.0))
SQUARE_CW: Ring = tuple(reversed(SQUARE_CCW))
HOLE_CW: Ring = ((1.0, 1.0), (1.0, 2.0), (2.0, 2.0), (2.0, 1.0), (1.0, 1.0))
HOLE_CCW: Ring = tuple(reversed(HOLE_CW))
EAST_CCW: Ring = ((6.0, 0.0), (7.0, 0.0), (7.0, 1.0), (6.0, 1.0), (6.0, 0.0))
EAST_CW: Ring = tuple(reversed(EAST_CCW))


def _rect(x: float, y: float, w: float, h: float) -> Ring:
    """A counter-clockwise rectangle with its lower-left corner at (x, y)."""
    return ((x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y))


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


def test_a_polygon_is_canonical_on_construction() -> None:
    """Exterior counter-clockwise, holes clockwise, whatever order they were given in."""
    inverted = Geometry(GeometryKind.POLYGON, (SQUARE_CW, HOLE_CCW), CRS)
    canonical = Geometry(GeometryKind.POLYGON, (SQUARE_CCW, HOLE_CW), CRS)
    assert inverted.parts == (SQUARE_CCW, HOLE_CW)
    assert inverted == canonical
    assert len({inverted, canonical}) == 1


def test_every_multipolygon_member_is_counter_clockwise() -> None:
    multi = Geometry(GeometryKind.MULTIPOLYGON, (SQUARE_CCW, EAST_CW), CRS)
    assert multi.parts == (SQUARE_CCW, EAST_CCW)


def test_a_canonical_value_keeps_the_parts_tuple_it_was_given() -> None:
    """What an engine returns is already canonical, so construction allocates nothing."""
    parts = (SQUARE_CCW, HOLE_CW)
    assert Geometry(GeometryKind.POLYGON, parts, CRS).parts is parts
    members = (SQUARE_CCW, EAST_CCW)
    assert Geometry(GeometryKind.MULTIPOLYGON, members, CRS).parts is members


def test_lines_and_points_are_never_reoriented() -> None:
    line = Geometry.linestring(SQUARE_CW, crs=CRS)
    assert line.parts == (SQUARE_CW,)
    multi = Geometry(GeometryKind.MULTILINESTRING, (SQUARE_CW, HOLE_CCW), CRS)
    assert multi.parts == (SQUARE_CW, HOLE_CCW)
    assert Geometry.point(1.0, 2.0, crs=CRS).parts == (((1.0, 2.0),),)


@pytest.mark.parametrize(
    "ring",
    [
        (),
        ((500000.0, 7000000.0),),
        ((500000.0, 7000000.0), (500001.0, 7000001.0)),
        (
            (500000.0, 7000000.0),
            (500001.0, 7000001.0),
            (500002.0, 7000002.0),
            (500000.0, 7000000.0),
        ),
    ],
    ids=["empty", "one-vertex", "two-vertices", "collinear"],
)
def test_a_ring_of_zero_area_keeps_its_order(ring: Ring) -> None:
    """A degenerate ring has no orientation to repair; what B33 does with it is B33's."""
    assert Geometry(GeometryKind.POLYGON, (ring,), CRS).parts == (ring,)
    assert Geometry(GeometryKind.POLYGON, (SQUARE_CCW, ring), CRS).parts == (
        SQUARE_CCW,
        ring,
    )


@pytest.mark.parametrize(
    "exterior",
    [
        _rect(500000.0, 7000000.0, 0.01, 0.0001),
        _rect(654321.0, 7654321.0, 0.001, 0.001),
    ],
    ids=["thin-1cm-by-0.1mm", "small-1mm"],
)
def test_orientation_is_read_at_projected_coordinates(exterior: Ring) -> None:
    """At eastings and northings in the hundreds of kilometres, a ring millimetres
    across still has its sign: the signed area is taken relative to the first vertex."""
    clockwise = tuple(reversed(exterior))
    assert Geometry(GeometryKind.POLYGON, (exterior,), CRS).parts == (exterior,)
    assert Geometry(GeometryKind.POLYGON, (clockwise,), CRS).parts == (exterior,)
    hole = tuple(
        (x + 0.0001, y + 0.00001) for x, y in exterior
    )  # inside, counter-clockwise
    assert Geometry(GeometryKind.POLYGON, (exterior, hole), CRS).parts == (
        exterior,
        tuple(reversed(hole)),
    )


def test_each_kind_belongs_to_one_family_and_multipoint_explodes_to_point() -> None:
    assert {kind: kind.family for kind in GeometryKind} == {
        GeometryKind.POINT: GeometryFamily.POINT,
        GeometryKind.MULTIPOINT: GeometryFamily.MULTIPOINT,
        GeometryKind.LINESTRING: GeometryFamily.LINE,
        GeometryKind.MULTILINESTRING: GeometryFamily.LINE,
        GeometryKind.POLYGON: GeometryFamily.POLYGON,
        GeometryKind.MULTIPOLYGON: GeometryFamily.POLYGON,
    }
    assert {family: family.single for family in GeometryFamily} == {
        GeometryFamily.POINT: GeometryFamily.POINT,
        GeometryFamily.MULTIPOINT: GeometryFamily.POINT,
        GeometryFamily.LINE: GeometryFamily.LINE,
        GeometryFamily.POLYGON: GeometryFamily.POLYGON,
    }


def test_the_families_are_the_four_a_feature_class_can_be() -> None:
    assert [family.value for family in GeometryFamily] == [
        "point",
        "multipoint",
        "line",
        "polygon",
    ]


def test_the_kinds_are_ogc_names_without_a_collection() -> None:
    assert [kind.value for kind in GeometryKind] == [
        "Point",
        "LineString",
        "Polygon",
        "MultiPoint",
        "MultiLineString",
        "MultiPolygon",
    ]
