"""TEMPLATE — not shipped. Target module: `src/ag/core/selection.py`.

Run scoping: what a human asks for, and how it expands.

A run is a SELECTION over the flat stage registry, optionally expanded by a closure.
That one mechanism covers every case: run one object at one scale, rerun everything
affected by an operation change, or run the lot.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from ag.core.types import ObjectName, OperationName, RunId, Scale, StageName
from ag.core.graph import derive_stage_dependencies
from ag.core.pipeline import Stage, StageRegistry
from ag.core.validation import Finding


class Closure(Enum):
    """Two closures answering different questions.

    DOWNSTREAM  "what is affected by what I changed" - the common case.
    UPSTREAM    "what do I need in order to run this at all".
    """

    NONE = "none"
    DOWNSTREAM = "downstream"
    UPSTREAM = "upstream"
    BOTH = "both"


@dataclass(frozen=True)
class RunRequest:
    """What a human asks for. The planner turns it into a RunPlan.

    Every predicate is optional; None means "no constraint". They AND together, so
    the examples read directly:

        RunRequest(run_id, scales={Scale.N100}, objects={ObjectName.ROAD})
            every stage tagged road + N100, nothing else

        RunRequest(run_id, operations={"simplify_polygons"}, closure=DOWNSTREAM)
            every stage using that operation, plus everything affected

        RunRequest(run_id)
            everything

    SELECT BY OPERATION, NOT BY OBJECT TAG, for "we changed a core generalization
    operation". The operation may be used by stages under other objects, which an
    object tag would miss, while also over-selecting stages under that object which
    do not use it at all.
    """

    run_id: RunId
    scales: frozenset[Scale] | None = None
    objects: frozenset[ObjectName] | None = None
    operations: frozenset[OperationName] | None = None
    stages: frozenset[StageName] | None = None
    closure: Closure = Closure.NONE


def select_stages(request: RunRequest, registry: StageRegistry) -> frozenset[StageName]:
    """Apply the predicates, then expand by closure direction."""
    selected = {
        stage.qualified_name for stage in registry.stages if matches(request, stage)
    }
    dependencies = derive_stage_dependencies(registry)

    if request.closure in (Closure.UPSTREAM, Closure.BOTH):
        selected |= _reachable(selected, dependencies)
    if request.closure in (Closure.DOWNSTREAM, Closure.BOTH):
        selected |= _reachable(selected, _reverse(dependencies))
    return frozenset(selected)


def matches(request: RunRequest, stage: Stage) -> bool:
    if request.scales is not None and stage.scale not in request.scales:
        return False
    if request.objects is not None and stage.object_name not in request.objects:
        return False
    if request.stages is not None and stage.name not in request.stages:
        return False
    if request.operations is not None and not any(
        call.operation in request.operations for call in stage.operations
    ):
        return False
    return True


def _reverse(
    dependencies: Mapping[StageName, frozenset[StageName]],
) -> Mapping[StageName, frozenset[StageName]]:
    reversed_map: dict[StageName, set[StageName]] = {k: set() for k in dependencies}
    for node, deps in dependencies.items():
        for dep in deps:
            reversed_map.setdefault(dep, set()).add(node)
    return {k: frozenset(v) for k, v in reversed_map.items()}


def _reachable(
    seed: set[StageName],
    edges: Mapping[StageName, frozenset[StageName]],
) -> set[StageName]:
    reached: set[StageName] = set()
    queue = list(seed)
    while queue:
        node = queue.pop()
        for neighbour in edges.get(node, frozenset()):
            if neighbour not in reached and neighbour not in seed:
                reached.add(neighbour)
                queue.append(neighbour)
    return reached


def check_upstream_available(
    selected: frozenset[StageName],
    registry: StageRegistry,
) -> list[Finding]:
    """UPSTREAM IS AN ERROR BY DEFAULT, NOT AN AUTO-EXPANSION.

    If a selected stage consumes an object that no selected stage produces, that
    object must already exist in the archive. If it does not, fail and NAME it
    rather than quietly widening the run.

    Silently expanding a request for one object into a six-hour run is the kind of
    surprise that costs a night. Same human-oversight reasoning as a classification
    mismatch: a scope that cannot be satisfied is a decision, not something to
    resolve automatically. Tell them to add --with-upstream.

    THIS IS THE ONE PLACE EXISTENCE CHECKING ENTERS THE DESIGN, which is why the
    object-store atomicity question matters: if a partially-written object can look
    complete, "the input exists" becomes a wrong answer and the run proceeds on a
    truncated file. On an NFS substrate the equivalent question is whether a
    half-written directory tree is distinguishable from a finished one - it is not,
    which argues for an explicit completion marker either way.
    """
    raise NotImplementedError(
        "for each selected stage's inputs not produced by a selected stage: "
        "ExternalSource and ProductIdentity -> the declared location must exist; "
        "Derived -> its producing stage must have a surviving archived or scratch "
        "output, else error naming it and suggesting --with-upstream"
    )
