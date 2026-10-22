"""The `GeometryOps` Protocol: operations on spatial datasets.

Its methods arrive one at a time as their callers do, with the vocabulary from open
standards rather than from one engine. The selection predicate algebra it takes lives in
`ag.ports.predicates`; the row shape each output declares lives in `ag.ports.row_shape`.
"""

from __future__ import annotations

from typing import Protocol

from ag.core.handles import In, Out, ParentsOut
from ag.ports.predicates import Predicate
from ag.ports.row_shape import Cardinality, Ids, Rows, row_shape


class GeometryOps(Protocol):
    """Operations on spatial datasets.

    Every handle parameter carries a direction marker, and every output declares its row
    shape on the method; an adapter conforms structurally and carries neither. ADR-0017.
    """

    @row_shape(output=Rows(Cardinality.ONE, Ids.CARRY, subject="input"))
    def select(self, *, input: In, where: Predicate, output: Out) -> None:
        """Writes the rows of `input` for which `where` is TRUE to `output`.

        How: the predicate is evaluated per row as SQL evaluates it, TRUE, FALSE or
        UNKNOWN, and only TRUE rows are kept, so a row whose field is NULL is excluded by
        a comparison and included by `Attr.is_null`; the rules are in the predicate
        module. Rows keep their attributes and geometry; `ONE + CARRY`, since every output
        row is an input row with its identity.

        Why: one method and a value type replace the engine's make-layer, select and copy
        idiom; nothing is materialised before this call, and no selection state survives
        it. ADR-0019 PC-D5.
        """
        ...

    @row_shape(output=Rows(Cardinality.MANY, Ids.MINT, subject="input"))
    def explode_multipart(
        self, *, input: In, output: Out, parents: ParentsOut = None
    ) -> None:
        """Writes one row per part of every row of `input` to `output`.

        How: a single-part row yields one row and a multipart row yields one row per
        part, each with the input row's attributes; `MANY + MINT`, since a piece is not
        the feature it came from. When `parents` is a handle the adapter writes a table
        of `(PARENT_ID, CHILD_ID)` rows to it, one per (input row, output row) pair, in
        the port's native indices; when it is None no parents are produced and nothing
        is paid for them.

        Why: the parts of a feature are the unit later operations work on, and the
        parents table is what lets the layer above record which feature each part came
        from without the adapter knowing anything about ids.
        """
        ...
