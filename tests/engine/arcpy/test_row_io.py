"""What `row_io.py` and the WKB codec expect of the engine's cursors: an empty shape
arrives as None or as an empty well-known binary and reads as a null geometry; a date
field at the engine's default precision holds whole seconds and rounds a fraction
written to it (12:00:00.5 arrives as 12:00:01), `describe` names it a whole-second field
and `read_rows` reads it to the second; a date field the adapter creates is migrated to
the precision that holds the fraction, and a value written with microseconds reads back
within a millisecond of itself. ADR-0019 PC-D17, PC-D25.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from ag.adapters.arcpy.support.dataset_schema import describe
from ag.adapters.arcpy.support.dataset_writer import ADD_FIELD_TYPES, insert_rows
from ag.adapters.arcpy.support.geometry_values import WKB_TOKEN, is_null_shape
from ag.adapters.arcpy.table_ops import ArcpyTableOps
from ag.ports import FieldType
from tests.engine.arcpy.conftest import Pro
from tests.support import wkb
from tests.support.cases import multilines, roads

pytestmark = pytest.mark.arcpy


def test_an_empty_shape_arrives_as_none_or_an_empty_wkb_and_reads_as_null(
    pro: Pro,
) -> None:
    seeded = pro.seed(multilines())
    path = str(seeded.handle.path)
    insert_rows(
        pro.session,
        path=path,
        tokens=("name", WKB_TOKEN),
        rows=[("z", wkb.empty(wkb.LINESTRING))],
    )
    cells = pro.read_cells(path=path, tokens=(WKB_TOKEN,), where="\"name\" = 'z'")
    assert len(cells) == 1
    (shape,) = cells[0]
    assert shape is None or is_null_shape(shape), shape
    rows = ArcpyTableOps(session=pro.session).read_rows(
        input=seeded.handle, fields=("name",)
    )
    assert [row.geometry for row in rows if row.attributes["name"] == "z"] == [None]


def test_a_field_at_the_default_precision_rounds_and_is_read_to_the_second(
    pro: Pro,
) -> None:
    """A bare AddField DATE, not the adapter's `add_fields`, stands in for a raw source."""
    seeded = pro.seed(roads())
    path = str(seeded.handle.path)
    pro.session.run_tool(
        "management.AddField",
        in_table=path,
        field_name="raw_stamp",
        field_type=ADD_FIELD_TYPES[FieldType.DATE],
    )
    insert_rows(
        pro.session,
        path=path,
        tokens=("name", "raw_stamp"),
        rows=[("frac", datetime(2024, 1, 1, 12, 0, 0, 500000))],
    )
    cells = pro.read_cells(path=path, tokens=("raw_stamp",), where="\"name\" = 'frac'")
    (stored,) = cells[0]
    assert stored == datetime(2024, 1, 1, 12, 0, 1), stored
    described = describe(pro.session, path)
    assert described.whole_second_fields == {"raw_stamp"}
    found = [
        row
        for row in ArcpyTableOps(session=pro.session).read_rows(
            input=seeded.handle, fields=("name", "raw_stamp")
        )
        if row.attributes["name"] == "frac"
    ]
    assert [row.attributes["raw_stamp"] for row in found] == [stored]


def test_a_field_the_adapter_creates_holds_a_fraction_to_within_a_millisecond(
    pro: Pro,
) -> None:
    seeded = pro.seed(roads())
    path = str(seeded.handle.path)
    written = datetime(2024, 1, 1, 12, 0, 0, 500123)
    insert_rows(
        pro.session, path=path, tokens=("name", "surveyed"), rows=[("frac", written)]
    )
    found = [
        row
        for row in ArcpyTableOps(session=pro.session).read_rows(
            input=seeded.handle, fields=("name", "surveyed")
        )
        if row.attributes["name"] == "frac"
    ]
    (stored,) = [row.attributes["surveyed"] for row in found]
    assert isinstance(stored, datetime)
    assert abs(stored - written) <= timedelta(milliseconds=1), stored
    assert stored.microsecond != 0, "the fraction was lost to a whole-second store"
