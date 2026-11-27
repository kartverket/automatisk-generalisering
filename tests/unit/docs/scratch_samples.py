"""The code samples of `docs/user_guide/scratch.md`, as the page shows them.

What: every fenced Python block of the guide is the text of this module between a
`# sample: <key>` line and its `# end: <key>` line. `test_scratch_user_guide.py` asserts
that the two texts are equal, runs each sample over the memory fakes and asserts the
layer names, manifest entries and error messages the page shows. So an edit to the page,
to this module or to the code it documents fails there, naming the other side.

Why: a guide whose samples are not run drifts from the code the first time a rule
changes, and a sample a reader copies must work as printed. The manager's root is a fixed
string and nothing here creates a workspace on disk, so every path and every message is
the same on every machine and the page can quote them whole.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, TypeAlias

# sample: imports
from ag.adapters.fakes.memory.cartographic_ops import MemoryCartographicOps
from ag.adapters.fakes.memory.geometry_ops import MemoryGeometryOps
from ag.adapters.fakes.memory.store import MemoryStore
from ag.adapters.fakes.memory.table_ops import MemoryTableOps
from ag.core.errors import InjectionError
from ag.core.handles import (
    INJECTED,
    Handles,
    In,
    Out,
    ScratchHandle,
    ScratchScope,
    handle,
)
from ag.core.operations import operation
from ag.core.types import DataType, PodRole
from ag.ports import NOT_INJECTED, Attr, Comparison, Toolbox
from ag.staging.errors import StagingError, WorkspaceError
from ag.staging.scratch import ScratchFileManager
from tests.support.cases import multilines

# end: imports


# sample: setup
STAGE = "n100/road/thin_roads"
"""The stage's qualified name; the runtime computes it, the samples spell it."""

CALL = f"{STAGE}:thin_roads"
"""The identity of the one operation call the sample pod runs."""

NAMED = Attr.cmp("name", Comparison.NE, "")
"""The one predicate every sample selects with: the roads that carry a name."""


class Roads(Handles):
    """The stage's declared handles: what its operations read and write."""

    source = handle()
    thinned = handle()


class NoGraph:
    """`GraphOps` has no members yet, so any object serves as its fake."""


def memory_toolbox(store: MemoryStore) -> Toolbox:
    """Every port over one in-memory store."""
    return Toolbox(
        geometry=MemoryGeometryOps(store=store),
        table=MemoryTableOps(store=store),
        cartographic=MemoryCartographicOps(store=store),
        graph=NoGraph(),
    )


def fan_in_pod(
    store: MemoryStore, *, calls: tuple[str, ...] = (CALL,)
) -> ScratchFileManager:
    """The manager the stage's fan-in pod would hold, over the same store."""
    return ScratchFileManager(
        root="/scratch",
        stage=STAGE,
        calls=calls,
        role=PodRole.FAN_IN,
        table=MemoryTableOps(store=store),
    )


# end: setup


# sample: handle_name
def handle_name() -> ScratchHandle:
    return (
        fan_in_pod(MemoryStore()).scope_for(CALL).child("clean").child("named")("kept")
    )


# end: handle_name


# sample: minimal
@operation
def thin_roads(
    *,
    source: In,
    output: Out,
    tb: Toolbox = NOT_INJECTED,
    scratch: ScratchScope = INJECTED,
) -> None:
    """Keeps the named roads, one row per part."""
    singlepart = scratch("singlepart")
    tb.geometry.explode_multipart(input=source, output=singlepart)
    tb.geometry.select(input=singlepart, where=NAMED, output=output)


# end: minimal


# sample: helper_with_child
def _parts(*, roads: In, output: Out, tb: Toolbox, scratch: ScratchScope) -> None:
    """The named roads of `roads`, one row per part, written to `output`."""
    exploded = scratch("exploded")
    tb.geometry.explode_multipart(input=roads, output=exploded)
    tb.geometry.select(input=exploded, where=NAMED, output=output)


@operation
def thin_roads_with_helper(
    *,
    source: In,
    output: Out,
    tb: Toolbox = NOT_INJECTED,
    scratch: ScratchScope = INJECTED,
) -> None:
    _parts(roads=source, output=output, tb=tb, scratch=scratch.child("parts"))


