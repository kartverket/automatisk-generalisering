"""`select` and `explode_multipart` against the port's contract, on every adapter.

What: `select` keeps the TRUE rows with their attributes and coordinates and leaves the
input's native indices as they were; `LIKE` and a date comparison behave as the port
specifies; the parents table partitions the children as the case expects, through native
indices; a `MINT` method on a non-dense input reports the pre-call indices and leaves
them unchanged; a null shape and a table input are refused before anything is written.
Geometry is compared by coordinates here and by kind in the table-ops module, so the one
question an engine answers about kinds fails in one place. ADR-0017 RS-D16, ADR-0019
PC-D5, PC-D15, PC-D28.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from ag.core.handles import ScratchHandle
from ag.core.types import DataType
from ag.ports import CHILD_ID, PARENT_ID, Attr, Comparison, Predicate, Row
from ag.ports.attributes import FieldName
from ag.ports.errors import (
    EmptyGeometryError,
    ParentsUnavailableError,
    PortContractError,
)
from ag.ports.geometry import Geometry, Ring
from ag.ports.geometry_ops import GeometryOps
from tests.conformance.conftest import Adapter
from tests.support.cases import (
    DatasetCase,
    lookup,
    multilines,
    multilines_children,
    multipoints,
    multipoints_children,
    roads,
)

Children = dict[int, frozenset[Geometry]]
PARTITIONS: list[tuple[DatasetCase, Children]] = [
    (multilines(), multilines_children()),
    (multipoints(), multipoints_children()),
]
ROAD_FIELDS: tuple[FieldName, ...] = ("name", "rank", "width_m", "surveyed")
EVERY_ROW: Predicate = Attr.is_null("name") | ~Attr.is_null("name")


def _rows(
    adapter: Adapter, handle: ScratchHandle, fields: tuple[FieldName, ...]
) -> list[Row]:
    return list(adapter.table_ops.read_rows(input=handle, fields=fields))


def _names(adapter: Adapter, handle: ScratchHandle) -> set[str]:
    return {str(row.attributes["name"]) for row in _rows(adapter, handle, ("name",))}


def _coords(geometry: Geometry | None) -> tuple[Ring, ...] | None:
    return None if geometry is None else geometry.parts


def _pairs(adapter: Adapter, handle: ScratchHandle) -> set[tuple[int, int]]:
    found: set[tuple[int, int]] = set()
    for row in _rows(adapter, handle, (PARENT_ID, CHILD_ID)):
        parent, child = row.attributes[PARENT_ID], row.attributes[CHILD_ID]
        assert isinstance(parent, int) and isinstance(child, int)
        found.add((parent, child))
    return found


def _selected(
    adapter: Adapter, seeded_handle: ScratchHandle, where: Predicate, name: str
) -> set[str]:
    output = adapter.handle(name)
    adapter.geometry_ops.select(input=seeded_handle, where=where, output=output)
    return _names(adapter, output)


def test_select_keeps_the_true_rows_and_leaves_the_input_indices(
    adapter: Adapter,
) -> None:
    case = roads()
    seeded = adapter.seed(case)
    output = adapter.handle("kept")
    adapter.geometry_ops.select(
        input=seeded.handle, where=Attr.cmp("rank", Comparison.GE, 2), output=output
    )
    kept = sorted(
        _rows(adapter, output, ROAD_FIELDS), key=lambda r: str(r.attributes["name"])
    )
    expected = sorted(
        (case.rows[2], case.rows[3]), key=lambda r: str(r.attributes["name"])
    )
    assert [dict(r.attributes) for r in kept] == [dict(r.attributes) for r in expected]
    assert [_coords(r.geometry) for r in kept] == [
        _coords(r.geometry) for r in expected
    ]
    assert adapter.indices(seeded.handle) == seeded.indices


def test_select_under_a_negation_excludes_the_null_row_until_is_null_is_added(
    adapter: Adapter,
) -> None:
    seeded = adapter.seed(roads())
    not_one = ~Attr.cmp("rank", Comparison.EQ, 1)
    assert _selected(adapter, seeded.handle, not_one, "a") == {"Gamma", "delta"}
    assert _selected(adapter, seeded.handle, not_one | Attr.is_null("rank"), "b") == {
        "beta_road",
        "Gamma",
        "delta",
    }


def test_like_is_case_sensitive_with_percent_and_underscore_as_its_wildcards(
    adapter: Adapter,
) -> None:
    seeded = adapter.seed(roads())

    def like(pattern: str) -> Predicate:
        return Attr.cmp("name", Comparison.LIKE, pattern)

    assert _selected(adapter, seeded.handle, like("%road"), "a") == {
        "Alpha road",
        "beta_road",
    }
    assert _selected(adapter, seeded.handle, like("alpha%"), "b") == set()
    assert _selected(adapter, seeded.handle, like("G_mma"), "c") == {"Gamma"}


def test_a_date_comparison_selects_to_the_whole_second(adapter: Adapter) -> None:
    seeded = adapter.seed(roads())
    since = Attr.cmp("surveyed", Comparison.GE, datetime(2024, 1, 1))
    assert _selected(adapter, seeded.handle, since, "a") == {"Alpha road", "Gamma"}


def test_select_on_a_table_keeps_the_matching_rows(adapter: Adapter) -> None:
    seeded = adapter.seed(lookup())
    output = adapter.handle("one", DataType.TABLE)
    adapter.geometry_ops.select(
        input=seeded.handle, where=Attr.cmp("code", Comparison.EQ, 1), output=output
    )
    rows = _rows(adapter, output, ("code", "label"))
    assert [dict(r.attributes) for r in rows] == [{"code": 1, "label": "one"}]
    assert all(r.geometry is None for r in rows)


def test_select_refuses_two_handles_on_one_path(adapter: Adapter) -> None:
    seeded = adapter.seed(roads())
    with pytest.raises(PortContractError, match="both name"):
        adapter.geometry_ops.select(
            input=seeded.handle, where=EVERY_ROW, output=seeded.handle
        )


@pytest.mark.parametrize(("case", "children_of"), PARTITIONS, ids=["lines", "points"])
def test_parents_pairs_match_the_expected_partition_through_native_indices(
    adapter: Adapter, case: DatasetCase, children_of: Children
) -> None:
    seeded = adapter.seed(case)
    output = adapter.handle("exploded")
    parents = adapter.handle("pairs", DataType.TABLE)
    if GeometryOps.explode_multipart not in adapter.capabilities.parents_for:
        with pytest.raises(ParentsUnavailableError):
            adapter.geometry_ops.explode_multipart(
                input=seeded.handle, output=output, parents=parents
            )
        return
    adapter.geometry_ops.explode_multipart(
        input=seeded.handle, output=output, parents=parents
    )
    pairs = _pairs(adapter, parents)
    # Two reads of one unchanged dataset, in the adapter's one order: index beside row.
    children = dict(
        zip(adapter.indices(output), _rows(adapter, output, ("name",)), strict=True)
    )
    assert len(pairs) == len(children) == sum(len(g) for g in children_of.values())
    for position, geometries in children_of.items():
        parent = seeded.index_of(position)
        child_ids = {child for p, child in pairs if p == parent}
        assert {_coords(children[c].geometry) for c in child_ids} == {
            g.parts for g in geometries
        }
        for child in child_ids:
            assert dict(children[child].attributes) == dict(
                case.rows[position - 1].attributes
            )
    assert {parent for parent, _ in pairs} == set(seeded.indices)
    assert adapter.indices(seeded.handle) == seeded.indices


def test_explode_without_parents_writes_the_children(adapter: Adapter) -> None:
    seeded = adapter.seed(multilines())
    output = adapter.handle("exploded")
    adapter.geometry_ops.explode_multipart(input=seeded.handle, output=output)
    children = _rows(adapter, output, ("name",))
    assert len(children) == sum(len(g) for g in multilines_children().values())
    assert {_coords(r.geometry) for r in children} == {
        g.parts for geometries in multilines_children().values() for g in geometries
    }
    assert adapter.indices(seeded.handle) == seeded.indices


def test_a_mint_method_on_a_non_dense_input_reports_the_pre_call_indices_unchanged(
    adapter: Adapter,
) -> None:
    case = multilines()
    seeded = adapter.seed_non_dense(case, drop={2})
    assert set(seeded.indices) != {1, 2}, "the setup must not hand positions back"
    output = adapter.handle("exploded")
    parents = adapter.handle("pairs", DataType.TABLE)
    adapter.geometry_ops.explode_multipart(
        input=seeded.handle, output=output, parents=parents
    )
    pairs = _pairs(adapter, parents)
    assert {parent for parent, _ in pairs} == set(seeded.indices)
    assert len(pairs) == len(multilines_children()[1]) + len(multilines_children()[3])
    assert adapter.indices(seeded.handle) == seeded.indices
    kept = adapter.handle("kept")
    adapter.geometry_ops.select(input=seeded.handle, where=EVERY_ROW, output=kept)
    assert _names(adapter, kept) == {"a", "e"}
    assert adapter.indices(seeded.handle) == seeded.indices


def test_explode_refuses_a_null_shape_before_anything_is_written(
    adapter: Adapter,
) -> None:
    seeded = adapter.seed(roads())
    with pytest.raises(EmptyGeometryError) as caught:
        adapter.geometry_ops.explode_multipart(
            input=seeded.handle,
            output=adapter.handle("exploded"),
            parents=adapter.handle("pairs", DataType.TABLE),
        )
    assert caught.value.context.row_indices == (seeded.index_of(4),)
    assert adapter.indices(seeded.handle) == seeded.indices


def test_explode_refuses_a_table_input(adapter: Adapter) -> None:
    seeded = adapter.seed(lookup())
    with pytest.raises(PortContractError, match="feature class"):
        adapter.geometry_ops.explode_multipart(
            input=seeded.handle, output=adapter.handle("exploded", DataType.TABLE)
        )
