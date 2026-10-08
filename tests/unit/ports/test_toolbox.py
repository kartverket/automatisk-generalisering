"""The toolbox and its sentinel.

What: `NOT_INJECTED` is an instance of `Toolbox`, so `@operation` accepts it as the
sentinel default and classifies the parameter as injected; reaching any port on it fails
with a sentence; a real toolbox is a frozen value of four ports.
"""

from __future__ import annotations

import copy
import pickle

import pytest

from ag.core.errors import InjectionError
from ag.core.handles import In, Out, handle
from ag.core.operations import operation
from ag.ports import NOT_INJECTED, Toolbox


class Example:
    roads = handle()
    output = handle()


def test_the_sentinel_is_a_toolbox_that_refuses_every_port() -> None:
    assert isinstance(NOT_INJECTED, Toolbox)
    for port in ("geometry", "table", "cartographic", "graph"):
        with pytest.raises(InjectionError, match=f"tb.{port} was reached"):
            getattr(NOT_INJECTED, port)
    assert repr(NOT_INJECTED) == "NOT_INJECTED"
    assert hash(NOT_INJECTED) == hash(NOT_INJECTED)


def test_the_sentinel_compares_by_identity_and_survives_pickling() -> None:
    """The inherited dataclass equality reads a field, so comparing two sentinel
    instances would raise rather than answer; identity equality keeps hash and equality
    consistent. A copy or a pickle must come back as the same singleton, since the stage
    runner compares against it."""
    assert NOT_INJECTED == NOT_INJECTED
    assert NOT_INJECTED != Toolbox(object(), object(), object(), object())
    # The static type is Toolbox; the sentinel's class takes no arguments.
    second_instance = type(NOT_INJECTED)()  # pyright: ignore[reportCallIssue]
    assert second_instance != NOT_INJECTED
    assert hash(second_instance) != hash(NOT_INJECTED)
    assert pickle.loads(pickle.dumps(NOT_INJECTED)) is NOT_INJECTED
    assert copy.deepcopy(NOT_INJECTED) is NOT_INJECTED


def test_an_operation_classifies_the_toolbox_as_injected() -> None:
    @operation
    def worked(*, roads: In, output: Out, tb: Toolbox = NOT_INJECTED) -> None: ...

    call = worked(roads=Example.roads, output=Example.output)
    assert call.injected == {Toolbox: "tb"}
    with pytest.raises(TypeError, match="declaration site"):
        worked(roads=Example.roads, output=Example.output, tb=NOT_INJECTED)


def test_a_toolbox_is_a_frozen_value_of_four_ports() -> None:
    """The Protocols are empty for now, so any object satisfies them; the value semantics
    are what this pins."""
    ports = [object() for _ in range(4)]
    tb = Toolbox(
        geometry=ports[0], table=ports[1], cartographic=ports[2], graph=ports[3]
    )
    assert (tb.geometry, tb.table, tb.cartographic, tb.graph) == tuple(ports)
    with pytest.raises(AttributeError):
        tb.geometry = ports[1]  # type: ignore[misc]
