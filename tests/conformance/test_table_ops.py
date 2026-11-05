"""`read_rows` against the port's contract, on every adapter.

What: every field type round-trips as the value the case wrote, dates to the whole
second; every geometry kind the port holds comes back as the kind that was written, which
is the one question about kinds an engine answers and the one place it fails; an
undeclared field is refused before any row is read; a table has no geometry and an empty
field list yields empty attributes. ADR-0019 PC-D17, PC-D22, PC-D25.
"""

from __future__ import annotations

import pytest

from ag.core.handles import ScratchHandle
from ag.ports import Row
from ag.ports.attributes import FieldName
from ag.ports.errors import PortContractError
from tests.conformance.conftest import Adapter
from tests.support.cases import (
    DatasetCase,
    lookup,
    multilines,
    multipoints,
    points,
    polygons,
    roads,
)

KIND_CASES = [roads(), multilines(), multipoints(), points(), polygons()]


def _rows(
    adapter: Adapter, handle: ScratchHandle, fields: tuple[FieldName, ...]
) -> list[Row]:
    return list(adapter.table_ops.read_rows(input=handle, fields=fields))


@pytest.mark.parametrize("case", [roads(), lookup()], ids=["feature-class", "table"])
def test_read_rows_round_trips_every_field_type(
    adapter: Adapter, case: DatasetCase
) -> None:
    seeded = adapter.seed(case)
    fields = tuple(field.name for field in case.schema.fields)
    rows = _rows(adapter, seeded.handle, fields)
    assert [dict(r.attributes) for r in rows] == [dict(r.attributes) for r in case.rows]


@pytest.mark.parametrize("case", KIND_CASES, ids=[c.name for c in KIND_CASES])
def test_read_rows_round_trips_each_geometry_kind(
    adapter: Adapter, case: DatasetCase
) -> None:
    seeded = adapter.seed(case)
    rows = _rows(adapter, seeded.handle, ("name",))
    assert [r.geometry for r in rows] == [r.geometry for r in case.rows]


def test_read_rows_refuses_an_undeclared_field_before_reading(adapter: Adapter) -> None:
    seeded = adapter.seed(roads())
    with pytest.raises(PortContractError, match="colour"):
        list(adapter.table_ops.read_rows(input=seeded.handle, fields=("colour",)))


def test_read_rows_of_a_table_has_no_geometry_and_no_fields_yields_empty_attributes(
    adapter: Adapter,
) -> None:
    seeded = adapter.seed(lookup())
    rows = _rows(adapter, seeded.handle, ("label",))
    assert [dict(r.attributes) for r in rows] == [{"label": "one"}, {"label": "two"}]
    assert all(r.geometry is None for r in rows)
    assert [dict(r.attributes) for r in _rows(adapter, seeded.handle, ())] == [{}, {}]
