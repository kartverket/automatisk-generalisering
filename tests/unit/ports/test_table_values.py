"""The table vocabulary: fields, schemas and rows."""

from __future__ import annotations

from datetime import date

import pytest

from ag.core.types import DataType
from ag.ports import Field, FieldType, Geometry, Row, Schema

CRS = "EPSG:25833"


def test_a_text_field_needs_a_length_and_no_other_type_takes_one() -> None:
    assert Field("name", FieldType.TEXT, 50).length == 50
    assert Field("count", FieldType.LONG).length is None
    with pytest.raises(ValueError, match="needs a length"):
        Field("name", FieldType.TEXT)
    with pytest.raises(ValueError, match="takes no length"):
        Field("count", FieldType.LONG, 10)


def test_a_feature_class_schema_needs_a_crs_and_a_table_does_not() -> None:
    fields = (Field("count", FieldType.LONG),)
    assert Schema(fields, geometry_crs=CRS).geometry_crs == CRS
    assert Schema(fields, data_type=DataType.TABLE).geometry_crs is None
    with pytest.raises(ValueError, match="needs geometry_crs"):
        Schema(fields)


def test_a_row_holds_attributes_and_an_optional_geometry() -> None:
    spatial = Row(
        {"count": 3, "when": date(2026, 1, 1)}, Geometry.point(1.0, 2.0, crs=CRS)
    )
    tabular = Row({"code": "x", "ratio": 0.5, "note": None})
    assert spatial.geometry is not None and spatial.geometry.coords == ((1.0, 2.0),)
    assert tabular.geometry is None
    assert tabular.attributes["note"] is None


def test_a_row_is_frozen_and_uses_slots() -> None:
    row = Row({"count": 3})
    with pytest.raises(AttributeError):
        row.geometry = None  # type: ignore[misc]
    assert not hasattr(row, "__dict__")
    assert set(Row.__slots__) == {"attributes", "geometry"}


def test_field_types_are_the_ones_the_pipelines_declare() -> None:
    assert [kind.value for kind in FieldType] == [
        "short",
        "long",
        "double",
        "text",
        "date",
    ]
