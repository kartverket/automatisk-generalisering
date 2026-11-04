"""`select` and `explode_multipart` under the in-memory adapter.

What: `select` preserves the kept rows' attributes and geometry and excludes the NULL
row under a negation; `explode_multipart` with `parents=` writes native-index pairs
matching the expected partition and with `parents=None` writes nothing; the input's
native index is unchanged by both and reassigned by the next write. The index and the
pairs are read from the store directly, because no port method exposes them.
ADR-0017 RS-D16, ADR-0019 PC-D15.
"""

from __future__ import annotations

import pytest

from ag.adapters.fakes.memory.geometry_ops import MemoryGeometryOps
from ag.adapters.fakes.memory.geometry_ops.shape import PARENTS_SCHEMA
from ag.adapters.fakes.memory.store import MemoryStore
from ag.core.types import DataType
from ag.ports import CHILD_ID, PARENT_ID, Attr, Comparison, Intersects, Predicate, Row
from ag.ports.errors import EmptyGeometryError, PortContractError
from tests.support.cases import lookup, parts, parts_children, roads
from tests.support.memory import memory_handle, seed


def _pair(row: Row) -> tuple[int, int]:
    """A parents row as two native indices."""
    parent, child = row.attributes[PARENT_ID], row.attributes[CHILD_ID]
    assert isinstance(parent, int) and isinstance(child, int)
    return parent, child


def test_select_keeps_the_true_rows_with_attributes_and_geometry_and_fresh_indices() -> (
    None
):
    store = MemoryStore()
    case = roads()
    seeded = seed(store, case)
    output = memory_handle("kept")
    MemoryGeometryOps(store=store).select(
        input=seeded.handle, where=Attr.cmp("rank", Comparison.GE, 2), output=output
    )
    kept = store.read(output)
    assert kept.schema == case.schema
    assert list(kept.rows.values()) == [case.rows[2], case.rows[3]]
    assert set(kept.rows).isdisjoint(seeded.indices)
    assert tuple(store.read(seeded.handle).rows) == seeded.indices


def test_select_under_a_negation_excludes_the_null_row_until_is_null_is_added() -> None:
    store = MemoryStore()
    seeded = seed(store, roads())
    ops = MemoryGeometryOps(store=store)
    not_one = ~Attr.cmp("rank", Comparison.EQ, 1)
    ops.select(input=seeded.handle, where=not_one, output=memory_handle("a"))
    ops.select(
        input=seeded.handle,
        where=not_one | Attr.is_null("rank"),
        output=memory_handle("b"),
    )
    names_a = [
        row.attributes["name"] for row in store.read(memory_handle("a")).rows.values()
    ]
    names_b = [
        row.attributes["name"] for row in store.read(memory_handle("b")).rows.values()
    ]
    assert names_a == ["Gamma", "delta"]
    assert names_b == ["beta_road", "Gamma", "delta"]


def test_select_of_every_row_preserves_count_attributes_and_geometry() -> None:
    store = MemoryStore()
    case = roads()
    seeded = seed(store, case)
    output = memory_handle("all")
    MemoryGeometryOps(store=store).select(
        input=seeded.handle,
        where=Attr.is_null("rank") | ~Attr.is_null("rank"),
        output=output,
    )
    assert tuple(store.read(output).rows.values()) == case.rows


@pytest.mark.parametrize(
    "where",
    [
        Attr.raw("rank > 1"),
        Attr.cmp("colour", Comparison.EQ, "red"),
        Attr.cmp("rank", Comparison.LT, 10**12),
        Intersects(memory_handle("other")),
    ],
    ids=["raw", "unknown-field", "long-overflow", "spatial"],
)
def test_a_bad_predicate_on_an_empty_dataset_raises(where: Predicate) -> None:
    store = MemoryStore()
    empty = memory_handle("empty")
    store.write(empty, schema=roads().schema, rows=())
    with pytest.raises(PortContractError):
        MemoryGeometryOps(store=store).select(
            input=empty, where=where, output=memory_handle("out")
        )


def test_a_good_predicate_on_an_empty_dataset_writes_an_empty_output() -> None:
    store = MemoryStore()
    empty = memory_handle("empty")
    store.write(empty, schema=roads().schema, rows=())
    MemoryGeometryOps(store=store).select(
        input=empty, where=Attr.is_null("rank"), output=memory_handle("out")
    )
    assert dict(store.read(memory_handle("out")).rows) == {}


