"""`select` and `explode_multipart` through the session on the fake engine: which tool
runs with what, what is refused before any tool runs, and the pairs the parents table
gets. The engine's own behaviour is the marked run's to confirm. ADR-0017 RS-D16,
ADR-0018 AR-D23, ADR-0019 PC-D15."""

from __future__ import annotations

import pytest

from ag.adapters.arcpy.geometry_ops import ArcpyGeometryOps
from ag.adapters.arcpy.session import ArcpySession
from ag.adapters.arcpy.support.dataset_schema import OID_TOKEN
from ag.adapters.arcpy.support.geometry_values import WKB_TOKEN, geometry_from_wkb
from ag.core.handles import ScratchHandle
from ag.core.types import DataType
from ag.ports import CHILD_ID, PARENT_ID, Attr, Comparison
from ag.ports.errors import EmptyGeometryError, EngineError, PortContractError
from ag.ports.geometry import Geometry, GeometryKind
from tests.support.cases import CRS, lookup, parts, roads
from tests.support.fake_arcpy import FakeEngine, FakeField, seed
from tests.support.wkb import multipolygon_with_hole, to_wkb


def handle(path: str, data_type: DataType = DataType.FEATURE_CLASS) -> ScratchHandle:
    return ScratchHandle(name=path, data_type=data_type, namespace="t").materialize(
        path
    )


def test_select_runs_the_select_tool_with_the_compiled_clause(
    engine: FakeEngine, session: ArcpySession
) -> None:
    seed(engine, roads(), path="roads")
    ArcpyGeometryOps(session=session).select(
        input=handle("roads"),
        where=Attr.cmp("rank", Comparison.GE, 2),
        output=handle("kept"),
    )
    assert engine.calls == [
        (
            "analysis.Select",
            {
                "in_features": "roads",
                "out_feature_class": "kept",
                "where_clause": '"rank" >= 2',
            },
        )
    ]
    assert "kept" in engine.datasets


def test_select_on_a_table_runs_the_table_form(
    engine: FakeEngine, session: ArcpySession
) -> None:
    seed(engine, lookup(), path="lookup")
    ArcpyGeometryOps(session=session).select(
        input=handle("lookup", DataType.TABLE),
        where=Attr.cmp("code", Comparison.EQ, 1),
        output=handle("one", DataType.TABLE),
    )
    assert engine.tool_names() == ["analysis.TableSelect"]
    assert engine.calls[0][1] == {
        "in_table": "lookup",
        "out_table": "one",
        "where_clause": '"code" = 1',
    }


def test_a_bad_predicate_is_refused_before_any_tool_runs(
    engine: FakeEngine, session: ArcpySession
) -> None:
    seed(engine, roads(), path="roads")
    engine.datasets["roads"].rows.clear()
    with pytest.raises(PortContractError):
        ArcpyGeometryOps(session=session).select(
            input=handle("roads"),
            where=Attr.cmp("colour", Comparison.EQ, "red"),
            output=handle("kept"),
        )
    assert engine.calls == []


def test_select_refuses_an_output_on_the_input_path(
    engine: FakeEngine, session: ArcpySession
) -> None:
    seed(engine, roads(), path="roads")
    with pytest.raises(PortContractError, match="both name"):
        ArcpyGeometryOps(session=session).select(
            input=handle("roads"), where=Attr.is_null("rank"), output=handle("roads")
        )
    assert engine.calls == []


def test_a_tool_failure_leaves_as_an_engine_error_with_its_messages(
    engine: FakeEngine, session: ArcpySession
) -> None:
    seed(engine, roads(), path="roads")
    engine.failures["analysis.Select"] = "ERROR 000210: cannot create"
    with pytest.raises(EngineError) as caught:
        ArcpyGeometryOps(session=session).select(
            input=handle("roads"), where=Attr.is_null("rank"), output=handle("kept")
        )
    assert caught.value.context.tool == "analysis.Select"
    assert "ERROR 000210: cannot create" in caught.value.context.tool_messages


