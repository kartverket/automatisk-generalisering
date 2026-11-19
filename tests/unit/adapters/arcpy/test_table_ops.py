"""`read_rows` through the session on the fake engine: exactly the named fields with
the geometry, laziness under one guard, and what is refused before the cursor opens.
The catalog: presence through the engine's own call, the kind after presence, and a
workspace created once at the path the caller spells, with every refusal before the
tool. ADR-0018 AR-D23, ADR-0019 PC-D22, PC-D31, PC-D32."""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime

import pytest

from ag.adapters.arcpy.session import ArcpySession
from ag.adapters.arcpy.support.dataset_schema import WHOLE_SECOND_PRECISION
from ag.adapters.arcpy.table_ops import ArcpyTableOps
from ag.adapters.arcpy.table_ops.catalog import FILE_GDB_TOOL
from ag.core.handles import ScratchHandle
from ag.core.types import DataType
from ag.ports.errors import EngineError, PortContractError
from ag.ports.workspace_format import WorkspaceFormat
from tests.support.cases import lookup, roads
from tests.support.fake_arcpy import (
    FILE_GDB_PROG_ID,
    FILE_WORKSPACE,
    MEMORY_WORKSPACE,
    FakeDataset,
    FakeEngine,
    FakeField,
    seed,
)

RASTER = "RasterDataset"
"""An engine `dataType` no port method takes, as a test stands one in."""


def handle(path: str, data_type: DataType = DataType.FEATURE_CLASS) -> ScratchHandle:
    return ScratchHandle(name=path, data_type=data_type, namespace="t").materialize(
        path
    )


def test_read_rows_returns_exactly_the_named_fields_and_the_geometry(
    engine: FakeEngine, session: ArcpySession
) -> None:
    case = roads()
    seed(engine, case, path="roads")
    rows = list(
        ArcpyTableOps(session=session).read_rows(
            input=handle("roads"), fields=("rank", "name")
        )
    )
    assert [tuple(row.attributes) for row in rows] == [("rank", "name")] * 4
    assert [row.attributes["name"] for row in rows] == [
        r.attributes["name"] for r in case.rows
    ]
    assert [row.geometry for row in rows] == [r.geometry for r in case.rows]


def test_read_rows_of_a_table_has_no_geometry_and_no_fields_means_none(
    engine: FakeEngine, session: ArcpySession
) -> None:
    seed(engine, lookup(), path="lookup")
    ops = ArcpyTableOps(session=session)
    rows = list(
        ops.read_rows(input=handle("lookup", DataType.TABLE), fields=("label",))
    )
    assert [dict(row.attributes) for row in rows] == [
        {"label": "one"},
        {"label": "two"},
    ]
    assert all(row.geometry is None for row in rows)
    bare = ops.read_rows(input=handle("lookup", DataType.TABLE), fields=())
    assert [dict(row.attributes) for row in bare] == [{}, {}]


def test_read_rows_is_lazy_and_closes_the_cursor_when_abandoned(
    engine: FakeEngine, session: ArcpySession
) -> None:
    seed(engine, roads(), path="roads")
    rows = ArcpyTableOps(session=session).read_rows(
        input=handle("roads"), fields=("name",)
    )
    assert engine.cursors_opened == 0
    iterator = iter(rows)
    first = next(iterator)
    assert first.attributes == {"name": "Alpha road"}
    assert engine.cursors_opened == 1 and engine.cursors_closed == 0
    assert isinstance(iterator, Generator)
    iterator.close()
    assert engine.cursors_closed == 1


@pytest.mark.parametrize(
    ("fields", "message"),
    [(("code", "x"), "'x' is not a field"), (("guid",), "'guid' is a GUID field")],
    ids=["undeclared", "unrepresentable"],
)
def test_read_rows_refuses_a_field_before_the_cursor_opens(
    engine: FakeEngine, session: ArcpySession, fields: tuple[str, ...], message: str
) -> None:
    seed(engine, lookup(), path="lookup")
    engine.datasets["lookup"].fields.append(FakeField("guid", "GUID"))
    with pytest.raises(PortContractError, match=message):
        ArcpyTableOps(session=session).read_rows(
            input=handle("lookup", DataType.TABLE), fields=fields
        )
    assert engine.cursors_opened == 0