def test_select_refuses_an_output_on_the_input_path() -> None:
    store = MemoryStore()
    seeded = seed(store, roads())
    with pytest.raises(PortContractError, match="both name"):
        MemoryGeometryOps(store=store).select(
            input=seeded.handle, where=Attr.is_null("rank"), output=seeded.handle
        )


def test_explode_without_parents_writes_the_children_and_nothing_else() -> None:
    store = MemoryStore()
    case = parts()
    seeded = seed(store, case)
    output = memory_handle("exploded")
    MemoryGeometryOps(store=store).explode_multipart(input=seeded.handle, output=output)
    children = store.read(output)
    expected = parts_children()
    assert children.schema == case.schema
    assert len(children.rows) == sum(len(g) for g in expected.values())
    assert {row.geometry for row in children.rows.values()} == set().union(
        *expected.values()
    )
    # The counter advanced by exactly the child count: the call wrote nothing else.
    assert (
        seed(store, lookup()).indices[0] == seeded.indices[-1] + len(children.rows) + 1
    )


def test_parents_pairs_match_the_expected_partition_through_native_indices() -> None:
    store = MemoryStore()
    case = parts()
    seeded = seed(store, case)
    output = memory_handle("exploded")
    parents = memory_handle("pairs", DataType.TABLE)
    MemoryGeometryOps(store=store).explode_multipart(
        input=seeded.handle, output=output, parents=parents
    )
    children = store.read(output).rows
    pair_rows = store.read(parents).rows
    pairs = {_pair(row) for row in pair_rows.values()}
    expected = parts_children()
    assert store.read(parents).schema == PARENTS_SCHEMA
    assert len(pair_rows) == len(pairs) == len(children)
    for position, geometries in expected.items():
        parent = seeded.index_of(position)
        child_ids = {child for p, child in pairs if p == parent}
        assert len(child_ids) == len(geometries)
        assert {children[c].geometry for c in child_ids} == geometries
        for child in child_ids:
            assert children[child].attributes == case.rows[position - 1].attributes
    assert len(pairs) == sum(len(g) for g in expected.values())


def test_explode_leaves_the_input_index_unchanged_and_the_next_write_reassigns_it() -> (
    None
):
    store = MemoryStore()
    case = parts()
    seeded = seed(store, case)
    MemoryGeometryOps(store=store).explode_multipart(
        input=seeded.handle,
        output=memory_handle("exploded"),
        parents=memory_handle("pairs", DataType.TABLE),
    )
    assert tuple(store.read(seeded.handle).rows) == seeded.indices
    rewritten = seed(store, case)
    assert set(rewritten.indices).isdisjoint(seeded.indices)


def test_explode_refuses_a_null_geometry_before_writing_whether_or_not_parents_asked() -> (
    None
):
    store = MemoryStore()
    seeded = seed(store, roads())
    ops = MemoryGeometryOps(store=store)
    output = memory_handle("exploded")
    with pytest.raises(EmptyGeometryError) as caught:
        ops.explode_multipart(input=seeded.handle, output=output)
    assert caught.value.context.row_indices == (seeded.index_of(4),)
    with pytest.raises(EmptyGeometryError):
        ops.explode_multipart(
            input=seeded.handle,
            output=output,
            parents=memory_handle("p", DataType.TABLE),
        )
    with pytest.raises(PortContractError, match="names no dataset"):
        store.read(output)


def test_explode_refuses_a_table_input() -> None:
    store = MemoryStore()
    seeded = seed(store, lookup())
    with pytest.raises(PortContractError, match="takes a feature class"):
        MemoryGeometryOps(store=store).explode_multipart(
            input=seeded.handle, output=memory_handle("out", DataType.TABLE)
        )


def test_explode_refuses_two_handles_on_one_path() -> None:
    store = MemoryStore()
    seeded = seed(store, parts())
    ops = MemoryGeometryOps(store=store)
    with pytest.raises(PortContractError, match="both name"):
        ops.explode_multipart(input=seeded.handle, output=seeded.handle)
    with pytest.raises(PortContractError, match="both name"):
        ops.explode_multipart(
            input=seeded.handle,
            output=memory_handle("shared"),
            parents=memory_handle("shared", DataType.TABLE),
        )
