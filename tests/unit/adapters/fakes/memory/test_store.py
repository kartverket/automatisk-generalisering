"""`MemoryStore`: native indices, the write checks, and what a read returns.

The native index is asserted on the store directly, because no port method exposes it;
that is a gap the conformance suite closes once a port method does. ADR-0019 PC-D26.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import MappingProxyType

import pytest

from ag.adapters.fakes.memory.store import MemoryStore
from ag.core.errors import InjectionError
from ag.core.handles import ScratchHandle
from ag.core.types import DataType
from ag.ports import AttributeValue, FieldName, Geometry, Row
from ag.ports.errors import PortContractError
from tests.support.cases import CRS, lookup, roads
from tests.support.memory import memory_handle, seed


def _road(**overrides: AttributeValue) -> Row:
    attributes: dict[FieldName, AttributeValue] = {
        "name": "Alpha road",
        "rank": 1,
        "width_m": 2.5,
        "surveyed": datetime(2024, 1, 1),
    }
    attributes.update(overrides)
    return Row(attributes, Geometry.linestring(((0.0, 0.0), (1.0, 1.0)), crs=CRS))


def test_indices_are_dense_from_one_and_a_second_write_takes_the_next_range() -> None:
    store = MemoryStore()
    first = seed(store, roads())
    second = seed(store, lookup())
    assert first.indices == (1, 2, 3, 4)
    assert second.indices == (5, 6)
    assert tuple(store.read(first.handle).rows) == first.indices


def test_rewriting_a_dataset_assigns_fresh_indices() -> None:
    store = MemoryStore()
    case = roads()
    first = seed(store, case)
    second = seed(store, case)
    assert second.handle == first.handle
    assert set(first.indices).isdisjoint(second.indices)
    assert tuple(store.read(second.handle).rows) == second.indices


def test_reading_and_writing_elsewhere_leave_the_index_unchanged() -> None:
    store = MemoryStore()
    seeded = seed(store, roads())
    store.read(seeded.handle)
    seed(store, lookup())
    assert tuple(store.read(seeded.handle).rows) == seeded.indices


def test_an_unmaterialised_handle_is_an_injection_error() -> None:
    store = MemoryStore()
    declared = ScratchHandle(name="roads", namespace="probe")
    with pytest.raises(InjectionError):
        store.read(declared)
    with pytest.raises(InjectionError):
        store.write(declared, schema=roads().schema, rows=())


def test_a_handle_nothing_was_written_to_is_a_contract_error() -> None:
    with pytest.raises(PortContractError, match="names no dataset"):
        MemoryStore().read(memory_handle("missing"))


def test_a_table_handle_refuses_a_feature_class_schema() -> None:
    with pytest.raises(PortContractError, match="names one kind of dataset"):
        MemoryStore().write(
            memory_handle("roads", DataType.TABLE), schema=roads().schema, rows=()
        )


@pytest.mark.parametrize(
    ("row", "reason"),
    [
        (Row({"name": "a", "rank": 1, "width_m": 1.0}), "missing"),
        (_road(extra="x"), "unexpected"),
        (_road(rank="1"), "is not an int"),
        (_road(rank=1.5), "is not an int"),
        (_road(rank=True), "is a bool"),
        (_road(rank=2**31), "outside the long range"),
        (_road(width_m="wide"), "is not a number"),
        (_road(name="x" * 21), "holds at most 20"),
        (_road(surveyed="2024-01-01"), "is not a datetime"),
        (_road(surveyed=datetime(2024, 1, 1, tzinfo=UTC)), "aware datetime"),
        (
            Row(_road().attributes, Geometry.point(0.0, 0.0, crs="EPSG:4326")),
            "schema declares",
        ),
    ],
    ids=[
        "missing-field",
        "extra-field",
        "str-on-long",
        "float-on-long",
        "bool-on-long",
        "long-overflow",
        "str-on-double",
        "text-too-long",
        "str-on-date",
        "aware-datetime",
        "wrong-crs",
    ],
)
def test_a_row_that_does_not_fit_the_schema_is_refused(row: Row, reason: str) -> None:
    with pytest.raises(PortContractError, match=reason):
        MemoryStore().write(memory_handle("roads"), schema=roads().schema, rows=[row])


def test_short_overflow_and_geometry_on_a_table_are_refused() -> None:
    store = MemoryStore()
    table = memory_handle("lookup", DataType.TABLE)
    with pytest.raises(PortContractError, match="outside the short range"):
        store.write(
            table, schema=lookup().schema, rows=[Row({"code": 40_000, "label": "x"})]
        )
    with pytest.raises(PortContractError, match="has none"):
        store.write(
            table,
            schema=lookup().schema,
            rows=[Row({"code": 1, "label": "x"}, Geometry.point(0.0, 0.0, crs=CRS))],
        )


def test_an_int_fits_a_double_field_and_none_fits_every_field() -> None:
    store = MemoryStore()
    row = _road(rank=None, width_m=2, surveyed=None)
    store.write(memory_handle("roads"), schema=roads().schema, rows=[row])


def test_a_refused_write_replaces_nothing() -> None:
    store = MemoryStore()
    seeded = seed(store, roads())
    with pytest.raises(PortContractError):
        store.write(
            seeded.handle, schema=roads().schema, rows=[_road(), _road(rank=True)]
        )
    assert tuple(store.read(seeded.handle).rows) == seeded.indices


def test_mutating_the_callers_mapping_after_a_write_leaves_the_stored_row_unchanged() -> (
    None
):
    store = MemoryStore()
    table = memory_handle("lookup", DataType.TABLE)
    attributes: dict[FieldName, AttributeValue] = {"code": 1, "label": "one"}
    store.write(table, schema=lookup().schema, rows=[Row(attributes)])
    attributes["code"] = True
    attributes["extra"] = "x"
    stored = next(iter(store.read(table).rows.values()))
    assert dict(stored.attributes) == {"code": 1, "label": "one"}
    assert isinstance(stored.attributes, MappingProxyType)
