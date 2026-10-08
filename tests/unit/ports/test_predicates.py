"""The predicate algebra: constructors that build a tree and fold nothing, and the
structured attribute leaves.

What: `~`, `&` and `|` build `Not`, `And` and `Or` nodes exactly as written, so an adapter
receives the unsimplified shape; the four attribute leaves check their structure at
construction; `Spatial` takes a distance only for `DWITHIN`. The De Morgan rewrite that
ArcPy needs is adapter code and is tested with it. Field names come from the open NVDB
road data: `vegkategori` (road category) and `fartsgrense` (speed limit).
"""

from __future__ import annotations

import pytest

from ag.core.handles import handle
from ag.ports import (
    And,
    Attr,
    Compare,
    Comparison,
    DWithin,
    Intersects,
    IsIn,
    IsNull,
    Not,
    Or,
    Predicate,
    RawAttr,
    Relation,
    Spatial,
    Within,
)


class Layers:
    water = handle()
    railway = handle()


EUROPEAN_ROAD = Attr.cmp("vegkategori", Comparison.EQ, "E")
FAST = Attr.cmp("fartsgrense", Comparison.GT, 80)


# ---------------------------------------------------------------------------
# The operators are constructors
# ---------------------------------------------------------------------------


def test_the_operators_build_a_tree_and_fold_nothing() -> None:
    """If `~` cancelled a double negation or distributed over `And`, an adapter's rewrite
    would be tested against an input it never receives."""
    assert ~EUROPEAN_ROAD == Not(EUROPEAN_ROAD)
    assert ~~EUROPEAN_ROAD == Not(Not(EUROPEAN_ROAD))
    assert EUROPEAN_ROAD & FAST == And((EUROPEAN_ROAD, FAST))
    assert EUROPEAN_ROAD | FAST == Or((EUROPEAN_ROAD, FAST))
    assert ~(EUROPEAN_ROAD & FAST) == Not(And((EUROPEAN_ROAD, FAST)))
    assert ~(EUROPEAN_ROAD | FAST) == Not(Or((EUROPEAN_ROAD, FAST)))


def test_a_predicate_has_no_truth_value() -> None:
    """`a and b` would return `b`, `not a` False, `if a:` always true, with no type error
    in any of them."""
    with pytest.raises(TypeError, match="no truth value"):
        bool(EUROPEAN_ROAD)
    with pytest.raises(TypeError, match="no truth value"):
        _ = EUROPEAN_ROAD and FAST
    with pytest.raises(TypeError, match="no truth value"):
        _ = not DWithin(Layers.water, 500.0)


def test_a_connective_needs_at_least_two_terms() -> None:
    for connective in (And, Or):
        with pytest.raises(ValueError, match="at least two terms"):
            connective(())
        with pytest.raises(ValueError, match="at least two terms"):
            connective((EUROPEAN_ROAD,))
    assert And((EUROPEAN_ROAD, FAST, Attr.is_null("fartsgrense"))).terms[2] == IsNull(
        "fartsgrense"
    )


def test_every_node_is_a_predicate() -> None:
    near_water = DWithin(Layers.water, 500.0)
    leaves = (
        EUROPEAN_ROAD,
        Attr.in_("vegkategori", ("E", "R")),
        Attr.is_null("fartsgrense"),
        Attr.raw("fartsgrense > 2 * 40"),
        near_water,
    )
    for node in leaves:
        assert isinstance(node, Predicate)
    assert isinstance(EUROPEAN_ROAD & (FAST | near_water), And)


# ---------------------------------------------------------------------------
# Structured attribute leaves
# ---------------------------------------------------------------------------


def test_cmp_builds_a_compare_leaf_with_the_operator_set() -> None:
    assert EUROPEAN_ROAD == Compare(field="vegkategori", op=Comparison.EQ, value="E")
    assert [op.value for op in Comparison] == ["=", "<>", "<", "<=", ">", ">=", "LIKE"]
    assert Attr.cmp("vegnummer", Comparison.LIKE, "E6%").value == "E6%"


def test_cmp_refuses_a_null_value() -> None:
    """`= NULL` is never true in SQL; the null test has its own leaf."""
    with pytest.raises(ValueError, match="Attr.is_null"):
        Attr.cmp("fartsgrense", Comparison.EQ, None)
    with pytest.raises(ValueError, match="never true"):
        Attr.cmp("fartsgrense", Comparison.NE, None)


def test_like_takes_a_string_pattern() -> None:
    assert Attr.cmp("vegnummer", Comparison.LIKE, "E%").value == "E%"
    with pytest.raises(ValueError, match="LIKE takes a string pattern"):
        Attr.cmp("fartsgrense", Comparison.LIKE, 80)


def test_in_builds_a_tuple_and_accepts_an_empty_set() -> None:
    """The empty set is legitimate: `~Attr.in_(id, ids)` with no ids to exclude."""
    assert Attr.in_("feature_id", [3, 1, 2]) == IsIn(
        field="feature_id", values=(3, 1, 2)
    )
    assert Attr.in_("feature_id", ()).values == ()
    assert Attr.in_("vegkategori", iter(["E", "R"])).values == ("E", "R")


def test_in_refuses_a_null_member() -> None:
    with pytest.raises(ValueError, match="NULL is never IN a set"):
        Attr.in_("feature_id", (1, None))


def test_is_null_and_raw_build_their_leaves() -> None:
    assert Attr.is_null("fartsgrense") == IsNull(field="fartsgrense")
    assert Attr.raw("fartsgrense > 2 * 40") == RawAttr(cql="fartsgrense > 2 * 40")


def test_leaves_are_immutable_values() -> None:
    with pytest.raises(AttributeError):
        EUROPEAN_ROAD.value = "R"  # type: ignore[misc]
    assert hash(EUROPEAN_ROAD) == hash(Compare("vegkategori", Comparison.EQ, "E"))


# ---------------------------------------------------------------------------
# Spatial leaves
# ---------------------------------------------------------------------------


def test_dwithin_carries_its_distance_and_the_others_refuse_one() -> None:
    assert DWithin(Layers.water, 500.0) == Spatial(
        relate_to=Layers.water, relation=Relation.DWITHIN, distance_m=500.0
    )
    assert Within(Layers.water).relation is Relation.WITHIN
    assert Within(Layers.water).distance_m is None
    assert Intersects(Layers.railway).relation is Relation.INTERSECTS
    with pytest.raises(ValueError, match="requires distance_m"):
        Spatial(relate_to=Layers.water, relation=Relation.DWITHIN)
    with pytest.raises(ValueError, match="takes no distance_m"):
        Spatial(relate_to=Layers.water, relation=Relation.WITHIN, distance_m=10.0)


def test_dwithin_requires_a_positive_distance() -> None:
    for distance in (0.0, -5.0):
        with pytest.raises(ValueError, match="positive distance_m"):
            DWithin(Layers.water, distance)


def test_relations_are_spelled_as_cql2_spells_them() -> None:
    assert Relation.INTERSECTS.value == "s_intersects"
    assert Relation.DWITHIN.value == "s_dwithin"
    assert len(Relation) == 9


def test_the_worked_example_reads_as_the_cartographer_says_it() -> None:
    """Every European road faster than 80 km/h within 500 m of water, excluding any that
    cross a railway."""
    where = (
        EUROPEAN_ROAD
        & FAST
        & DWithin(Layers.water, 500.0)
        & ~Intersects(Layers.railway)
    )
    assert where == And(
        (
            And((And((EUROPEAN_ROAD, FAST)), DWithin(Layers.water, 500.0))),
            Not(Intersects(Layers.railway)),
        )
    )
