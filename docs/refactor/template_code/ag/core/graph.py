"""TEMPLATE — not shipped. Target module: `src/ag/core/graph.py`.

Dependency derivation. One rule, applied to stages.

    Stage B depends on stage A iff B's declared inputs include one of A's declared
    outputs.

Nothing declares a dependency and nothing declares a sequence.

Now that stage IO is declared rather than derived from operations, this module got
much smaller - which is the right trade. The stage author writes what the stage
downloads and uploads; everything internal is ScratchHandles and none of it appears here.

WHY DERIVE EDGES RATHER THAN DECLARE THEM

Under the one-producer rule the two carry IDENTICAL ordering information - naming an
output uniquely names its producer. The difference is what else each artifact does:

  - The FILE is the dependency. The producing stage is the mechanism that brings it
    into existence, not the thing depended on.
  - IO must be declared regardless: the pod has to know what to download, pinning
    needs it, classification is the join over inputs, placement follows from input
    locations. Declared edges would be load-bearing for ordering and nothing else.
  - Refactoring. Split a stage in two, with the second producing the original
    output: every consumer is unchanged, because consumers depend on the data.

The one thing derivation cannot express is ordering with NO data reason ("run this
last"). In this design that is mostly moot: in-place mutation is forbidden, so every
real dependency is a data dependency.
"""

from __future__ import annotations

from collections.abc import Hashable, Mapping, Sequence
from typing import TypeVar

from ag.core.types import StageName, StorageScope
from ag.core.data_objects import Derived, ProductIdentity
from ag.core.operations import ScratchHandle
from ag.core.pipeline import Stage, StageRegistry

NodeT = TypeVar("NodeT", bound=Hashable)


def topological_order(
    nodes: Sequence[NodeT],
    dependencies: Mapping[NodeT, frozenset[NodeT]],
) -> tuple[NodeT, ...]:
    """Kahn's algorithm, ties broken by position in `nodes` so the result is
    deterministic and diffable across runs.

    Raises on a cycle; validation should have caught it first and reported the
    members, which is a far better error than this one.
    """
    position = {node: index for index, node in enumerate(nodes)}
    remaining = {node: set(dependencies.get(node, frozenset())) for node in nodes}
    ordered: list[NodeT] = []

    while remaining:
        ready = sorted(
            (node for node, deps in remaining.items() if not deps),
            key=lambda node: position[node],
        )
        if not ready:
            raise ValueError(f"cycle among: {sorted(str(n) for n in remaining)}")
        for node in ready:
            ordered.append(node)
            del remaining[node]
        for deps in remaining.values():
            deps.difference_update(ready)

    return tuple(ordered)


def derive_stage_dependencies(
    registry: StageRegistry,
) -> Mapping[StageName, frozenset[StageName]]:
    """ONE graph over all stages. There is no pipeline-level DAG, because there is
    no pipeline at runtime.

    This is what makes arealdekke_n25 depend on arealdekke_n10 and on nothing else.
    It does not wait for road_n10, which a scale-major nested loop would have forced
    even though no data flows between them.

    TWO WAYS AN EDGE ARISES, and missing the second one is a silent correctness bug:

      1. OBJECT identity - the consumer names the very Derived a stage produces.
         This is the intra-pipeline case, where both stages are written in the same
         module and share the symbol.
      2. PUBLISHED identity - the consumer names a ProductIdentity some pipeline
         publishes. This is the CROSS-pipeline case. building_n100 reads N100_ROAD
         because from building's side it is external data with a location;
         road_n100 produces a Derived and promotes it to that identity with a
         Publish. The Derived and the identity are different objects, so matching on
         the Derived alone finds nothing.

    Handling only (1) makes road_n100 and building_n100 look independent - they
    could run in either order, and building would displace against whatever roads
    happened to be in the archive. No error, just quietly wrong maps.

    Since both sides now reference the same ProductIdentity symbol, case 2 is a
    dictionary lookup rather than the (scale, dataset) string match it used to be.
    """
    producer = registry.producer_of()
    by_identity = registry.identity_producer()

    def upstream(stage: Stage) -> frozenset[str]:
        names: set[str] = set()
        for obj in stage.consumes():
            if isinstance(obj, Derived) and obj in producer:
                names.add(producer[obj].qualified_name)  # case 1
            elif isinstance(obj, ProductIdentity) and obj in by_identity:
                names.add(by_identity[obj].qualified_name)  # case 2
        return frozenset(names) - {stage.qualified_name}

    return {stage.qualified_name: upstream(stage) for stage in registry.stages}


def operation_order(stage: Stage) -> tuple[str, ...]:
    """Operations run in LISTED ORDER. This exists only to make that explicit.

    Deliberately not a topological sort. Within one pod, in one workspace, a list is
    enough - the author grouped and sequenced them on purpose, and a derived order
    would add a mechanism to reproduce information the list already carries.

    What IS worth checking is that the list is consistent: no operation reads a
    ScratchHandle that a later operation writes. See validation.check_operation_order.
    """
    return tuple(call.operation for call in stage.operations)


def internal_handles(stage: Stage) -> frozenset[ScratchHandle]:
    """Declared handles that live and die inside the pod.

    Written by some operation, and named by no StageOutput. These never get a URI,
    never get packed into an object, and nothing uploads them. Every one of them is a
    round trip saved relative to putting its producing operation in its own stage -
    and since a .gdb is a directory tree, each saved round trip is an archive plus an
    unarchive, not just a copy.

    This is most of why grouping operations into a stage pays.
    """
    exported = {out.handle for out in stage.outputs}
    written = {handle for call in stage.operations for handle in call.writes()}
    return frozenset(written - exported)


def edge_scope(producer: Stage, consumer: Stage) -> StorageScope:
    """Which namespace an edge crosses - DERIVED from tags, never declared.

    Same tag group means the two stages belong to one pipeline, so the handoff may
    stay in run-scratch. A different tag group is the pipeline boundary, and that
    handoff goes through the archive even though no pipeline object exists at
    runtime.

    The SUBSTRATE behind each scope is a deployment choice - see staging.py. Nothing
    above this line changes if run-scratch moves from object storage to NFS.
    """
    if producer is consumer:
        return StorageScope.POD_LOCAL
    if producer.key == consumer.key:
        return StorageScope.RUN_SCRATCH
    return StorageScope.ARCHIVE