def test_explode_without_parents_runs_the_tool_and_drops_the_reference(
    engine: FakeEngine, session: ArcpySession
) -> None:
    seed(engine, parts(), path="parts")
    ArcpyGeometryOps(session=session).explode_multipart(
        input=handle("parts"), output=handle("exploded")
    )
    assert engine.tool_names() == [
        "management.MultipartToSinglepart",
        "management.DeleteField",
    ]
    assert engine.calls[1][1] == {"in_table": "exploded", "drop_field": "ORIG_FID"}
    output = engine.datasets["exploded"]
    assert [f.name for f in output.fields] == ["name"]
    assert all("ORIG_FID" not in row for row in output.rows)


def test_explode_with_parents_writes_the_pairs_in_native_indices(
    engine: FakeEngine, session: ArcpySession
) -> None:
    case = parts()
    seed(engine, case, path="parts")
    multiline = case.rows[1].geometry
    assert multiline is not None
    engine.children["parts"] = {
        2: [to_wkb(part) for part in _singles(multiline)],
        3: [b"p1", b"p2"],
    }
    ArcpyGeometryOps(session=session).explode_multipart(
        input=handle("parts"),
        output=handle("exploded"),
        parents=handle("ws/pairs", DataType.TABLE),
    )
    assert engine.tool_names() == [
        "management.MultipartToSinglepart",
        "management.CreateTable",
        "management.AddField",
        "management.AddField",
        "management.DeleteField",
    ]
    assert engine.calls[1][1] == {"out_path": "ws", "out_name": "pairs"}
    pairs = engine.datasets["ws/pairs"]
    assert [f.name for f in pairs.fields] == [PARENT_ID, CHILD_ID]
    children = engine.datasets["exploded"].rows
    assert [(r[PARENT_ID], r[CHILD_ID]) for r in pairs.rows] == [
        (1, 1),
        (2, 2),
        (2, 3),
        (2, 4),
        (3, 5),
        (3, 6),
        (4, 7),
    ]
    assert [row[OID_TOKEN] for row in children] == [1, 2, 3, 4, 5, 6, 7]
    assert "ORIG_FID" not in engine.datasets["exploded"].rows[0]


def test_explode_finds_the_reference_by_diff_when_orig_fid_is_taken(
    engine: FakeEngine, session: ArcpySession
) -> None:
    case = parts()
    seed(engine, case, path="parts")
    engine.datasets["parts"].fields.append(FakeField("ORIG_FID", "Integer"))
    for row in engine.datasets["parts"].rows:
        row["ORIG_FID"] = 99
    engine.reference_fields = ["ORIG_FID_1"]
    ArcpyGeometryOps(session=session).explode_multipart(
        input=handle("parts"),
        output=handle("exploded"),
        parents=handle("ws/pairs", DataType.TABLE),
    )
    assert engine.calls[-1][1] == {"in_table": "exploded", "drop_field": "ORIG_FID_1"}
    output = engine.datasets["exploded"]
    assert [f.name for f in output.fields] == ["name", "ORIG_FID"]
    assert all(row["ORIG_FID"] == 99 for row in output.rows)
    assert [r[PARENT_ID] for r in engine.datasets["ws/pairs"].rows] == [1, 2, 3, 4]


def test_the_reference_diff_ignores_the_output_engine_fields(
    engine: FakeEngine, session: ArcpySession
) -> None:
    seed(engine, parts(), path="parts")
    engine.datasets["parts"].length_name = ""
    ArcpyGeometryOps(session=session).explode_multipart(
        input=handle("parts"), output=handle("exploded")
    )
    assert engine.datasets["exploded"].length_name == "Shape_Length"
    assert engine.calls[-1][1] == {"in_table": "exploded", "drop_field": "ORIG_FID"}


