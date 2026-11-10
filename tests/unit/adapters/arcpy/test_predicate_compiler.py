"""The predicate compiler: the clauses it writes, what `check` refuses before any row,
and that identifiers are quoted by the engine under the guard. ADR-0019 PC-D15 to
PC-D17, PC-D20."""

from __future__ import annotations

from datetime import datetime

import pytest

from ag.adapters.arcpy.session import ArcpySession
from ag.adapters.arcpy.support.dataset_schema import DescribedDataset, describe
from ag.adapters.arcpy.support.predicate_compiler import check, where_clause
from ag.ports import Attr, Comparison, Intersects, Predicate
from ag.ports.errors import EngineError, PortContractError
from tests.support.cases import roads
from tests.support.fake_arcpy import FakeEngine, FakeField, seed
from tests.support.memory import memory_handle


@pytest.fixture
def dataset(engine: FakeEngine, session: ArcpySession) -> DescribedDataset:
    seed(engine, roads(), path="roads")
    engine.datasets["roads"].fields.append(FakeField("GlobalID", "GlobalID"))
    return describe(session, "roads")


def compiled(
    where: Predicate, *, session: ArcpySession, dataset: DescribedDataset
) -> str:
    check(where, dataset=dataset)
    return where_clause(where, session=session, dataset=dataset)


@pytest.mark.parametrize(
    ("where", "clause"),
    [
        (Attr.in_("rank", ()), '("rank" IS NULL AND "rank" IS NOT NULL)'),
        (~Attr.in_("rank", ()), 'NOT (("rank" IS NULL AND "rank" IS NOT NULL))'),
        (~Attr.cmp("rank", Comparison.EQ, 1), 'NOT ("rank" = 1)'),
        (Attr.cmp("name", Comparison.LIKE, "Al%_a"), "\"name\" LIKE 'Al%_a'"),
        (Attr.cmp("name", Comparison.EQ, "it's"), "\"name\" = 'it''s'"),
        (
            Attr.cmp("surveyed", Comparison.GE, datetime(2024, 1, 2, 3, 4, 5)),
            "\"surveyed\" >= date '2024-01-02 03:04:05'",
        ),
        (
            Attr.cmp("surveyed", Comparison.EQ, datetime(2024, 1, 2, 3, 4, 5, 500000)),
            "\"surveyed\" = date '2024-01-02 03:04:05.500000'",
        ),
        (Attr.in_("rank", (1, 2)), '"rank" IN (1, 2)'),
        (Attr.cmp("width_m", Comparison.LT, 2.5), '"width_m" < 2.5'),
        (Attr.cmp("rank", Comparison.NE, 1), '"rank" <> 1'),
        (Attr.is_null("rank"), '"rank" IS NULL'),
        (Attr.raw("rank > 1"), "(rank > 1)"),
        (
            (Attr.is_null("rank") | Attr.cmp("rank", Comparison.GT, 2))
            & ~Attr.is_null("name"),
            '(("rank" IS NULL OR "rank" > 2) AND NOT ("name" IS NULL))',
        ),
    ],
    ids=[
        "empty-in",
        "not-empty-in",
        "not-over-nullable",
        "like",
        "quote-doubled",
        "date",
        "date-with-fraction",
        "in",
        "double",
        "ne",
        "is-null",
        "raw",
        "nested",
    ],
)
def test_the_clause(
    where: Predicate, clause: str, session: ArcpySession, dataset: DescribedDataset
) -> None:
    assert compiled(where, session=session, dataset=dataset) == clause


@pytest.mark.parametrize(
    ("where", "message"),
    [
        (Attr.cmp("rank", Comparison.EQ, "x"), "not an int"),
        (Attr.cmp("rank", Comparison.LT, 10**12), "outside the long range"),
        (Attr.cmp("name", Comparison.EQ, "x" * 21), "holds at most 20"),
        (Attr.in_("width_m", (1.0, "two")), "not a number"),
        (Attr.cmp("rank", Comparison.LIKE, "1%"), "a pattern matches text only"),
        (Attr.cmp("colour", Comparison.EQ, "red"), "'colour' is not a field"),
        (Attr.is_null("GlobalID"), "'GlobalID' is a GlobalID field"),
        (~(Attr.is_null("rank") & Attr.cmp("colour", Comparison.EQ, "x")), "colour"),
    ],
    ids=[
        "wrong-type",
        "long-overflow",
        "text-too-long",
        "wrong-type-in-set",
        "like-on-number",
        "undeclared",
        "unrepresentable",
        "nested-undeclared",
    ],
)
def test_check_refuses_before_anything_compiles(
    where: Predicate, message: str, dataset: DescribedDataset, engine: FakeEngine
) -> None:
    with pytest.raises(PortContractError, match=message):
        check(where, dataset=dataset)
    assert engine.quoted == []


def test_a_like_pattern_is_held_to_the_type_and_not_the_length(
    session: ArcpySession, dataset: DescribedDataset
) -> None:
    pattern = "%" * 30
    assert (
        compiled(
            Attr.cmp("name", Comparison.LIKE, pattern), session=session, dataset=dataset
        )
        == f"\"name\" LIKE '{pattern}'"
    )


def test_a_bool_never_reaches_the_compiler() -> None:
    with pytest.raises(ValueError, match="is a bool"):
        Attr.cmp("rank", Comparison.EQ, True)
    with pytest.raises(ValueError, match="is a bool"):
        Attr.in_("rank", (1, False))


def test_a_spatial_leaf_is_not_a_port_error(dataset: DescribedDataset) -> None:
    with pytest.raises(NotImplementedError):
        check(Intersects(memory_handle("other")), dataset=dataset)


def test_identifiers_are_quoted_by_the_engine_for_the_dataset(
    engine: FakeEngine, session: ArcpySession, dataset: DescribedDataset
) -> None:
    compiled(
        Attr.is_null("rank") & Attr.is_null("name"), session=session, dataset=dataset
    )
    assert engine.quoted == [("roads", "name"), ("roads", "rank")]


def test_a_quoting_failure_is_an_engine_error(
    engine: FakeEngine, session: ArcpySession, dataset: DescribedDataset
) -> None:
    engine.failures["AddFieldDelimiters"] = "no workspace"
    with pytest.raises(EngineError) as caught:
        where_clause(Attr.is_null("rank"), session=session, dataset=dataset)
    assert caught.value.context.tool == "AddFieldDelimiters"