# end: helper_with_child


# sample: helper_twice
@operation
def thin_roads_twice(
    *,
    source: In,
    output: Out,
    tb: Toolbox = NOT_INJECTED,
    scratch: ScratchScope = INJECTED,
) -> None:
    first_pass = scratch("first_pass")
    _parts(roads=source, output=first_pass, tb=tb, scratch=scratch.child("parts"))
    _parts(roads=first_pass, output=output, tb=tb, scratch=scratch.child("parts"))


# end: helper_twice


# sample: helper_tagged
@operation
def thin_roads_tagged(
    *,
    source: In,
    output: Out,
    tb: Toolbox = NOT_INJECTED,
    scratch: ScratchScope = INJECTED,
) -> None:
    first_pass = scratch("first_pass")
    _parts(roads=source, output=first_pass, tb=tb, scratch=scratch.child("parts"))
    _parts(
        roads=first_pass,
        output=output,
        tb=tb,
        scratch=scratch.child("parts", tag="reranked"),
    )


# end: helper_tagged


# sample: caller_names_outputs
def _exploded(*, roads: In, output: Out, tb: Toolbox) -> None:
    """One row per part. Names nothing of its own, so it takes no scope."""
    tb.geometry.explode_multipart(input=roads, output=output)


@operation
def thin_roads_reading_back(
    *,
    source: In,
    output: Out,
    tb: Toolbox = NOT_INJECTED,
    scratch: ScratchScope = INJECTED,
) -> None:
    parts = scratch("parts")
    _exploded(roads=source, output=parts, tb=tb)
    tb.geometry.select(input=parts, where=NAMED, output=output)


# end: caller_names_outputs


# sample: loop
@operation
def thin_roads_in_sweeps(
    *,
    source: In,
    output: Out,
    tb: Toolbox = NOT_INJECTED,
    scratch: ScratchScope = INJECTED,
) -> None:
    for letter in ("a", "b", "e"):
        named = scratch(f"named_{letter}")
        tb.geometry.select(
            input=source, where=Attr.cmp("name", Comparison.EQ, letter), output=named
        )
        _parts(
            roads=named,
            output=scratch(f"parts_{letter}"),
            tb=tb,
            scratch=scratch.child("sweep", tag=letter),
        )
    tb.geometry.explode_multipart(input=source, output=output)


# end: loop


# sample: nested
def _named(*, roads: In, output: Out, tb: Toolbox, scratch: ScratchScope) -> None:
    kept = scratch("kept")
    tb.geometry.select(input=roads, where=NAMED, output=kept)
    tb.geometry.explode_multipart(input=kept, output=output)


def _clean(*, roads: In, output: Out, tb: Toolbox, scratch: ScratchScope) -> None:
    """Explodes, then hands the parts to `_named` one level down."""
    exploded = scratch("exploded")
    tb.geometry.explode_multipart(input=roads, output=exploded)
    _named(roads=exploded, output=output, tb=tb, scratch=scratch.child("named"))


@operation
def thin_roads_nested(
    *,
    source: In,
    output: Out,
    tb: Toolbox = NOT_INJECTED,
    scratch: ScratchScope = INJECTED,
) -> None:
    _clean(roads=source, output=output, tb=tb, scratch=scratch.child("clean"))


# end: nested


# sample: testing
def test_parts_explodes_into_its_own_scratch() -> None:
    store = MemoryStore()
    tb = memory_toolbox(store)
    pod = fan_in_pod(store)
    source = pod.handle(Roads.source)
    case = multilines()
    store.write(source, schema=case.schema, rows=case.rows)

    _parts(
        roads=source,
        output=pod.handle(Roads.thinned),
        tb=tb,
        scratch=pod.scope_for(CALL),
    )

    assert tb.table.exists(input=pod.handle(Roads.thinned))
    assert list(pod.manifest()) == [
        "/scratch/n100_road_thin_roads_thin_roads__fan_in.gdb/exploded"
    ]


# end: testing


# sample: case_unchanged
def case_unchanged() -> ScratchFileManager:
    pod = fan_in_pod(MemoryStore())
    pod.scope_for(CALL)("singlepart")
    return pod


