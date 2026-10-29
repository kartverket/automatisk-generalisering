"""The generic port facade: every Protocol member reachable, hooks, shape from the Protocol.

What: the handle-bearing Protocols are derived from the Toolbox's fields, `graph` left
out because the form of `GraphOps` is open (ADR-0018 AR-D7), and every member of each is
walked: a call through the facade leaves a store in the same state as the direct call on
a store seeded the same way, native indices and the parents table included, with the
same returned rows. The walked set is pinned, so a broken discovery step cannot pass as
an empty walk. The hooks see a `PortCall` carrying the Protocol's own `__row_shape__`,
not one on the adapter (ADR-0017 RS-D10), and the whole call as keyword arguments
(ADR-0019 PC-D4); `before` runs before the port writes, `after` after, and not at all
when the port raises. A non-member raises `AttributeError`, a positional call raises
`TypeError` naming the method, the facade has no public name of its own, and a
non-Protocol is refused by `wrap`. The facade's private state is reachable as any Python
attribute is; the lint rule on private member access is what keeps domain code from
reaching through it, and no test here claims more.

Why: the facade is one generic class over every port, so what makes it correct is that
nothing on the surface escapes it and nothing it adds changes a call; both are only
shown by walking the surface against the fake.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from dataclasses import dataclass
from typing import get_protocol_members, get_type_hints

import pytest

from ag.adapters.fakes.memory.cartographic_ops import MemoryCartographicOps
from ag.adapters.fakes.memory.geometry_ops import MemoryGeometryOps
from ag.adapters.fakes.memory.store import MemoryStore
from ag.adapters.fakes.memory.table_ops import MemoryTableOps
from ag.core.handles import In, Out, ScratchHandle
from ag.core.types import DataType
from ag.lineage.facade import PortCall, wrap
from ag.ports import Attr, Comparison, Predicate
from ag.ports.cartographic_ops import CartographicOps
from ag.ports.errors import PortContractError
from ag.ports.geometry_ops import GeometryOps
from ag.ports.row_shape import Cardinality, Ids, Rows, row_shape
from ag.ports.table_ops import TableOps
from ag.ports.toolbox import Toolbox
from tests.support.cases import DatasetCase, parts, roads
from tests.support.memory import memory_handle, seed

WALKED: dict[str, type] = {
    name: hint for name, hint in get_type_hints(Toolbox).items() if name != "graph"
}
"""Toolbox field to its Protocol, for every handle-bearing port."""

MEMBERS: tuple[tuple[type, str], ...] = tuple(
    (protocol, member)
    for protocol in WALKED.values()
    for member in sorted(get_protocol_members(protocol))
)
"""Every (Protocol, member) the test walks."""

DECLARED: frozenset[tuple[type, str]] = frozenset(
    {
        (GeometryOps, "select"),
        (GeometryOps, "explode_multipart"),
        (TableOps, "read_rows"),
    }
)
"""What the three Protocols declare today; `CartographicOps` has no member yet."""

ADAPTERS: dict[type, Callable[[MemoryStore], object]] = {
    GeometryOps: lambda store: MemoryGeometryOps(store=store),
    TableOps: lambda store: MemoryTableOps(store=store),
    CartographicOps: lambda store: MemoryCartographicOps(store=store),
}


@dataclass(frozen=True)
class Scenario:
    """One call of a member: the case to seed, its arguments, and what to compare.

    `arguments` builds the call's keyword arguments from the seeded handle; `outputs`
    names the arguments whose datasets are compared after the call; `returns_rows` says
    the result is an iterable of rows to materialise and compare.
    """

    case: Callable[[], DatasetCase]
    arguments: Callable[[ScratchHandle], dict[str, object]]
    outputs: tuple[str, ...] = ()
    returns_rows: bool = False


SCENARIOS: dict[tuple[type, str], Scenario] = {
    (GeometryOps, "select"): Scenario(
        case=roads,
        arguments=lambda handle: {
            "input": handle,
            "where": Attr.cmp("rank", Comparison.GE, 2),
            "output": memory_handle("kept"),
        },
        outputs=("output",),
    ),
    (GeometryOps, "explode_multipart"): Scenario(
        case=parts,
        arguments=lambda handle: {
            "input": handle,
            "output": memory_handle("exploded"),
            "parents": memory_handle("pairs", DataType.TABLE),
        },
        outputs=("output", "parents"),
    ),
    (TableOps, "read_rows"): Scenario(
        case=roads,
        arguments=lambda handle: {"input": handle, "fields": ("name", "rank")},
        returns_rows=True,
    ),
}


def _ids() -> list[str]:
    return [f"{protocol.__name__}.{member}" for protocol, member in MEMBERS]


def test_the_walk_is_the_declared_surface_and_not_empty() -> None:
    assert set(WALKED.values()) == {GeometryOps, TableOps, CartographicOps}
    assert frozenset(MEMBERS) == DECLARED
    assert MEMBERS, "an empty walk proves nothing"


def test_every_walked_member_has_a_scenario() -> None:
    assert set(SCENARIOS) == set(MEMBERS)


@pytest.mark.parametrize(("protocol", "member"), MEMBERS, ids=_ids())
def test_a_call_through_the_facade_equals_the_direct_call(
    protocol: type, member: str
) -> None:
    scenario = SCENARIOS[protocol, member]
    direct_store, wrapped_store = MemoryStore(), MemoryStore()
    direct = ADAPTERS[protocol](direct_store)
    wrapped = wrap(protocol, ADAPTERS[protocol](wrapped_store))
    direct_seeded = seed(direct_store, scenario.case())
    wrapped_seeded = seed(wrapped_store, scenario.case())
    assert direct_seeded == wrapped_seeded
    arguments = scenario.arguments(direct_seeded.handle)

    direct_result = getattr(direct, member)(**arguments)
    wrapped_result = getattr(wrapped, member)(**arguments)

    if scenario.returns_rows:
        assert list(wrapped_result) == list(direct_result)
    else:
        assert wrapped_result == direct_result
    for name in ("input", *scenario.outputs):
        handle = arguments[name]
        assert isinstance(handle, ScratchHandle)
        assert wrapped_store.read(handle) == direct_store.read(handle), name


def test_the_hooks_see_the_call_with_the_protocols_rows_in_order() -> None:
    store = MemoryStore()
    seeded = seed(store, roads())
    output = memory_handle("kept")
    before_seen: list[PortCall] = []
    after_seen: list[tuple[PortCall, object]] = []

    def before(call: PortCall) -> None:
        with pytest.raises(PortContractError):
            store.read(output)  # not written yet
        before_seen.append(call)

    def after(call: PortCall, result: object) -> None:
        assert len(store.read(output).rows) == 2  # written by now
        after_seen.append((call, result))

    where = Attr.cmp("rank", Comparison.GE, 2)
    facade = wrap(
        GeometryOps, MemoryGeometryOps(store=store), before=before, after=after
    )
    facade.select(input=seeded.handle, where=where, output=output)

    expected = PortCall(
        protocol=GeometryOps,
        method="select",
        rows=getattr(GeometryOps.select, "__row_shape__"),
        kwargs={"input": seeded.handle, "where": where, "output": output},
    )
    assert before_seen == [expected]
    assert after_seen == [(expected, None)]
    assert expected.rows == {
        "output": Rows(Cardinality.ONE, Ids.CARRY, subject="input")
    }


def test_a_query_records_no_rows() -> None:
    store = MemoryStore()
    seeded = seed(store, roads())
    seen: list[PortCall] = []
    facade = wrap(TableOps, MemoryTableOps(store=store), before=seen.append)
    list(facade.read_rows(input=seeded.handle, fields=("name",)))
    assert seen[0].method == "read_rows"
    assert dict(seen[0].rows) == {}


def test_the_rows_come_from_the_protocol_and_not_from_the_adapter() -> None:
    class Decorated(MemoryGeometryOps):
        @row_shape(output=Rows(Cardinality.GROUP, Ids.MINT, subject="input"))
        def select(self, *, input: In, where: Predicate, output: Out) -> None:
            MemoryGeometryOps.select(self, input=input, where=where, output=output)

    store = MemoryStore()
    seeded = seed(store, roads())
    seen: list[PortCall] = []
    facade = wrap(GeometryOps, Decorated(store=store), before=seen.append)
    facade.select(
        input=seeded.handle, where=Attr.is_null("rank"), output=memory_handle("o")
    )
    assert seen[0].rows == getattr(GeometryOps.select, "__row_shape__")
    assert seen[0].rows != getattr(Decorated.select, "__row_shape__")


def test_after_is_not_called_when_the_port_raises() -> None:
    store = MemoryStore()
    seeded = seed(store, roads())
    before_seen: list[PortCall] = []
    after_seen: list[tuple[PortCall, object]] = []
    facade = wrap(
        GeometryOps,
        MemoryGeometryOps(store=store),
        before=before_seen.append,
        after=lambda call, result: after_seen.append((call, result)),
    )
    with pytest.raises(PortContractError):
        facade.select(
            input=seeded.handle, where=Attr.is_null("rank"), output=seeded.handle
        )
    assert len(before_seen) == 1
    assert after_seen == []


def test_a_name_off_the_protocol_raises_and_the_facade_has_no_public_name() -> None:
    facade = wrap(GeometryOps, MemoryGeometryOps(store=MemoryStore()))
    with pytest.raises(AttributeError, match="GeometryOps has no member 'dissolve'"):
        getattr(facade, "dissolve")
    assert [name for name in dir(facade) if not name.startswith("_")] == []
    # A dunder probe on an instance without state: recursed before the miss was raised
    # ahead of any state read.
    copy.copy(facade)


def test_a_positional_call_fails_at_the_facade_naming_the_method() -> None:
    store = MemoryStore()
    seeded = seed(store, roads())
    facade = wrap(GeometryOps, MemoryGeometryOps(store=store))
    with pytest.raises(TypeError, match="GeometryOps.select takes keyword arguments"):
        getattr(facade, "select")(seeded.handle)
    with pytest.raises(PortContractError):
        store.read(memory_handle("kept"))


def test_wrap_refuses_a_non_protocol() -> None:
    with pytest.raises(TypeError):
        wrap(MemoryGeometryOps, MemoryGeometryOps(store=MemoryStore()))
