"""TEMPLATE — not shipped. Target module: `src/ag/adapters/arcpy/predicates.py`.

Compiling a `Predicate` tree onto arcpy's selection API. No `import arcpy` here.

THE PROBLEM THIS SOLVES, AND WHY IT IS THE ADAPTER'S AND NOT THE MODEL'S

`Predicate` is an ordinary boolean algebra: `And`, `Or`, `Not` over attribute and
spatial leaves (ADR-0001). arcpy cannot evaluate one. It offers a running selection on
a layer, mutated by successive calls, and it can invert only at a LEAF -
`invert_where_clause` on SelectLayerByAttribute, `invert_spatial_relationship` on
SelectLayerByLocation. There is no representation for `Not(And(a, b))`.

De Morgan closes the gap: push every negation down to the leaves, where arcpy has a
flag for it, and the remaining tree is pure And/Or, which the running selection can
express as SUBSET and ADD.

THE AWKWARDNESS IS ONE ADAPTER'S, NOT THE MODEL'S. The same tree compiles to SQL by
structural recursion with no rewrite at all:

    And(terms) -> " AND ".join(compile(t) for t in terms)
    Not(term)  -> f"NOT ({compile(term)})"
    Spatial(h, Relation.DWITHIN, d) -> f"ST_DWithin(geom, {ref(h)}, {d})"

That asymmetry is the argument for ADR-0001 in miniature: a port shaped after arcpy's
held selection would have made every future adapter emulate a mutable cursor over a
layer, to buy nothing. A port shaped after the concept costs this one file.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ag.ports.geometry_ops import And, Attr, Not, Or, Predicate, Spatial


@dataclass(frozen=True)
class Negated(Predicate):
    """A leaf that arcpy will invert with its own flag.

    ADAPTER-INTERNAL AND IT NEVER CROSSES THE PORT. It exists only between
    `push_negation` and `apply`, to carry "this leaf is inverted" in the one shape
    arcpy can act on. A SQL adapter has no use for it and would never define it.

    Subclasses `Predicate` so the rewritten tree is still a `Predicate` and `apply`
    can match over one type. Wrapping a `Negated` in another `Negated` is not
    representable through `push_negation`, which cancels double negation on the way
    down rather than nesting it.
    """

    term: Predicate


class Combine(Enum):
    """How a selection call combines with the running selection on the layer."""

    NEW = "NEW_SELECTION"
    ADD = "ADD_TO_SELECTION"
    REMOVE = "REMOVE_FROM_SELECTION"
    SUBSET = "SUBSET_SELECTION"


def push_negation(predicate: Predicate, negate: bool = False) -> Predicate:
    """De Morgan to the leaves. Returns a tree whose only `Not` is a leaf `Negated`.

        Not(And(a, b))  ->  Or((Negated(a), Negated(b)))
        Not(Or(a, b))   ->  And((Negated(a), Negated(b)))
        Not(Not(a))     ->  a

    `negate` is the accumulated parity on the way down, so double negation cancels
    by arithmetic rather than by a special case: two `Not`s flip the flag twice and
    the leaf comes out bare.

    TOTAL OVER THE PREDICATE TREE. The `case _` arm catches `Attr`, `Spatial` and any
    leaf added later, which is deliberate - a new leaf type is negatable the moment it
    exists, without editing this function.
    """
    match predicate:
        case Not(term):
            return push_negation(term, not negate)
        case And(terms):
            rewritten = tuple(push_negation(t, negate) for t in terms)
            return Or(rewritten) if negate else And(rewritten)
        case Or(terms):
            rewritten = tuple(push_negation(t, negate) for t in terms)
            return And(rewritten) if negate else Or(rewritten)
        case _:
            return Negated(predicate) if negate else predicate


def apply(layer: str, predicate: Predicate, combine: Combine = Combine.NEW) -> None:
    """Drive the running selection on `layer`. Call `push_negation` first.

    And -> SUBSET the running selection; Or -> ADD to it. The first term of either
    inherits the caller's `combine`, so a nested tree composes: the head establishes
    or narrows the selection and the tail refines it in the parent's direction.

    NOT IMPLEMENTED HERE. The arcpy calls belong with `session.py`, which owns the
    lazily-bound import and the message drain. What is testable without arcpy is the
    rewrite above, and that is what `tests/unit/test_predicates.py` covers.
    """
    match predicate:
        case And(terms) | Or(terms):
            rest = Combine.SUBSET if isinstance(predicate, And) else Combine.ADD
            apply(layer, terms[0], combine)
            for term in terms[1:]:
                apply(layer, term, rest)
        case Attr() | Negated(Attr()):
            raise NotImplementedError(
                "SelectLayerByAttribute(layer, combine.value, cql_to_sql(term.cql), "
                "invert_where_clause=isinstance(predicate, Negated))"
            )
        case Spatial() | Negated(Spatial()):
            raise NotImplementedError(
                "SelectLayerByLocation(layer, relation, relate_to, distance_m, "
                "combine.value, invert_spatial_relationship=...)"
            )
        case _:
            raise TypeError(
                f"{type(predicate).__name__} has no arcpy representation. A bare Not "
                "means push_negation was not called - arcpy inverts only at a leaf, "
                "so Not(And(...)) has nothing to compile to."
            )