# end: case_unchanged


# sample: case_nested
def case_nested() -> ScratchFileManager:
    pod = fan_in_pod(MemoryStore())
    pod.scope_for(CALL).child("clean").child("named")("kept")
    return pod


# end: case_nested


# sample: case_suffix
def case_suffix() -> ScratchFileManager:
    pod = fan_in_pod(MemoryStore())
    scratch = pod.scope_for(CALL)
    scratch.child("parts")("exploded")
    scratch.child("parts")("exploded")
    scratch.child("parts")("exploded")
    return pod


# end: case_suffix


# sample: case_tagged
def case_tagged() -> ScratchFileManager:
    pod = fan_in_pod(MemoryStore())
    scratch = pod.scope_for(CALL)
    scratch.child("parts")("exploded")
    scratch.child("parts", tag="reranked")("exploded")
    scratch.child("parts", tag="2")("exploded")
    return pod


# end: case_tagged


# sample: case_table
def case_table() -> ScratchFileManager:
    pod = fan_in_pod(MemoryStore())
    counts = pod.scope_for(CALL)("counts", DataType.TABLE)
    assert counts.data_type is DataType.TABLE
    return pod


# end: case_table


# sample: long_labels
AREAS = "attach_the_administrative_area_attributes_to_every_road_segment_of_the_source"
TOPOLOGY = "build_the_topology_over_the_dissolved_network_with_degrees_and_components"
"""Two labels of a helper chain whose names were never shortened by their authors."""

# end: long_labels


# sample: case_shortened
def case_shortened() -> ScratchFileManager:
    pod = fan_in_pod(MemoryStore())
    scratch = pod.scope_for(CALL).child("clean").child(AREAS).child(TOPOLOGY)
    scratch("nodes")
    scratch("nodes_with_their_degree_and_component_recorded_for_the_second_pass")
    scratch(
        "nodes_with_their_degree_their_component_the_rank_of_the_longest_road_"
        "touching_them_and_the_sweep_that_recorded_them"
    )
    return pod


# end: case_shortened


# sample: digest
def windows_apart(full: str) -> str:
    """A digest that is the same for every name, with every window distinct, so every
    shortened name collides and the probe must move on. A stand-in, for the page, for
    the one name in 16 to the 12th that the real digest would give the same window."""
    return "".join(str(window) * 12 for window in range(5)).ljust(64, "f")


def probing_pod(store: MemoryStore) -> ScratchFileManager:
    return ScratchFileManager(
        root="/scratch",
        stage=STAGE,
        calls=(CALL,),
        role=PodRole.FAN_IN,
        table=MemoryTableOps(store=store),
        digest=windows_apart,
    )


# end: digest


# sample: case_probe
def case_probe() -> ScratchFileManager:
    pod = probing_pod(MemoryStore())
    scratch = pod.scope_for(CALL).child("clean")
    scratch.child(AREAS).child(TOPOLOGY)("nodes")
    scratch.child(AREAS + "_again").child(TOPOLOGY)("nodes")
    return pod


# end: case_probe


# sample: error_bad_segment
def error_bad_segment() -> None:
    fan_in_pod(MemoryStore()).scope_for(CALL)("road-parts")


# end: error_bad_segment


# sample: error_unbound
def error_unbound() -> None:
    INJECTED("singlepart")


# end: error_unbound


# sample: error_repeated_leaf
def error_repeated_leaf() -> None:
    scratch = fan_in_pod(MemoryStore()).scope_for(CALL)
    scratch("parts")
    scratch("Parts")


# end: error_repeated_leaf


# sample: error_leaf_too_long
def error_leaf_too_long() -> None:
    fan_in_pod(MemoryStore()).scope_for(CALL).child("clean")("x" * 154)


# end: error_leaf_too_long


# sample: error_every_window_taken
def error_every_window_taken() -> None:
    scratch = probing_pod(MemoryStore()).scope_for(CALL).child("clean")
    for suffix in ("", "_2", "_3", "_4", "_5", "_6"):
        scratch.child(AREAS + suffix).child(TOPOLOGY)("nodes")


