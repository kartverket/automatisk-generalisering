"""The row-shape values and the decorator, at runtime.

What: `Rows` refuses the three illegal cells and the subject and refs rules at
construction, with each message stating its reason; both axes are required; the
decorator stores the declarations on the function and hands the same function back with
its signature and hints untouched. The structural-typing half of the decorator's contract
is `tests/static/test_row_shape_typing.py`, which needs pyright.
"""

from __future__ import annotations

import inspect
from collections.abc import Mapping
from types import MappingProxyType
from typing import Protocol, get_type_hints

import pytest

from ag.core.handles import In, Out
from ag.ports.row_shape import Cardinality, Ids, Rows, row_shape


def test_group_with_carry_or_foreign_is_refused_because_a_scalar_cannot_hold_a_set() -> (
    None
):
    for ids in (Ids.CARRY, Ids.FOREIGN):
        with pytest.raises(ValueError, match="scalar cannot hold a set"):
            Rows(Cardinality.GROUP, ids, subject="input")


def test_many_with_carry_is_refused_as_the_inheritance_model() -> None:
    with pytest.raises(ValueError, match="inheritance model lineage rejects"):
        Rows(Cardinality.MANY, Ids.CARRY, subject="input")


def test_carry_and_mint_need_a_subject_and_take_no_refs() -> None:
    for ids in (Ids.CARRY, Ids.MINT):
        with pytest.raises(ValueError, match="subject= is required"):
            Rows(Cardinality.ONE, ids)
        with pytest.raises(ValueError, match="refs are for FOREIGN"):
            Rows(Cardinality.ONE, ids, subject="input", refs={"ref": "input"})


def test_foreign_needs_refs_and_has_no_subject() -> None:
    with pytest.raises(ValueError, match="refs={column: input} is required"):
        Rows(Cardinality.ONE, Ids.FOREIGN)
    with pytest.raises(ValueError, match="has no subject"):
        Rows(Cardinality.ONE, Ids.FOREIGN, subject="input", refs={"ref": "input"})


def test_both_axes_are_required() -> None:
    with pytest.raises(TypeError):
        Rows(Cardinality.ONE)  # type: ignore[call-arg]


def test_the_legal_cells_construct_and_name_their_inputs() -> None:
    carry = Rows(Cardinality.ONE, Ids.CARRY, subject="input", context="overlay")
    foreign = Rows(Cardinality.MANY, Ids.FOREIGN, refs={"source": "input"})
    assert carry.inputs() == ("input", "overlay")
    assert foreign.inputs() == ("input",)
    assert isinstance(foreign.refs, MappingProxyType)
    assert Rows(Cardinality.GROUP, Ids.MINT, subject="input").inputs() == ("input",)


class Ops(Protocol):
    @row_shape(output=Rows(Cardinality.ONE, Ids.CARRY, subject="input"))
    def copy(self, *, input: In, output: Out) -> None: ...


class Undecorated(Protocol):
    def copy(self, *, input: In, output: Out) -> None: ...


def test_the_decorator_returns_the_function_itself() -> None:
    declared = Ops.__dict__["copy"]
    assert inspect.isfunction(declared)
    assert not hasattr(declared, "__wrapped__")
    stored: Mapping[str, Rows] = getattr(declared, "__row_shape__")
    assert stored == {"output": Rows(Cardinality.ONE, Ids.CARRY, subject="input")}
    with pytest.raises(TypeError):
        stored["output"] = None  # type: ignore[index]


def test_the_decorator_leaves_signature_and_hints_unchanged() -> None:
    declared = Ops.__dict__["copy"]
    reference = Undecorated.__dict__["copy"]
    assert inspect.signature(declared) == inspect.signature(reference)
    assert get_type_hints(declared, include_extras=True) == get_type_hints(
        reference, include_extras=True
    )
