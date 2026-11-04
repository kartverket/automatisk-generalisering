"""Three-valued evaluation under the in-memory adapter: ADR-0019 PC-D15 to PC-D17, PC-D20.

`check` is exercised on its own, with no rows at all, because that is when it runs; the
same bad predicates reach `select` on an empty dataset in the geometry tests.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from ag.adapters.fakes.memory.support.predicate_eval import Truth, check, evaluate
from ag.ports import Attr, Comparison, Intersects, Predicate, Row
from ag.ports.errors import PortContractError
from tests.support.cases import roads
from tests.support.memory import memory_handle

SCHEMA = roads().schema
ALPHA, BETA, GAMMA, DELTA = roads().rows
"""`BETA` has a NULL rank and a NULL date; `GAMMA` a NULL width."""


def truth(predicate: Predicate, row: Row) -> Truth:
    check(predicate, schema=SCHEMA)
    return evaluate(predicate, row=row, schema=SCHEMA)


def test_compare_is_unknown_on_a_null_field_and_so_is_its_negation() -> None:
    rank_is_one = Attr.cmp("rank", Comparison.EQ, 1)
    assert truth(rank_is_one, ALPHA) is Truth.TRUE
    assert truth(rank_is_one, BETA) is Truth.UNKNOWN
    assert truth(~rank_is_one, BETA) is Truth.UNKNOWN
    assert truth(~rank_is_one, GAMMA) is Truth.TRUE


def test_not_in_excludes_the_null_row_and_or_is_null_brings_it_back() -> None:
    not_in = ~Attr.in_("rank", (1, 3))
    assert truth(not_in, BETA) is Truth.UNKNOWN
    assert truth(not_in | Attr.is_null("rank"), BETA) is Truth.TRUE
    assert truth(not_in, DELTA) is Truth.TRUE


def test_empty_in_is_false_for_every_row_and_is_null_is_never_unknown() -> None:
    assert truth(Attr.in_("rank", ()), ALPHA) is Truth.FALSE
    assert truth(Attr.in_("rank", ()), BETA) is Truth.FALSE
    assert truth(Attr.is_null("rank"), BETA) is Truth.TRUE
    assert truth(Attr.is_null("rank"), ALPHA) is Truth.FALSE


def test_and_and_or_follow_the_three_valued_tables() -> None:
    true = Attr.cmp("name", Comparison.EQ, "beta_road")
    false = Attr.cmp("name", Comparison.EQ, "other")
    unknown = Attr.cmp("rank", Comparison.EQ, 1)
    assert truth(unknown & false, BETA) is Truth.FALSE
    assert truth(unknown & true, BETA) is Truth.UNKNOWN
    assert truth(true & true, BETA) is Truth.TRUE
    assert truth(unknown | true, BETA) is Truth.TRUE
    assert truth(unknown | false, BETA) is Truth.UNKNOWN
    assert truth(false | false, BETA) is Truth.FALSE


@pytest.mark.parametrize(
    ("op", "value", "expected"),
    [
        (Comparison.EQ, 1, Truth.TRUE),
        (Comparison.NE, 1, Truth.FALSE),
        (Comparison.LT, 2, Truth.TRUE),
        (Comparison.LE, 1, Truth.TRUE),
        (Comparison.GT, 1, Truth.FALSE),
        (Comparison.GE, 2, Truth.FALSE),
    ],
)
def test_every_ordering_operator_on_a_number(
    op: Comparison, value: int, expected: Truth
) -> None:
    assert truth(Attr.cmp("rank", op, value), ALPHA) is expected


def test_orderings_hold_on_text_dates_and_an_int_against_a_double() -> None:
    on_new_year = Attr.cmp("surveyed", Comparison.GE, datetime(2024, 1, 1))
    assert truth(Attr.cmp("name", Comparison.LT, "B"), ALPHA) is Truth.TRUE
    assert truth(on_new_year, ALPHA) is Truth.TRUE
    assert truth(on_new_year, DELTA) is Truth.FALSE
    assert truth(Attr.cmp("width_m", Comparison.GT, 2), ALPHA) is Truth.TRUE
    assert truth(Attr.cmp("width_m", Comparison.GT, 2), GAMMA) is Truth.UNKNOWN


@pytest.mark.parametrize(
    ("pattern", "row", "expected"),
    [
        ("Alpha%", ALPHA, Truth.TRUE),
        ("alpha%", ALPHA, Truth.FALSE),
        ("%road", ALPHA, Truth.TRUE),
        ("%road", BETA, Truth.TRUE),
        ("_lpha road", ALPHA, Truth.TRUE),
        ("Alpha_road", ALPHA, Truth.TRUE),
        ("Alpha", ALPHA, Truth.FALSE),
        ("A.pha road", ALPHA, Truth.FALSE),
        ("%", BETA, Truth.TRUE),
        ("%" * 11 + "Alpha road", ALPHA, Truth.TRUE),
    ],
    ids=[
        "prefix",
        "case-sensitive",
        "suffix",
        "suffix-other-row",
        "underscore-one-char",
        "underscore-matches-space",
        "no-implicit-wildcard",
        "regex-char-is-literal",
        "percent-alone",
        "pattern-longer-than-the-field",
    ],
)
def test_like_wildcards(pattern: str, row: Row, expected: Truth) -> None:
    assert truth(Attr.cmp("name", Comparison.LIKE, pattern), row) is expected


@pytest.mark.parametrize(
    ("predicate", "reason"),
    [
        (Attr.cmp("colour", Comparison.EQ, "red"), "is not a field"),
        (Attr.is_null("colour"), "is not a field"),
        (Attr.cmp("rank", Comparison.EQ, 1.5), "is not an int"),
        (Attr.cmp("rank", Comparison.EQ, "1"), "is not an int"),
        (Attr.cmp("rank", Comparison.LT, 10**12), "outside the long range"),
        (Attr.in_("rank", (1, 2**31)), "outside the long range"),
        (Attr.cmp("name", Comparison.EQ, "x" * 21), "holds at most 20"),
        (Attr.cmp("rank", Comparison.LIKE, "1%"), "matches text only"),
        (Attr.cmp("surveyed", Comparison.GT, "2024"), "is not a datetime"),
        (Attr.raw("rank > 1"), "compiles no CQL"),
        (Intersects(memory_handle("other")), "computes no geometry"),
        (~(Attr.cmp("rank", Comparison.EQ, 1) & Attr.raw("x")), "compiles no CQL"),
    ],
    ids=[
        "unknown-field",
        "unknown-field-is-null",
        "float-on-long",
        "str-on-long",
        "long-overflow-lt",
        "long-overflow-in",
        "text-too-long",
        "like-on-a-number",
        "str-on-date",
        "raw",
        "spatial",
        "raw-nested",
    ],
)
def test_check_refuses_what_the_adapter_cannot_evaluate(
    predicate: Predicate, reason: str
) -> None:
    with pytest.raises(PortContractError, match=reason):
        check(predicate, schema=SCHEMA)


def test_evaluate_treats_an_unchecked_raw_or_spatial_leaf_as_a_defect() -> None:
    with pytest.raises(TypeError, match="check"):
        evaluate(Attr.raw("x"), row=ALPHA, schema=SCHEMA)