# end: error_every_window_taken


# sample: error_declared_over_limit
def error_declared_over_limit() -> None:
    fan_in_pod(MemoryStore()).handle(
        ScratchHandle(name="x" * 161, namespace="guide.Roads")
    )


# end: error_declared_over_limit


# sample: error_illegal_declared
def error_illegal_declared() -> None:
    fan_in_pod(MemoryStore()).handle(
        ScratchHandle(name="veier_æ", namespace="guide.Roads")
    )


# end: error_illegal_declared


# sample: error_declared_case
class Lower(Handles):
    roads = handle()


class Upper(Handles):
    Roads = handle()


def error_declared_case() -> None:
    pod = fan_in_pod(MemoryStore())
    pod.handle(Lower.roads)
    pod.handle(Upper.Roads)


# end: error_declared_case


# sample: error_workspace_too_long
def error_workspace_too_long() -> None:
    ScratchFileManager(
        root="/scratch",
        stage=STAGE + "/" + "x" * 100,
        calls=(),
        role=PodRole.FAN_IN,
        table=MemoryTableOps(store=MemoryStore()),
    )


# end: error_workspace_too_long


# sample: error_alike
def error_alike() -> None:
    fan_in_pod(MemoryStore(), calls=(CALL, f"{STAGE}:Thin_Roads"))


# end: error_alike


# sample: error_unknown_call
def error_unknown_call() -> None:
    fan_in_pod(MemoryStore()).scope_for(f"{STAGE}:other")


# end: error_unknown_call


# sample: error_repeated_call
def error_repeated_call() -> None:
    fan_in_pod(MemoryStore(), calls=(CALL, CALL))


# end: error_repeated_call


# sample: error_role_index
def error_role_index() -> None:
    ScratchFileManager(
        root="/scratch",
        stage=STAGE,
        calls=(CALL,),
        role=PodRole.POD,
        table=MemoryTableOps(store=MemoryStore()),
    )


# end: error_role_index


class Thinning(Protocol):
    """The body of every operation sample: the signature they share."""

    def __call__(
        self, *, source: In, output: Out, tb: Toolbox, scratch: ScratchScope
    ) -> None: ...


OPERATIONS: dict[str, Thinning] = {
    "minimal": thin_roads.fn,
    "helper_with_child": thin_roads_with_helper.fn,
    "helper_twice": thin_roads_twice.fn,
    "helper_tagged": thin_roads_tagged.fn,
    "caller_names_outputs": thin_roads_reading_back.fn,
    "loop": thin_roads_in_sweeps.fn,
    "nested": thin_roads_nested.fn,
}
"""Each operation sample by its marker key; the test runs the body with a bound scope."""

Case: TypeAlias = Callable[[], ScratchFileManager]

CASES: dict[str, Case] = {
    "case_unchanged": case_unchanged,
    "case_nested": case_nested,
    "case_suffix": case_suffix,
    "case_tagged": case_tagged,
    "case_table": case_table,
    "case_shortened": case_shortened,
    "case_probe": case_probe,
}
"""Each naming case by its marker key; the test reads the manifest it returns."""

ERRORS: dict[str, tuple[type[Exception], Callable[[], None]]] = {
    "error_bad_segment": (ValueError, error_bad_segment),
    "error_unbound": (InjectionError, error_unbound),
    "error_repeated_leaf": (WorkspaceError, error_repeated_leaf),
    "error_leaf_too_long": (WorkspaceError, error_leaf_too_long),
    "error_every_window_taken": (WorkspaceError, error_every_window_taken),
    "error_declared_over_limit": (WorkspaceError, error_declared_over_limit),
    "error_illegal_declared": (WorkspaceError, error_illegal_declared),
    "error_declared_case": (WorkspaceError, error_declared_case),
    "error_workspace_too_long": (WorkspaceError, error_workspace_too_long),
    "error_alike": (WorkspaceError, error_alike),
    "error_unknown_call": (StagingError, error_unknown_call),
    "error_repeated_call": (StagingError, error_repeated_call),
    "error_role_index": (StagingError, error_role_index),
}
"""Each error sample by its marker key with the exception type the page names."""