def test_a_cursor_failure_mid_read_leaves_as_an_engine_error(
    engine: FakeEngine, session: ArcpySession
) -> None:
    seed(engine, roads(), path="roads")
    engine.fail_at_row = 3
    rows = ArcpyTableOps(session=session).read_rows(
        input=handle("roads"), fields=("name",)
    )
    iterator = iter(rows)
    assert [next(iterator).attributes["name"] for _ in range(2)] == [
        "Alpha road",
        "beta_road",
    ]
    with pytest.raises(EngineError) as caught:
        next(iterator)
    assert caught.value.context.tool == "SearchCursor"
    assert engine.cursors_closed == 1


@pytest.mark.parametrize(
    ("stored", "read"),
    [
        (datetime(2015, 1, 6, 7, 11, 36, 500), datetime(2015, 1, 6, 7, 11, 36)),
        (datetime(2015, 1, 6, 7, 11, 35, 999500), datetime(2015, 1, 6, 7, 11, 36)),
        (datetime(2015, 1, 6, 23, 59, 59, 999999), datetime(2015, 1, 7)),
        (datetime(2015, 1, 6, 7, 11, 36), datetime(2015, 1, 6, 7, 11, 36)),
    ],
    ids=["just-over", "just-under", "over-midnight", "exact"],
)
def test_a_date_from_a_whole_second_store_is_read_to_its_nearest_second(
    engine: FakeEngine, session: ArcpySession, stored: datetime, read: datetime
) -> None:
    """A precision 0 field holds whole seconds in a double, and one value in eight comes
    back a microsecond off; rounding restores the stored second on either side."""
    seed(engine, roads(), path="roads", date_precision=WHOLE_SECOND_PRECISION)
    engine.datasets["roads"].rows[1]["surveyed"] = stored
    rows = list(
        ArcpyTableOps(session=session).read_rows(
            input=handle("roads"), fields=("surveyed",)
        )
    )
    assert rows[1].attributes["surveyed"] == read


@pytest.mark.parametrize(
    ("stored", "read"),
    [
        (
            datetime(2015, 1, 6, 7, 11, 36, 37004),
            datetime(2015, 1, 6, 7, 11, 36, 37000),
        ),
        (
            datetime(2015, 1, 6, 7, 11, 36, 36996),
            datetime(2015, 1, 6, 7, 11, 36, 37000),
        ),
        (datetime(2015, 1, 6, 7, 11, 36, 999600), datetime(2015, 1, 6, 7, 11, 37)),
        (
            datetime(2015, 1, 6, 7, 11, 36, 37000),
            datetime(2015, 1, 6, 7, 11, 36, 37000),
        ),
    ],
    ids=["just-over", "just-under", "over-the-second", "exact"],
)
def test_a_date_from_a_millisecond_store_is_read_to_its_nearest_millisecond(
    engine: FakeEngine, session: ArcpySession, stored: datetime, read: datetime
) -> None:
    """A precision 1 field holds milliseconds, and a fifth of the values come back a few
    microseconds off; rounding restores the stored millisecond."""
    seed(engine, roads(), path="roads")
    engine.datasets["roads"].rows[1]["surveyed"] = stored
    rows = list(
        ArcpyTableOps(session=session).read_rows(
            input=handle("roads"), fields=("surveyed",)
        )
    )
    assert rows[1].attributes["surveyed"] == read


def test_a_cell_of_an_unknown_type_is_an_adapter_defect_not_wrapped(
    engine: FakeEngine, session: ArcpySession
) -> None:
    seed(engine, lookup(), path="lookup")
    engine.datasets["lookup"].rows[1]["label"] = b"bytes"
    rows = iter(
        ArcpyTableOps(session=session).read_rows(
            input=handle("lookup", DataType.TABLE), fields=("label",)
        )
    )
    next(rows)
    with pytest.raises(TypeError, match="'lookup' row 1"):
        next(rows)


