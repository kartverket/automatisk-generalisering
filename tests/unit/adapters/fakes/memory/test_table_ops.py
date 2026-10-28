"""`read_rows` under the in-memory adapter: exactly the named fields, with geometry.
ADR-0019 PC-D22.
"""

from __future__ import annotations

import pytest

from ag.adapters.fakes.memory.store import MemoryStore
from ag.adapters.fakes.memory.table_ops import MemoryTableOps
from ag.ports.errors import PortContractError
from tests.support.cases import lookup, roads
from tests.support.memory import seed


def test_read_rows_returns_exactly_the_named_fields_and_the_geometry() -> None:
    store = MemoryStore()
    case = roads()
    seeded = seed(store, case)
    rows = list(
        MemoryTableOps(store=store).read_rows(
            input=seeded.handle, fields=("rank", "name")
        )
    )
    assert [tuple(row.attributes) for row in rows] == [("rank", "name")] * 4
    assert [row.attributes["name"] for row in rows] == [
        r.attributes["name"] for r in case.rows
    ]
    assert [row.geometry for row in rows] == [r.geometry for r in case.rows]
    assert tuple(store.read(seeded.handle).rows) == seeded.indices


def test_read_rows_of_a_table_has_no_geometry_and_no_fields_means_none() -> None:
    store = MemoryStore()
    seeded = seed(store, lookup())
    ops = MemoryTableOps(store=store)
    rows = list(ops.read_rows(input=seeded.handle, fields=("label",)))
    assert [dict(row.attributes) for row in rows] == [
        {"label": "one"},
        {"label": "two"},
    ]
    assert all(row.geometry is None for row in rows)
    bare = ops.read_rows(input=seeded.handle, fields=())
    assert [dict(row.attributes) for row in bare] == [{}, {}]


def test_read_rows_refuses_a_field_the_dataset_does_not_declare() -> None:
    store = MemoryStore()
    seeded = seed(store, lookup())
    with pytest.raises(PortContractError, match="are not fields of"):
        MemoryTableOps(store=store).read_rows(input=seeded.handle, fields=("code", "x"))
