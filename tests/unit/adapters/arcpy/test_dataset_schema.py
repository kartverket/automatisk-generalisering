"""Describe to `Schema` on the fake engine: the type map, the shape-type map, the omitted
engine fields, the unrepresentable fields, the refusals and the one lookup. ADR-0019
PC-D17, PC-D22, PC-D27."""

from __future__ import annotations

import pytest

from ag.adapters.arcpy.session import ArcpySession
from ag.adapters.arcpy.support.dataset_schema import (
    FIELD_TYPES,
    SHAPE_TYPES,
    WHOLE_SECOND_PRECISION,
    declared_field,
    describe,
)
from ag.core.types import DataType
from ag.ports.attributes import Field, FieldType
from ag.ports.errors import EngineError, PortContractError
from ag.ports.geometry import GeometryFamily
from tests.support.cases import (
    DatasetCase,
    lookup,
    multilines,
    multipoints,
    points,
    polygons,
    roads,
)
from tests.support.fake_arcpy import (
    FEATURE_CLASS,
    FakeDataset,
    FakeEngine,
    FakeField,
    seed,
)

FAMILY_CASES = [points(), multipoints(), multilines(), polygons()]


def test_the_five_types_map_and_the_engine_fields_are_left_out(
    engine: FakeEngine, session: ArcpySession
) -> None:
    seed(engine, roads(), path="roads")
    engine.datasets["roads"].area_name = "Shape_Area"

    dataset = describe(session, "roads")

    assert dataset.schema == roads().schema
    assert dataset.schema.data_type is DataType.FEATURE_CLASS
    assert dataset.schema.geometry_crs == "EPSG:25833"
    assert dataset.schema.geometry_family is GeometryFamily.LINE
    assert dataset.engine_fields == {"OBJECTID", "Shape", "Shape_Length", "Shape_Area"}
    assert dataset.all_fields[:4] == ("OBJECTID", "Shape", "Shape_Length", "Shape_Area")
    assert dataset.unrepresentable == {}


def test_a_table_has_no_crs_and_only_the_native_index_as_engine_field(
    engine: FakeEngine, session: ArcpySession
) -> None:
    seed(engine, lookup(), path="lookup")
    dataset = describe(session, "lookup")
    assert dataset.schema == lookup().schema
    assert dataset.schema.geometry_family is None
    assert dataset.engine_fields == {"OBJECTID"}
    assert dataset.schema.fields[0] == Field("code", FieldType.SHORT)


def test_describe_names_the_date_fields_whose_store_holds_whole_seconds(
    engine: FakeEngine, session: ArcpySession
) -> None:
    seed(engine, roads(), path="raw", date_precision=WHOLE_SECOND_PRECISION)
    seed(engine, roads(), path="own")
    assert describe(session, "raw").whole_second_fields == {"surveyed"}
    assert describe(session, "own").whole_second_fields == frozenset()
    assert describe(session, "raw").schema == describe(session, "own").schema


@pytest.mark.parametrize("case", FAMILY_CASES, ids=[c.name for c in FAMILY_CASES])
def test_describe_reads_the_family_from_the_shape_type(
    engine: FakeEngine, session: ArcpySession, case: DatasetCase
) -> None:
    seed(engine, case, path=case.name)
    assert describe(session, case.name).schema == case.schema


def test_an_unrepresentable_field_is_recorded_not_refused_until_named(
    engine: FakeEngine, session: ArcpySession
) -> None:
    seed(engine, roads(), path="roads")
    engine.datasets["roads"].fields += [
        FakeField("GlobalID", "GlobalID"),
        FakeField("big", "BigInteger"),
    ]

    dataset = describe(session, "roads")

    assert dataset.schema == roads().schema
    assert dataset.unrepresentable == {"GlobalID": "GlobalID", "big": "BigInteger"}
    assert declared_field(dataset, "rank") == Field("rank", FieldType.LONG)
    with pytest.raises(PortContractError, match="'big' is a BigInteger field"):
        declared_field(dataset, "big")
    with pytest.raises(PortContractError, match="'colour' is not a field of 'roads'"):
        declared_field(dataset, "colour")


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"has_z": True}, "carries Z values"),
        ({"has_m": True}, "carries M values"),
        ({"epsg": 0}, "no EPSG code"),
        ({"data_type": "FeatureDataset"}, "not a table or a feature class"),
        ({"shape_type": "Annotation"}, "shape type 'Annotation'"),
    ],
    ids=["z", "m", "no-epsg", "not-a-dataset", "unknown-shape-type"],
)
def test_describe_refuses_before_any_row(
    engine: FakeEngine,
    session: ArcpySession,
    change: dict[str, object],
    message: str,
) -> None:
    seed(engine, roads(), path="roads")
    for name, value in change.items():
        setattr(engine.datasets["roads"], name, value)
    with pytest.raises(PortContractError, match=message) as caught:
        describe(session, "roads")
    assert caught.value.context.handle == "roads"
    assert engine.cursors_opened == 0


def test_a_describe_failure_is_an_engine_error_naming_the_call(
    engine: FakeEngine, session: ArcpySession
) -> None:
    with pytest.raises(EngineError) as caught:
        describe(session, "missing")
    assert caught.value.context.tool == "Describe"
    assert type(caught.value.__cause__) is OSError


def test_the_engine_type_names_are_the_expected_spellings() -> None:
    assert set(FIELD_TYPES) == {"SmallInteger", "Integer", "Double", "String", "Date"}
    assert SHAPE_TYPES == {
        "Point": GeometryFamily.POINT,
        "Multipoint": GeometryFamily.MULTIPOINT,
        "Polyline": GeometryFamily.LINE,
        "Polygon": GeometryFamily.POLYGON,
    }


def test_an_empty_engine_name_is_not_an_engine_field(
    engine: FakeEngine, session: ArcpySession
) -> None:
    engine.datasets["fc"] = FakeDataset(FEATURE_CLASS, [FakeField("a", "Double")])
    assert "" not in describe(session, "fc").engine_fields
