"""The row-shape grammar: what a port method declares about each output it writes.

What: `Cardinality` and `Ids`, the two axes; `Rows`, one output's declaration, naming the
input its rows derive from; and `@row_shape(**outputs)`, which attaches one `Rows` per
output parameter to a Protocol method as `__row_shape__`, keyed by the parameter's name.

How: the two axes are independent and declared together. `cardinality` says how many
output rows one subject row yields (`ONE`, `MANY`, `GROUP`); `ids` says what identity those
rows carry (`CARRY` keeps the subject's id, `MINT` issues new ids with the edges recorded,
`FOREIGN` carries no `lineage_id` and holds subject ids in declared columns). Three cells
are illegal and refused at construction, each for its reason: `GROUP + CARRY` and
`GROUP + FOREIGN`, because many parents collapse into one row and a scalar cannot hold a
set; `MANY + CARRY`, because it is the inheritance model lineage rejects, since five split
pieces all keeping one id leave the log unable to express a partial drop. `CARRY` implies
`ONE`. Per-row behaviour comes from the parents table at runtime, not from the cell: a
group with one parent carries its id and emits no edge, a group with two or more mints,
and the same holds for `MANY`; that is behaviour inside a cell and no reason to admit
`GROUP + CARRY`. The cost of a cell is stated here so that it is chosen deliberately:
`ONE + MINT` emits one edge per row, the most expensive shape, against one edge per group
for `GROUP + MINT` and none for `ONE + CARRY`.

Every output names the input its rows derive from, because the surface has no genuine
aggregate output and anything that cannot name one must be argued rather than fall through
an escape hatch. For `CARRY` and `MINT` that input is the subject: the input whose ids are
kept or whose rows are the parents. For `FOREIGN` the ref columns name the inputs instead,
so a `FOREIGN` row carries refs and no subject. A `context` is an input that influenced
the output without contributing identity: `intersection` output rows are pieces of the
roads, and the overlay shaped them without becoming their ancestor. The word is shared
with the stage-level input role because both mean "influences, never becomes", and for no
other reason; the two are declared at different levels and need not coincide for a call
(ADR-0021 ST-D21). `Rows` refuses the three illegal cells and these subject and refs rules at
construction, so a wrong declaration fails when the Protocol is imported. The check over
the surface, `tests/static/test_row_shape.py`, holds what construction cannot see; its
rules are ADR-0017 RS-4, and a handle inside a `Spatial` predicate and a method that
changes its input in place are the two things no rule sees, stated there so they are not
mistaken for omissions.

Why: the declaration lives on the Protocol, read from the Protocol and never from an
adapter, so adapters conform without decoration and cannot drift from the contract. The
decorator stores the mapping on the function and returns the function itself, so the
method's structural type is untouched and a class assigned to the Protocol type-checks
exactly as it would without the declaration; a wrapper would hide the signature from the
checker and break that. A method whose rows the caller builds has no subject parameter
to name and declares its ids axis where it is called instead; a method with a `MINT`
output reports parentage through a `ParentsOut` parameter, which is a relation the layer
above consumes and carries no row shape. ADR-0017.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, TypeVar

from ag.ports.attributes import FieldName


class Cardinality(Enum):
    """Output rows per subject row."""

    ONE = "one"
    MANY = "many"
    GROUP = "group"


class Ids(Enum):
    """What identity the output rows carry."""

    CARRY = "carry"
    """The subject's id, unchanged. Implies `ONE`."""
    MINT = "mint"
    """New ids, with the edges from the subject's rows recorded."""
    FOREIGN = "foreign"
    """No `lineage_id`; the ref columns hold subject ids as foreign keys."""


@dataclass(frozen=True)
class Rows:
    """One output's row shape: both axes and the input its rows derive from.

    `subject` names the `In` parameter whose rows carry identity into the output, for
    `CARRY` and `MINT`. `refs` maps a ref column to the `In` parameter whose ids it holds,
    for `FOREIGN`, in place of a subject. `context` names an `In` parameter that influenced
    the output without contributing identity, on any cell.
    """

    cardinality: Cardinality
    ids: Ids
    subject: str | None = None
    context: str | None = None
    refs: Mapping[FieldName, str] | None = None

    def __post_init__(self) -> None:
        if self.cardinality is Cardinality.GROUP and self.ids is not Ids.MINT:
            raise ValueError(
                f"GROUP + {self.ids.name} is illegal: many parents, one row, and a "
                "scalar cannot hold a set. A group output mints."
            )
        if self.cardinality is Cardinality.MANY and self.ids is Ids.CARRY:
            raise ValueError(
                "MANY + CARRY is illegal: this is the inheritance model lineage rejects. "
                "Five split pieces all keeping one id leave the log unable to express a "
                "partial drop; pieces mint (ADR-0017)."
            )
        if self.ids is Ids.FOREIGN:
            if not self.refs:
                raise ValueError(
                    "a FOREIGN output names the inputs its ref columns hold ids of: "
                    "refs={column: input} is required."
                )
            if self.subject is not None:
                raise ValueError(
                    "a FOREIGN output carries no lineage_id, so it has no subject; its "
                    "refs name the inputs instead."
                )
        else:
            if self.subject is None:
                raise ValueError(
                    f"a {self.ids.name} output names the input its rows derive from: "
                    "subject= is required."
                )
            if self.refs:
                raise ValueError(
                    f"a {self.ids.name} output carries the subject's ids or new ones; "
                    "refs are for FOREIGN."
                )
        if self.refs is not None:
            object.__setattr__(self, "refs", MappingProxyType(dict(self.refs)))

    def inputs(self) -> tuple[str, ...]:
        """Every input parameter name the declaration refers to, subject first."""
        named: list[str] = []
        if self.subject is not None:
            named.append(self.subject)
        if self.context is not None:
            named.append(self.context)
        if self.refs:
            named.extend(self.refs.values())
        return tuple(named)


F = TypeVar("F", bound=Callable[..., Any])


def row_shape(**outputs: Rows) -> Callable[[F], F]:
    """Attaches one `Rows` per output parameter to a Protocol method, by name.

    The mapping is stored as `__row_shape__` on the function object and the function is
    returned unchanged, so the Protocol's structural type is exactly what the signature
    says. Read it from the Protocol class, never from an adapter instance.
    """

    def attach(fn: F) -> F:
        setattr(fn, "__row_shape__", MappingProxyType(dict(outputs)))
        return fn

    return attach