def test_exists_answers_a_dataset_a_workspace_and_nothing(
    engine: FakeEngine, session: ArcpySession
) -> None:
    seed(engine, roads(), path="roads")
    ops = ArcpyTableOps(session=session)
    assert ops.exists(input=handle("roads"))
    assert ops.exists(input=handle(FILE_WORKSPACE))
    assert ops.exists(input=handle(MEMORY_WORKSPACE))
    assert not ops.exists(input=handle("absent"))


def test_an_exists_failure_is_an_engine_error_naming_the_call(
    engine: FakeEngine, session: ArcpySession
) -> None:
    engine.failures["Exists"] = "The catalog is unreachable."
    with pytest.raises(EngineError) as caught:
        ArcpyTableOps(session=session).exists(input=handle("roads"))
    assert caught.value.context.tool == "Exists"


def test_data_type_of_reads_the_kind_of_a_feature_class_and_a_table(
    engine: FakeEngine, session: ArcpySession
) -> None:
    seed(engine, roads(), path="roads")
    seed(engine, lookup(), path="lookup")
    ops = ArcpyTableOps(session=session)
    assert ops.data_type_of(input=handle("roads")) is DataType.FEATURE_CLASS
    assert ops.data_type_of(input=handle("lookup", DataType.TABLE)) is DataType.TABLE


@pytest.mark.parametrize(
    ("path", "message"),
    [("raster", RASTER), (FILE_WORKSPACE, "Workspace"), ("absent", "names nothing")],
    ids=["raster", "workspace", "missing"],
)
def test_data_type_of_refuses_any_other_kind_and_a_missing_path(
    engine: FakeEngine, session: ArcpySession, path: str, message: str
) -> None:
    engine.datasets["raster"] = FakeDataset(RASTER, [])
    with pytest.raises(PortContractError, match=message) as caught:
        ArcpyTableOps(session=session).data_type_of(input=handle(path))
    assert caught.value.context.handle == path


def test_create_workspace_hands_the_tool_the_folder_and_the_stem(
    engine: FakeEngine, session: ArcpySession
) -> None:
    fmt = WorkspaceFormat.FILE_GDB
    path = f"/scratch/stage{fmt.suffix}"
    ArcpyTableOps(session=session).create_workspace(path=path, fmt=fmt)
    assert engine.calls == [
        (FILE_GDB_TOOL, {"out_folder_path": "/scratch", "out_name": "stage"})
    ]
    assert engine.workspaces[path] == FILE_GDB_PROG_ID


@pytest.mark.parametrize(
    ("path", "message"),
    [
        ("/scratch/stage", "does not end in"),
        ("/scratch/stage.gpkg", "does not end in"),
        (MEMORY_WORKSPACE, "does not end in"),
        (FILE_WORKSPACE + WorkspaceFormat.FILE_GDB.suffix, "already there"),
        ("roads" + WorkspaceFormat.FILE_GDB.suffix, "already there"),
    ],
    ids=[
        "no-suffix",
        "other-suffix",
        "memory-path",
        "workspace-exists",
        "dataset-exists",
    ],
)
def test_create_workspace_refuses_before_any_tool(
    engine: FakeEngine, session: ArcpySession, path: str, message: str
) -> None:
    suffix = WorkspaceFormat.FILE_GDB.suffix
    engine.workspaces[FILE_WORKSPACE + suffix] = FILE_GDB_PROG_ID
    seed(engine, roads(), path="roads" + suffix)
    with pytest.raises(PortContractError, match=message) as caught:
        ArcpyTableOps(session=session).create_workspace(
            path=path, fmt=WorkspaceFormat.FILE_GDB
        )
    assert caught.value.context.handle == path
    assert engine.calls == []


def test_a_tool_failure_on_create_workspace_is_an_engine_error_naming_the_tool(
    engine: FakeEngine, session: ArcpySession
) -> None:
    engine.failures[FILE_GDB_TOOL] = "ERROR 000210: Cannot create output"
    path = f"/no_such_folder/stage{WorkspaceFormat.FILE_GDB.suffix}"
    with pytest.raises(EngineError) as caught:
        ArcpyTableOps(session=session).create_workspace(
            path=path, fmt=WorkspaceFormat.FILE_GDB
        )
    assert caught.value.context.tool == FILE_GDB_TOOL
    assert "ERROR 000210" in " ".join(caught.value.context.tool_messages)
    assert path not in engine.workspaces
