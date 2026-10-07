"""TEMPLATE — not shipped. Target: `tests/unit/`.

The De Morgan rewrite, which is the only non-obvious claim in the predicate model.

ADR-0001 says selection is a composable predicate VALUE rather than arcpy's held
selection, and the objection it has to answer is "arcpy cannot evaluate a boolean
tree". The answer is `push_negation`: rewrite until every negation sits on a leaf,
where arcpy has a flag for it. These tests are that answer's evidence.

NO ARCPY, NO FAKE, NO FIXTURE. The rewrite is a pure function over frozen dataclasses,
which is exactly why it is worth testing before anything else in `adapters/` exists -
it is the part of the port design that could be WRONG, as opposed to merely unwritten.
"""

from __future__ import annotations

from ag.adapters.arcpy.predicates import Negated, push_negation
from ag.core.operations import handle
from ag.ports import And, Attr, DWithin, Intersects, Not, Or, Relation, Within


class Layers:
    water = handle()
    roads = handle()


A = Attr("byggtyp_nbr = 970")
B = Attr("area_m2 > 500")


# ---------------------------------------------------------------------------
# The precondition. Everything below is vacuous without it.
# ---------------------------------------------------------------------------


def test_the_operators_build_a_tree_and_fold_nothing() -> None:
    """`~`, `&` and `|` are CONSTRUCTORS, not simplifiers.

    THIS TEST IS WHY THE ONES BELOW MEAN ANYTHING. If `__invert__` cancelled double
    negation, `~~A` would already be `A` before `push_negation` saw it and
    `test_double_negation_cancels_to_a_bare_leaf` would pass without the function
    doing anything. If `__invert__` distributed over `And` - a plausible
    "optimisation" - `~(A & B)` would arrive already rewritten and every De Morgan
    test below would be asserting that `push_negation` is the identity.

    So: assert the INPUT trees are the unsimplified shapes the rewrite is supposed to
    be handed, the same way the classification test asserts its annotation is really
    a string before checking that it resolves.
    """
    assert ~A == Not(A)
    assert ~~A == Not(Not(A))
    assert A & B == And((A, B))
    assert A | B == Or((A, B))
    assert ~(A & B) == Not(And((A, B)))
    assert ~(A | B) == Not(Or((A, B)))


def test_no_predicate_node_is_a_negated_leaf_before_the_rewrite() -> None:
    """`Negated` is adapter-internal and must never appear in a tree a call site
    built. If a constructor produced one, the rewrite's output would be
    indistinguishable from its input."""
    for tree in (~A, ~~A, ~(A & B), ~(A | ~B)):
        assert not _contains_negated(tree)


# ---------------------------------------------------------------------------
# The rewrite
# ---------------------------------------------------------------------------


def test_a_bare_leaf_is_unchanged() -> None:
    assert push_negation(A) is A


def test_not_of_a_leaf_becomes_a_negated_leaf() -> None:
    assert ~A == Not(A)
    assert push_negation(~A) == Negated(A)


def test_de_morgan_over_and() -> None:
    """The case that has no arcpy representation without this rewrite.

    `Not(And(a, b))` cannot be expressed by inverting a single predicate, which is
    all `invert_where_clause` does. It CAN be expressed as `Or` of two inverted
    leaves, and that is two ordinary SelectLayerByAttribute calls.
    """
    given = ~(A & B)
    assert given == Not(And((A, B)))
    assert push_negation(given) == Or((Negated(A), Negated(B)))


def test_de_morgan_over_or() -> None:
    given = ~(A | B)
    assert given == Not(Or((A, B)))
    assert push_negation(given) == And((Negated(A), Negated(B)))


def test_double_negation_cancels_to_a_bare_leaf() -> None:
    """Not a special case in the implementation - the parity flag flips twice.

    Worth asserting anyway: the bug this catches is `Negated(Negated(A))`, which
    `apply` has no arm for and would reject at runtime.
    """
    given = ~~A
    assert given == Not(Not(A))
    assert push_negation(given) is A


def test_negation_reaches_leaves_through_nesting() -> None:
    """Three levels, mixed operators, one spatial leaf.

    The realistic shape: `~(church & near_water)` where one term is itself compound.
    Every negation must arrive at a leaf regardless of depth, and the operators must
    alternate on the way down.
    """
    near_water = DWithin(Layers.water, 500.0)
    given = ~(A & (B | near_water))
    assert given == Not(And((A, Or((B, near_water)))))
    assert push_negation(given) == Or(
        (Negated(A), And((Negated(B), Negated(near_water))))
    )


def test_spatial_leaves_negate_like_attribute_leaves() -> None:
    """arcpy has a separate flag for each - invert_where_clause and
    invert_spatial_relationship - but the rewrite does not care which."""
    assert push_negation(~Intersects(Layers.roads)) == Negated(Intersects(Layers.roads))


def test_the_worked_example_from_the_architecture_document() -> None:
    """03-architecture §2.4's vertical slice: every church building within 500 m of
    water, excluding any that touch a road.

    Mixed attribute and spatial terms, one negation, and the negation is the only
    thing the rewrite has to move. This is the expression a call site actually writes.
    """
    where = A & DWithin(Layers.water, 500.0) & ~Intersects(Layers.roads)
    rewritten = push_negation(where)

    assert isinstance(rewritten, And)
    assert Negated(Intersects(Layers.roads)) in _leaves(rewritten)
    assert not _contains_not(rewritten)


def test_no_bare_not_survives_the_rewrite() -> None:
    """The postcondition the whole function exists for, over a deliberately awkward
    tree. `apply` rejects a bare `Not`, so this is what makes that arm unreachable."""
    where = ~(A | ~(B & Within(Layers.water)))
    assert not _contains_not(push_negation(where))


def test_predicate_operators_build_the_expected_nodes() -> None:
    assert isinstance(A & B, And)
    assert isinstance(A | B, Or)
    assert isinstance(~A, Not)


def test_dwithin_carries_its_distance_and_the_others_refuse_one() -> None:
    """`Spatial.__post_init__`. DWITHIN without a distance is a silent full-extent
    selection; a distance on any other relation means the caller expected a buffer
    that will not happen."""
    assert DWithin(Layers.water, 500.0).distance_m == 500.0
    assert Within(Layers.water).relation is Relation.WITHIN
    assert Within(Layers.water).distance_m is None


# ---------------------------------------------------------------------------


def _leaves(predicate: object) -> list[object]:
    match predicate:
        case And(terms) | Or(terms):
            return [leaf for t in terms for leaf in _leaves(t)]
        case _:
            return [predicate]


def _contains_not(predicate: object) -> bool:
    """A bare `Not` anywhere. `Negated` is a leaf and does not count - it is the
    representation arcpy can act on."""
    match predicate:
        case Not():
            return True
        case And(terms) | Or(terms):
            return any(_contains_not(t) for t in terms)
        case _:
            return False


def _contains_negated(predicate: object) -> bool:
    match predicate:
        case Negated():
            return True
        case Not(term):
            return _contains_negated(term)
        case And(terms) | Or(terms):
            return any(_contains_negated(t) for t in terms)
        case _:
            return False
