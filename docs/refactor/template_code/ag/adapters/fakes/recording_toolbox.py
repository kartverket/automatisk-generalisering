"""TEMPLATE — not shipped. Target module: `src/ag/adapters/fakes/recording_toolbox.py`.

A Toolbox that records every port call and computes nothing.

WHAT IT IS FOR. An operation written against the ports either can or cannot express
what it needs to do. pyright answers "do the calls type-check"; this answers "does a
whole stage run to completion, in order, without any operation needing something the
surface does not offer". Those are different questions, and only the second one has
ever found a missing port method.

`tools/run_example.py` drives both worked pipelines through `runtime.stage_entry` with
one of these in place of an arcpy Toolbox, and prints the ordered call sequence per
operation. No arcpy, no licence, no data, no cluster.

WHAT IT VERIFIES, AND WHAT IT ONLY APPEARS TO

    real       every operation runs its whole body without reaching for something
               that is not on a port.
    real       every declared output is actually WRITTEN. `exists` answers from the
               set of handles that appeared in some port call, so an operation that
               declares `dropped: Out` and never passes it anywhere fails the output
               sweep exactly as it would in a pod. That is a live bug class.
    real       operation order, and that each operation's inputs were produced by an
               earlier one.
    NOT real   `data_type_of` answers from the handle's own declared type, so the
               sweep's type check cannot fail here. Catching a tool that produces a
               table where a feature class was declared needs a real engine.
    NOT real   nothing is computed. Every geometric and tabular result is empty or a
               placeholder, so no operation's LOGIC is exercised.

`__getattr__` RATHER THAN 55 STUB METHODS. The four Protocols have 55 methods between
them, and a spy's body is the same line in every one of them. The cost is one `cast`
per port, because pyright cannot see `__getattr__` as satisfying a Protocol - the same
trade `ports.toolbox.NOT_INJECTED` makes, and acceptable here for the same reason: it
is contained in one module whose entire job is to be a stand-in.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import cast

from ag.core.operations import ScratchHandle
from ag.core.types import DataType
from ag.ports.cartographic_ops import CartographicOps
from ag.ports.geometry_ops import GeometryOps
from ag.ports.graph_ops import GraphOps
from ag.ports.table_ops import TableOps
from ag.ports.toolbox import Toolbox


@dataclass(frozen=True)
class PortCall:
    """One recorded call. `port` is the Toolbox attribute name, not a class name."""

    port: str
    method: str
    arguments: Mapping[str, object]

    def render(self) -> str:
        """`geometry.buffer(input=roads, output=buffered, distance_m=30.0)`"""
        shown = ", ".join(f"{k}={_render(v)}" for k, v in self.arguments.items())
        return f"{self.port}.{self.method}({shown})"


def _render(value: object) -> str:
    if isinstance(value, ScratchHandle):
        return value.name or "<unnamed>"
    if isinstance(value, tuple):
        return "(" + ", ".join(_render(v) for v in value) + ")"
    return repr(value)


@dataclass
class Recorder:
    """The shared log, plus the set of handles something has written.

    ONE RECORDER PER TOOLBOX, shared by all four ports, so the call sequence is in
    true order across ports rather than four separate lists that have to be merged.
    """

    calls: list[PortCall] = field(default_factory=list)
    written: set[ScratchHandle] = field(default_factory=set)

    def record(self, port: str, method: str, arguments: Mapping[str, object]) -> None:
        self.calls.append(PortCall(port=port, method=method, arguments=arguments))
        for value in arguments.values():
            self._note(value)

    def _note(self, value: object) -> None:
        """Every handle that appears in any call counts as present afterwards.

        AN OVER-APPROXIMATION, AND A USEFUL ONE. It does not distinguish reading from
        writing, so it cannot catch an operation that reads a handle it should have
        written. It DOES catch the case that matters: a declared output the operation
        never mentions at all, which is a handle nothing ever wrote and which the
        output sweep then rejects by name.
        """
        if isinstance(value, ScratchHandle):
            self.written.add(value)
        elif isinstance(value, tuple):
            for item in value:
                self._note(item)

    def since(self, mark: int) -> tuple[PortCall, ...]:
        return tuple(self.calls[mark:])


# ---------------------------------------------------------------------------


_EMPTY_RESULTS: Mapping[str, object] = {
    "count": 0,
    "describe_fields": (),
    "read_rows": (),
    "connected_components": (),
    "shortest_path": None,
    "minimum_spanning_tree": (),
    "cycles": (),
    "degree": {},
    "articulation_points": frozenset(),
}
"""Return values for the methods that return something.

EVERY ONE IS EMPTY, which is the honest answer for a spy: it computed nothing, so it
found nothing. `read_rows` returning no rows means an operation's row-processing
branch does not execute - a real limitation, and the reason this is not a substitute
for the in-memory fakes the contract suites need.
"""


class _RecordingPort:
    """Records any method call and returns the declared empty result."""

    def __init__(self, name: str, recorder: Recorder) -> None:
        self._name = name
        self._recorder = recorder

    def __getattr__(self, method: str) -> Callable[..., object]:
        if method.startswith("_"):
            raise AttributeError(method)

        def call(**kwargs: object) -> object:
            self._recorder.record(self._name, method, kwargs)
            return _EMPTY_RESULTS.get(method)

        return call


class _RecordingTableOps(_RecordingPort):
    """`TableOps` with the two catalog methods answered for real.

    The output sweep calls both after every operation, so a spy that returned an
    empty result for them would fail every stage on its first operation. `exists`
    consults what has been written, which is the check worth keeping;
    `data_type_of` echoes the handle's declared type, which makes the sweep's type
    comparison vacuous - stated plainly in the module docstring rather than left for
    someone to discover.
    """

    def exists(self, *, input: ScratchHandle) -> bool:
        self._recorder.record("table", "exists", {"input": input})
        return input in self._recorder.written

    def data_type_of(self, *, input: ScratchHandle) -> DataType:
        self._recorder.record("table", "data_type_of", {"input": input})
        return input.data_type


def recording_toolbox() -> tuple[Toolbox, Recorder]:
    """A Toolbox whose four ports share one Recorder.

    The four `cast`s are the `__getattr__` trade described in the module docstring.
    They are the only ones in the package, and they are why this module - and not
    every operation test - carries the compromise.
    """
    recorder = Recorder()
    toolbox = Toolbox(
        geometry=cast("GeometryOps", _RecordingPort("geometry", recorder)),
        table=cast("TableOps", _RecordingTableOps("table", recorder)),
        cartographic=cast("CartographicOps", _RecordingPort("cartographic", recorder)),
        graph=cast("GraphOps", _RecordingPort("graph", recorder)),
    )
    return toolbox, recorder
