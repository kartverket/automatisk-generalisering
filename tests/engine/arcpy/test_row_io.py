"""What `row_io.py` and the WKB codec expect of the engine's cursors: an empty shape
arrives as None or as an empty well-known binary and reads as a null geometry; a date
written with a fraction is either held to the second by the engine or refused by
`read_rows`, never truncated by the adapter. ADR-0019 PC-D17, PC-D25.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from ag.adapters.arcpy.support.dataset_writer import insert_rows
from ag.adapters.arcpy.support.geometry_values import WKB_TOKEN, is_null_shape
from ag.adapters.arcpy.table_ops import ArcpyTableOps
from ag.ports.errors import PortContractError
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


def test_a_date_with_a_fraction_is_held_to_the_second_by_the_engine_or_refused(
    pro: Pro,
) -> None:
    seeded = pro.seed(roads())
    path = str(seeded.handle.path)
    insert_rows(
        pro.session,
        path=path,
        tokens=("name", "surveyed"),
        rows=[("frac", datetime(2024, 1, 1, 12, 0, 0, 500000))],
    )
    cells = pro.read_cells(path=path, tokens=("surveyed",), where="\"name\" = 'frac'")
    (stored,) = cells[0]
    assert isinstance(stored, datetime), stored
    ops = ArcpyTableOps(session=pro.session)
    if stored.microsecond == 0:
        found = [
            row
            for row in ops.read_rows(input=seeded.handle, fields=("name", "surveyed"))
            if row.attributes["name"] == "frac"
        ]
        assert [row.attributes["surveyed"] for row in found] == [
            datetime(2024, 1, 1, 12)
        ]
    else:
        with pytest.raises(PortContractError, match="sub-second"):
            list(ops.read_rows(input=seeded.handle, fields=("name", "surveyed")))