def test_a_multipart_polygon_with_holes_explodes_to_polygons_with_their_holes(
    engine: FakeEngine, session: ArcpySession
) -> None:
    seed(engine, parts(), path="lakes")
    lake = engine.datasets["lakes"].rows[0]
    lake[WKB_TOKEN] = multipolygon_with_hole()
    holed = Geometry(
        GeometryKind.POLYGON,
        (
            ((0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0), (0.0, 0.0)),
            ((1.0, 1.0), (2.0, 1.0), (2.0, 2.0), (1.0, 2.0), (1.0, 1.0)),
        ),
        CRS,
    )
    engine.children["lakes"] = {1: [to_wkb(holed)]}
    ArcpyGeometryOps(session=session).explode_multipart(
        input=handle("lakes"),
        output=handle("islands"),
        parents=handle("ws/pairs", DataType.TABLE),
    )
    assert engine.tool_names()[0] == "management.MultipartToSinglepart"
    child = engine.datasets["islands"].rows[0]
    assert geometry_from_wkb(child[WKB_TOKEN], crs=CRS, where="row") == holed
    assert engine.datasets["ws/pairs"].rows[0][PARENT_ID] == 1


def test_a_tool_that_adds_two_fields_is_an_engine_error(
    engine: FakeEngine, session: ArcpySession
) -> None:
    seed(engine, parts(), path="parts")
    engine.reference_fields = ["ORIG_FID", "EXTRA"]
    with pytest.raises(EngineError, match="one reference field was expected") as caught:
        ArcpyGeometryOps(session=session).explode_multipart(
            input=handle("parts"), output=handle("exploded")
        )
    assert caught.value.context.tool == "management.MultipartToSinglepart"
    assert engine.tool_names() == ["management.MultipartToSinglepart"]


def test_explode_refuses_a_null_shape_before_the_tool_whether_or_not_parents_asked(
    engine: FakeEngine, session: ArcpySession
) -> None:
    seed(engine, roads(), path="roads")
    ops = ArcpyGeometryOps(session=session)
    with pytest.raises(EmptyGeometryError) as caught:
        ops.explode_multipart(input=handle("roads"), output=handle("exploded"))
    assert caught.value.context.row_indices == (4,)
    with pytest.raises(EmptyGeometryError):
        ops.explode_multipart(
            input=handle("roads"),
            output=handle("exploded"),
            parents=handle("ws/pairs", DataType.TABLE),
        )
    assert engine.calls == []
    assert engine.cursors_closed == 2


def test_an_empty_shape_counts_as_null(
    engine: FakeEngine, session: ArcpySession
) -> None:
    seed(engine, parts(), path="parts")
    engine.datasets["parts"].rows[0][WKB_TOKEN] = (
        b"\x01\x02\x00\x00\x00\x00\x00\x00\x00"
    )
    with pytest.raises(EmptyGeometryError) as caught:
        ArcpyGeometryOps(session=session).explode_multipart(
            input=handle("parts"), output=handle("exploded")
        )
    assert caught.value.context.row_indices == (1,)


def test_explode_refuses_a_table_and_handles_on_one_path(
    engine: FakeEngine, session: ArcpySession
) -> None:
    seed(engine, lookup(), path="lookup")
    seed(engine, parts(), path="parts")
    ops = ArcpyGeometryOps(session=session)
    with pytest.raises(PortContractError, match="has no geometry to explode"):
        ops.explode_multipart(
            input=handle("lookup", DataType.TABLE), output=handle("exploded")
        )
    with pytest.raises(PortContractError, match="both name"):
        ops.explode_multipart(
            input=handle("parts"),
            output=handle("exploded"),
            parents=handle("exploded", DataType.TABLE),
        )
    assert engine.calls == []


def _singles(geometry: Geometry) -> list[Geometry]:
    return [
        Geometry(GeometryKind.LINESTRING, (part,), geometry.crs)
        for part in geometry.parts
    ]
