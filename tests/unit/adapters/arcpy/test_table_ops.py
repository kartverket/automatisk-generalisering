"""`read_rows` through the session on the fake engine: exactly the named fields with
the geometry, laziness under one guard, and what is refused before the cursor opens.
ADR-0018 AR-D23, ADR-0019 PC-D22."""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime

import pytest

from ag.adapters.arcpy.session import ArcpySession
from ag.adapters.arcpy.support.dataset_schema import WHOLE_SECOND_PRECISION
from ag.adapters.arcpy.table_ops import ArcpyTableOps
from ag.core.handles import ScratchHandle
from ag.core.types import DataType
from ag.ports.errors import EngineError, PortContractError
from tests.support.cases import lookup, roads
from tests.support.fake_arcpy import FakeEngine, FakeField, seed


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


def test_a_date_from_a_field_that_holds_the_fraction_is_read_as_it_is(
    engine: FakeEngine, session: ArcpySession
) -> None:
    seed(engine, roads(), path="roads")
    stored = datetime(2015, 1, 6, 7, 11, 36, 500)
    engine.datasets["roads"].rows[1]["surveyed"] = stored
    rows = list(
        ArcpyTableOps(session=session).read_rows(
            input=handle("roads"), fields=("surveyed",)
        )
    )
    assert rows[1].attributes["surveyed"] == stored


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
