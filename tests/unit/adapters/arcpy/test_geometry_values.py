"""The WKB codec: every kind round-trips in both byte orders, null and empty shapes are
None, and what the port cannot hold is refused by name. ADR-0019 PC-D25."""

from __future__ import annotations

import pytest

from ag.adapters.arcpy.support.geometry_values import (
    WKB_TOKEN,
    geometry_from_wkb,
    is_null_shape,
)
from ag.ports.errors import PortContractError
from ag.ports.geometry import Geometry, GeometryKind
from tests.support import wkb
from tests.support.cases import CRS

SQUARE = ((0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0), (0.0, 0.0))
HOLE = ((1.0, 1.0), (2.0, 1.0), (2.0, 2.0), (1.0, 2.0), (1.0, 1.0))
KINDS = [
    Geometry.point(1.5, 2.5, crs=CRS),
    Geometry.linestring(((0.0, 0.0), (1.0, 1.0), (2.0, 0.0)), crs=CRS),
    Geometry(GeometryKind.POLYGON, (SQUARE, HOLE), CRS),
    Geometry(GeometryKind.MULTIPOINT, (((0.0, 2.0),), ((1.0, 2.0),)), CRS),
    Geometry(
        GeometryKind.MULTILINESTRING,
        (((0.0, 1.0), (1.0, 1.0)), ((2.0, 1.0), (3.0, 1.0))),
        CRS,
    ),
    Geometry(GeometryKind.MULTIPOLYGON, (SQUARE, HOLE), CRS),
]


@pytest.mark.parametrize("order", ["<", ">"], ids=["little-endian", "big-endian"])
@pytest.mark.parametrize("geometry", KINDS, ids=[g.kind.value for g in KINDS])
def test_every_kind_round_trips(geometry: Geometry, order: str) -> None:
    data = wkb.to_wkb(geometry, order=order)
    assert geometry_from_wkb(data, crs=CRS, where="row") == geometry
    assert geometry_from_wkb(bytearray(data), crs=CRS, where="row") == geometry
    assert geometry_from_wkb(memoryview(data), crs=CRS, where="row") == geometry
    assert not is_null_shape(data)


@pytest.mark.parametrize(
    "value",
    [None, *(wkb.empty(code) for code in range(1, 7))],
    ids=[
        "none",
        "point",
        "linestring",
        "polygon",
        "multipoint",
        "multiline",
        "multipoly",
    ],
)
def test_a_null_or_empty_shape_is_none_and_null(value: object) -> None:
    assert geometry_from_wkb(value, crs=CRS, where="row") is None
    assert is_null_shape(value)


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (wkb.typed(1001), "WKB type 1001"),
        (wkb.typed(2001), "WKB type 2001"),
        (wkb.typed(0x80000001), "WKB type 2147483649"),
        (wkb.typed(8), "WKB type 8"),
        (wkb.multipolygon_with_hole(), "multipolygon member with holes"),
    ],
    ids=["z", "m", "ewkb-z", "circular-string", "member-with-hole"],
)
def test_what_the_port_cannot_hold_is_refused_naming_the_row(
    data: bytes, message: str
) -> None:
    with pytest.raises(PortContractError, match=message) as caught:
        geometry_from_wkb(data, crs=CRS, where="'roads' row 3")
    assert "'roads' row 3" in str(caught.value)


def test_an_unreadable_type_is_not_null() -> None:
    assert not is_null_shape(wkb.typed(1001))


def test_a_value_that_is_not_bytes_is_an_adapter_defect() -> None:
    with pytest.raises(TypeError, match=WKB_TOKEN):
        geometry_from_wkb("POINT (1 2)", crs=CRS, where="row")
