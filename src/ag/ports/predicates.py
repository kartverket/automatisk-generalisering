"""The selection predicate algebra: a composable value, not a held selection.

What: `Predicate` and its closed set of nodes. Attribute leaves are structured, built
through the `Attr` constructors: `Attr.cmp(field, op, value)`, `Attr.in_(field, values)`,
`Attr.is_null(field)`, and `Attr.raw(cql)` as the rare escape hatch. `Spatial` relates to
another dataset by an OGC relation; `And`, `Or` and `Not` combine, built by `&`, `|` and
`~`. The sugar `Intersects`, `Within` and `DWithin` read as a cartographer would say them.

How: the operators are constructors, never simplifiers: `~~a` is `Not(Not(a))` and an
adapter rewrites the tree its own way. A predicate has no truth value, so `and`, `or` and
`not` are errors rather than silent misreads. The node set is closed on purpose, five kinds
of leaf and three connectives, so an adapter can pattern-match it exhaustively.

Evaluation, which every adapter implements alike: a predicate is TRUE, FALSE or UNKNOWN
per row, as SQL evaluates it, and `select` keeps the rows where it is TRUE. `Compare` and
a non-empty `IsIn` are UNKNOWN when the field is NULL; the empty `IsIn` is FALSE for every
row; `IsNull` is never UNKNOWN; `Spatial` is UNKNOWN for a row with a null geometry; `Not`
of UNKNOWN is UNKNOWN, `And` is FALSE if any term is FALSE and otherwise UNKNOWN if any
term is, `Or` the mirror. So `~Attr.in_(f, (1,))` excludes the NULL rows and a caller that
wants them writes `~Attr.in_(f, ids) | Attr.is_null(f)`. `LIKE` matches with `%` for any
run of characters and `_` for one, case-sensitively, with no escape character; a pattern
that needs a literal `%` or `_` goes through `Attr.raw`. A value whose type does not match
the field's type is a `PortContractError` from the adapter, never an engine coercion. The
in-memory adapter raises `PortContractError` on `RawAttr` rather than guess at CQL.

Why: a mutable selection is one engine's idiom, not the concept; exposing it would make
every future adapter emulate that statefulness, and it is lazier to materialise nothing
until `select`. Attribute leaves are structured rather than one CQL string because an
opaque string forces every adapter to write a parser before it can quote identifiers for
its workspace type, and admits expressions no adapter can compile; `Attr.raw` keeps the
string form available, greppable, and counted by a static test. A `Spatial` leaf carries a
handle inside a value, outside any `In` or `Out` annotation: no handle check sees it, which
is deliberate, and which handles it may name is an open question of the record.
ADR-0001 and ADR-0015.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from typing import TypeAlias

from ag.core.handles import ScratchHandle
from ag.ports.attributes import AttributeValue, FieldName


class Relation(Enum):
    """Spatial predicates, named as OGC CQL2 spells them over the DE-9IM model.

    Why: these names carry the same meaning in PostGIS, GEOS, shapely and DuckDB, so an
    adapter author who knows any of those knows what `s_within` must do. Two engine
    relations are absent on purpose: "within a distance" is `DWITHIN` plus `distance_m`,
    and "have their centre in" is not a relation but `s_within(centroid(geom), other)`,
    the rule fan-in uses for ownership, which a composite expresses with primitives every
    adapter already has.
    """

    INTERSECTS = "s_intersects"
    WITHIN = "s_within"
    CONTAINS = "s_contains"
    TOUCHES = "s_touches"
    CROSSES = "s_crosses"
    OVERLAPS = "s_overlaps"
    DISJOINT = "s_disjoint"
    EQUALS = "s_equals"
    DWITHIN = "s_dwithin"


class Comparison(Enum):
    """The operators an attribute comparison may use, spelled as SQL spells them.

    A null test is not among them: `= NULL` is never true in SQL, so it goes through
    `Attr.is_null` and no adapter has to special-case it. `LIKE` takes a string pattern
    with `%` and `_` as its wildcards.
    """

    EQ = "="
    NE = "<>"
    LT = "<"
    LE = "<="
    GT = ">"
    GE = ">="
    LIKE = "LIKE"


class Predicate:
    """A selection expression. Combine with `&`, `|` and `~`.

    Not an ABC and not a Protocol: a closed set of nodes that an adapter pattern-matches
    exhaustively. Structural typing would be wrong here, because an adapter compiling the
    tree needs to know it has seen every case.
    """

    def __and__(self, other: Predicate) -> Predicate:
        return And((self, other))

    def __or__(self, other: Predicate) -> Predicate:
        return Or((self, other))

    def __invert__(self) -> Predicate:
        return Not(self)

    def __bool__(self) -> bool:
        """Refuses a truth value: `a and b` would silently return `b`, `not a` False."""
        raise TypeError(
            "a Predicate has no truth value. Combine predicates with &, | and ~; "
            "`and`, `or` and `not` would evaluate to the wrong thing without an error."
        )


@dataclass(frozen=True)
class Compare(Predicate):
    """`field <op> value`, with a non-null value, a string for `LIKE`."""

    field: FieldName
    op: Comparison
    value: AttributeValue

    def __post_init__(self) -> None:
        if self.value is None:
            raise ValueError(
                f"Attr.cmp({self.field!r}, {self.op.name}, None): a comparison with NULL "
                "is never true in SQL. Use Attr.is_null(field), or its negation."
            )
        if self.op is Comparison.LIKE and not isinstance(self.value, str):
            raise ValueError(
                f"Attr.cmp({self.field!r}, LIKE, {self.value!r}): LIKE takes a string "
                "pattern with % and _ as wildcards."
            )


@dataclass(frozen=True)
class IsIn(Predicate):
    """`field IN (values)`. An empty set matches no row, which an adapter must honour."""

    field: FieldName
    values: tuple[AttributeValue, ...]

    def __post_init__(self) -> None:
        if any(value is None for value in self.values):
            raise ValueError(
                f"Attr.in_({self.field!r}, ...) contains None: NULL is never IN a set. "
                "Use Attr.is_null(field) for the null rows."
            )


@dataclass(frozen=True)
class IsNull(Predicate):
    """`field IS NULL`."""

    field: FieldName


@dataclass(frozen=True)
class RawAttr(Predicate):
    """A CQL2 text expression an adapter must compile as written.

    The escape hatch for what the structured leaves cannot say. Every call site is counted
    by a static test, so adding one is a deliberate edit to that test. An adapter that
    cannot compile CQL raises `PortContractError` rather than guess.
    """

    cql: str


class Attr:
    """The constructors of attribute leaves. A namespace, not a type.

    Why: the leaves are four different shapes, so they are four dataclasses an adapter
    matches on; the constructors give call sites one spelling, `Attr.cmp`, `Attr.in_`,
    `Attr.is_null`, `Attr.raw`. Structure and value types are checked when a leaf is built,
    at import; a wrong field name is not, and schema declarations on handles would be the
    additive step that catches it.
    """

    @staticmethod
    def cmp(field: FieldName, op: Comparison, value: AttributeValue) -> Compare:
        return Compare(field=field, op=op, value=value)

    @staticmethod
    def in_(field: FieldName, values: Iterable[AttributeValue]) -> IsIn:
        return IsIn(field=field, values=tuple(values))

    @staticmethod
    def is_null(field: FieldName) -> IsNull:
        return IsNull(field=field)

    @staticmethod
    def raw(cql: str) -> RawAttr:
        return RawAttr(cql=cql)


AttributeLeaf: TypeAlias = Compare | IsIn | IsNull | RawAttr
"""The closed set of attribute leaves an adapter compiles."""


@dataclass(frozen=True)
class Spatial(Predicate):
    """A spatial predicate against another dataset.

    `DWITHIN` is the one relation that takes a distance, and the distance is positive; a
    distance on any other relation means the caller expected a buffer that will not happen.
    """

    relate_to: ScratchHandle
    relation: Relation
    distance_m: float | None = None

    def __post_init__(self) -> None:
        needs_distance = self.relation is Relation.DWITHIN
        if needs_distance and self.distance_m is None:
            raise ValueError("DWITHIN requires distance_m")
        if needs_distance and self.distance_m is not None and self.distance_m <= 0:
            raise ValueError(
                f"DWITHIN requires a positive distance_m, got {self.distance_m!r}; a zero "
                "or negative distance is INTERSECTS or nothing."
            )
        if not needs_distance and self.distance_m is not None:
            raise ValueError(
                f"{self.relation.value} takes no distance_m. Only DWITHIN is a distance "
                "relation; passing one anywhere else means the caller expected a buffer "
                "that will not happen."
            )


@dataclass(frozen=True)
class And(Predicate):
    terms: tuple[Predicate, ...]

    def __post_init__(self) -> None:
        _at_least_two(terms=self.terms, name="And")


@dataclass(frozen=True)
class Or(Predicate):
    terms: tuple[Predicate, ...]

    def __post_init__(self) -> None:
        _at_least_two(terms=self.terms, name="Or")


@dataclass(frozen=True)
class Not(Predicate):
    term: Predicate


def _at_least_two(*, terms: tuple[Predicate, ...], name: str) -> None:
    """A connective with fewer than two terms has no meaning the adapters agree on."""
    if len(terms) < 2:
        raise ValueError(
            f"{name} needs at least two terms, got {len(terms)}. Build connectives with "
            "& and |; a single predicate stands on its own."
        )


def Intersects(other: ScratchHandle) -> Spatial:  # noqa: N802
    """Sugar, so a call site reads as the cartographer would say it."""
    return Spatial(relate_to=other, relation=Relation.INTERSECTS)


def Within(other: ScratchHandle) -> Spatial:  # noqa: N802
    """Sugar for `Spatial(..., Relation.WITHIN)`."""
    return Spatial(relate_to=other, relation=Relation.WITHIN)


def DWithin(other: ScratchHandle, distance_m: float) -> Spatial:  # noqa: N802
    """Sugar for `Spatial(..., Relation.DWITHIN, distance_m)`."""
    return Spatial(relate_to=other, relation=Relation.DWITHIN, distance_m=distance_m)
