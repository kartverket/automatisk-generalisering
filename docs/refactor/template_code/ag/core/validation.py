"""TEMPLATE — not shipped. Target module: `src/ag/core/validation.py`.

Static validation. No cluster, no credentials, no data, no arcpy.

ONE ENTRY POINT, `validate`. Run in CI and again at orchestrator startup, from this
same function. Three implementations would drift.

Findings accumulate rather than raise, so one run reports everything wrong at once
instead of one thing per attempt.

THE LAYERING RULE THIS MODULE SITS IN THE MIDDLE OF

    Nothing that can fail at import may be deferred to plan.
    Nothing that can fail at plan may be deferred to the pod.

So this module holds exactly what CANNOT be made structural or checked at import.
Every check's docstring should say why. The refactor keeps deleting checks by making
things impossible - two have gone in this pass alone - and the surviving set should
read as a legible list of what the type system cannot express, not as accumulated
habit.

WHAT WAS DELETED, AND WHAT REPLACED IT

    check_handle_names_unique_per_stage   handles are class attributes now, and two
                                          attributes in one class body cannot share
                                          a name. The check policed a property
                                          Python already guarantees - and it was
                                          also wrong, flagging every StageOutput
                                          that named a handle an operation writes,
                                          which is the required wiring.

    check_sources_agree                   an ExternalSource is declared once, in
                                          sources.py. There is nothing to reconcile.

CHECKS SPLIT BY VOCABULARY, which is what the two IO types buy:

    inside a stage   ScratchHandle-level. Catches in-place mutation, misordering,
                     handles written but never used, and handles borrowed from
                     another stage.
    across stages    DataObject-level. Catches cycles, ambiguous producers, and
                     legality mismatches.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from ag.core.data_objects import (
    Derived,
    ExternalSource,
    LineageRoot,
    ProductIdentity,
    lineage_roots,
)
from ag.core.operations import ScratchHandle
from ag.core.pipeline import Stage, StageRegistry


class Severity(Enum):
    """ERROR aborts the run. WARNING is reported and does not.

    The distinction is whether the finding describes something that will produce a
    wrong result, or something that merely wastes work. A handle written and never
    read costs disk; a handle borrowed from another stage produces a missing dataset
    in the pod.
    """

    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class Finding:
    severity: Severity
    where: str
    message: str

    def __str__(self) -> str:
        return f"{self.severity.value}: {self.where}: {self.message}"


def _error(where: str, message: str) -> Finding:
    return Finding(Severity.ERROR, where, message)


def _warning(where: str, message: str) -> Finding:
    return Finding(Severity.WARNING, where, message)


def validate(
    registry: StageRegistry,
    ranking: object,  # ScaleRanking; loose to avoid an import cycle
    rules: Sequence[object],  # ClassificationRule
) -> list[Finding]:
    """Every static check, in one pass.

    Takes the REGISTRY rather than one Pipeline: over half these invariants are
    cross-pipeline - one producer per Derived, one publisher per identity, no cycle
    in the stage graph, no pipeline reading what it publishes - and a per-pipeline
    entry point could only ever check the intra-pipeline half.
    """
    findings: list[Finding] = []
    for stage in registry.stages:
        findings.extend(check_operations_produce_something(stage))
        findings.extend(check_one_writer_per_handle(stage))
        findings.extend(check_operation_order(stage))
        findings.extend(check_stage_io_is_wired(stage))
        findings.extend(check_stage_uses_own_handles(stage))
        findings.extend(warn_unused_handles(stage))
    findings.extend(check_stage_tags_match_pipeline(registry))
    findings.extend(check_derived_names_unique(registry))
    findings.extend(check_one_producer(registry))
    findings.extend(check_one_publisher_per_identity(registry))
    findings.extend(check_stage_graph_acyclic(registry))
    findings.extend(check_origin_is_reachable(registry))
    findings.extend(check_no_coarser_input(registry, ranking))
    findings.extend(check_no_self_read(registry))
    findings.extend(check_publications(registry, rules))
    return findings


# ---------------------------------------------------------------------------
# Inside a stage - ScratchHandle level
# ---------------------------------------------------------------------------


def check_operations_produce_something(stage: Stage) -> list[Finding]:
    """Every operation must declare at least one output.

    NOT STRUCTURAL because an operation with no Out parameter is a perfectly legal
    Python function; only the stage's use of it makes the omission a defect.

    An operation that consumes something and produces nothing is either dead code or
    an undeclared IN-PLACE MUTATION - it modified its input and told nobody.

    This is the check that catches the live bug: `calculate_polygon_values` calls
    AddField/CalculateField on `simplify_polygons___...` and produces no file any
    other module reads. Anything deriving dependencies from declared IO concludes it
    is a leaf with no consumers - safe to run last, or concurrently with
    `polygon_propogate_displacement`. Both wrong; the second is a write-write race on
    the same feature class.

    RUN THIS AGAINST THE CURRENT CODEBASE FIRST. If it does not flag
    calculate_polygon_values, the model is wrong somewhere, and that is worth knowing
    before anything else is built.
    """
    return [
        _error(
            f"{stage.qualified_name}/{call.operation}",
            "operation declares no output - either dead code or an undeclared "
            "in-place mutation of one of its inputs",
        )
        for call in stage.operations
        if not call.outputs
    ]


def check_one_writer_per_handle(stage: Stage) -> list[Finding]:
    """Each ScratchHandle is written by at most one operation in the stage.

    NOT STRUCTURAL because it is a property of the operation LIST, which is data.

    Two operations writing the same handle is the intra-stage form of in-place
    mutation, and it makes the second one's effect invisible to anything reading the
    declarations.

    Note reading is unconstrained: a context handle may be read by every operation
    in the stage. It is WRITING that must be unique.
    """
    writers: dict[ScratchHandle, list[str]] = {}
    for call in stage.operations:
        for handle in call.writes():
            writers.setdefault(handle, []).append(call.operation)
    return [
        _error(
            f"{stage.qualified_name}/{handle.name}",
            f"written by more than one operation: {sorted(ops)}",
        )
        for handle, ops in writers.items()
        if len(ops) > 1
    ]


def check_operation_order(stage: Stage) -> list[Finding]:
    """No operation reads a handle that a LATER operation writes.

    Operations run in listed order, so this is the whole correctness condition for
    the list - and the reason an intra-stage DAG is unnecessary. Rather than derive
    an order, check the author's.

    A stage input handle is available from the start; anything else must have been
    written by an earlier operation.
    """
    available = {stage_input.handle for stage_input in stage.inputs}
    findings: list[Finding] = []
    for call in stage.operations:
        for handle in call.reads():
            if handle not in available:
                findings.append(
                    _error(
                        f"{stage.qualified_name}/{call.operation}",
                        f"reads {handle.name!r} before anything writes it - either "
                        "it is missing from the stage inputs, or the operation list "
                        "is out of order",
                    )
                )
        available.update(call.writes())
    return findings


def check_stage_io_is_wired(stage: Stage) -> list[Finding]:
    """Declared stage IO must actually be used.

    A StageInput nothing reads is a wasted download - potentially gigabytes, per
    partition. A StageOutput nothing writes is a stage that will fail at upload time
    after doing all its work, which is the worst moment to discover it.

    Both are cheap to catch and neither has false positives.
    """
    read = {handle for call in stage.operations for handle in call.reads()}
    written = {handle for call in stage.operations for handle in call.writes()}
    findings = [
        _error(
            f"{stage.qualified_name}/{si.handle.name}",
            f"declared as a stage input from {si.obj!r} but no operation reads it - "
            "this downloads data nothing uses, once per partition",
        )
        for si in stage.inputs
        if si.handle not in read
    ]
    findings.extend(
        _error(
            f"{stage.qualified_name}/{so.handle.name}",
            f"declared as the stage output for {so.obj!r} but no operation writes "
            "it - the stage would fail at upload after all its work",
        )
        for so in stage.outputs
        if so.handle not in written
    )
    return findings


def check_stage_uses_own_handles(stage: Stage) -> list[Finding]:
    """Every handle a stage touches comes from the handle class it declares.

    NOT STRUCTURAL, and not catchable at import either: `Network.merged` is a
    perfectly good ScratchHandle and type-checks anywhere a handle is accepted. The
    ordinary copy-paste - a ConflictResolution operation still referencing a Network
    handle - was undetectable before `namespace` existed, and failed in the pod as a
    missing dataset, after fan-out had already moved the data.

    This is the check `Stage.handles` exists for, and the reason ScratchHandle
    carries `namespace` at all.
    """
    expected = stage.handles.__qualname__
    seen: dict[str, set[str]] = {}
    for handle in stage.all_handles():
        if handle.namespace != expected:
            seen.setdefault(handle.namespace, set()).add(handle.name)
    return [
        _error(
            f"{stage.qualified_name}",
            f"uses handles from {namespace!r} ({sorted(names)}) but declares "
            f"handles={expected!r}. A handle from another stage's class resolves to "
            "a path in that stage's workspace, which this pod never creates.",
        )
        for namespace, names in seen.items()
    ]


def warn_unused_handles(stage: Stage) -> list[Finding]:
    """A handle written by an operation, read by nothing, and named by no
    StageOutput. Legal, usually dead work - hence WARNING, not ERROR."""
    read = {handle for call in stage.operations for handle in call.reads()}
    exported = {so.handle for so in stage.outputs}
    return [
        _warning(
            f"{stage.qualified_name}/{handle.name}",
            f"written by {call.operation} but read by nothing and named by no "
            "StageOutput - the work that produced it is discarded",
        )
        for call in stage.operations
        for handle in call.writes()
        if handle not in read and handle not in exported
    ]


# ---------------------------------------------------------------------------
# Across stages - DataObject level
# ---------------------------------------------------------------------------


def check_stage_tags_match_pipeline(registry: StageRegistry) -> list[Finding]:
    """Every Stage agrees with its Pipeline on scale and object_name.

    CANNOT BE AN IMPORT-TIME CHECK: a Stage is fully constructed before the Pipeline
    that lists it exists, so there is nothing to compare against at construction.
    This is the reason the tags are repeated on each Stage rather than inherited -
    a Stage that could not say what it is without a Pipeline lookup would make every
    consumer of a bare Stage worse.

    A mismatch is not cosmetic. The tags reach the scratch path, the Job name, run
    selection and the placement tag group, so a stage tagged with the wrong scale
    writes into another pipeline's prefix.
    """
    return [
        _error(
            stage.qualified_name,
            f"tagged ({stage.scale}, {stage.object_name}) but listed by the "
            f"pipeline ({pipeline.scale}, {pipeline.object_name})",
        )
        for pipeline in registry.pipelines.values()
        for stage in pipeline.stages
        if stage.key != pipeline.key
    ]


def check_derived_names_unique(registry: StageRegistry) -> list[Finding]:
    """Derived NAMES must be unique within a pipeline.

    THIS IS THE CHECK THAT JUSTIFIES LEAVING `Derived("selected_roads")` A LITERAL.
    The name is declared once and no consumer requires it to match its symbol, so it
    is a value - but locations.scratch_location builds a remote path from
    `{run_id}/{scale}/{object}/{stage}/{obj.name}`, and Derived is eq=False, so two
    DISTINCT objects sharing a name string compute the SAME LOCATION and one
    silently overwrites the other. check_one_producer does not catch it: it compares
    object identity, and these are different objects.

    SCOPED PER PIPELINE, WHICH IS STRICTER THAN THE PATH SCHEME REQUIRES. The path
    carries a `{stage.name}` segment, so two same-named Derived in different stages
    do not collide today. The extra strictness is deliberate: this design sells
    regrouping operations across stages as a free edit, and a regroup that merges
    two stages would turn a latent duplicate into a silent overwrite at exactly the
    moment nobody is looking for one. Per pipeline also gives readable
    `--invalidate-from` messages.
    """
    producer = registry.producer_of()
    by_pipeline: dict[object, dict[str, list[str]]] = {}
    for obj, stage in producer.items():
        names = by_pipeline.setdefault(stage.key, {})
        names.setdefault(obj.name, []).append(stage.qualified_name)

    return [
        _error(
            f"{key}/{name}",
            f"more than one Derived declares the name {name!r} in this pipeline "
            f"(produced by {sorted(set(stages))}) - these compute the same scratch "
            "location and would overwrite each other",
        )
        for key, names in by_pipeline.items()
        for name, stages in names.items()
        if len(stages) > 1
    ]


def check_one_producer(registry: StageRegistry) -> list[Finding]:
    """Exactly one stage produces each Derived.

    NOT HYGIENE - a PRECONDITION for the whole derivation mechanism. Two producers
    makes the edge ambiguous and derivation silently picks one. Do not let anyone
    later relax it as "too strict".
    """
    producers: dict[Derived, list[str]] = {}
    for stage in registry.stages:
        for obj in stage.produces():
            producers.setdefault(obj, []).append(stage.qualified_name)
    return [
        _error(
            f"{obj!r}",
            f"produced by more than one stage: {sorted(stages)} - the dependency "
            "edge is ambiguous and derivation would silently pick one",
        )
        for obj, stages in producers.items()
        if len(stages) > 1
    ]


def check_one_publisher_per_identity(registry: StageRegistry) -> list[Finding]:
    """No two pipelines publish the same ProductIdentity.

    The cross-pipeline twin of check_one_producer, and NOT covered by it:
    two pipelines can publish two DIFFERENT Derived objects to the SAME identity,
    so every Derived has one producer and the identity still has two. Both
    identity_producer and publish_of use the first entry they see, so the loser is
    dropped without a word and the dependency edge points at whichever pipeline
    happened to be flattened first.
    """
    publishers: dict[ProductIdentity, list[str]] = {}
    for pipeline in registry.pipelines.values():
        for publish in pipeline.publishes:
            publishers.setdefault(publish.identity, []).append(
                f"{pipeline.scale}/{pipeline.object_name}"
            )
    return [
        _error(
            f"{identity!r}",
            f"published by more than one pipeline: {sorted(pipelines)}",
        )
        for identity, pipelines in publishers.items()
        if len(pipelines) > 1
    ]


def check_origin_is_reachable(registry: StageRegistry) -> list[Finding]:
    """A Derived's declared origin must be reachable through the wiring.

    `origin` is a human judgement - "this is fundamentally building data" - so it
    cannot be derived. But it CAN be sanity-checked: every root named in an object's
    origin must actually reach the stage that produces it, directly or transitively.

    This catches the copy-paste error where an object is given the wrong origin,
    which matters because origin drives IDENTITY - which lineage the object lives
    under.

    It deliberately does NOT check the converse. A stage may legitimately read roots
    that are not in its output's origin: NVDB_ROADS reaches the displacement stage
    but is not part of DISPLACED's lineage, because no road data is merged in. That
    asymmetry is the whole point of the origin-versus-legality split, and a check
    requiring equality would forbid the normal case.
    """
    producer = registry.producer_of()
    findings: list[Finding] = []
    for obj, stage in producer.items():
        reachable = _reachable_roots(stage, registry, set())
        for root in obj.origin:
            if root not in reachable:
                findings.append(
                    _error(
                        f"{stage.qualified_name}/{obj.name}",
                        f"declares origin {root!r}, but that root never reaches this "
                        "stage through any input chain",
                    )
                )
    return findings


def _reachable_roots(
    stage: Stage,
    registry: StageRegistry,
    seen: set[str],
) -> frozenset[LineageRoot]:
    if stage.qualified_name in seen:
        return frozenset()
    seen.add(stage.qualified_name)
    producer = registry.producer_of()
    by_identity = registry.identity_producer()
    found: set[LineageRoot] = set()
    for stage_input in stage.inputs:
        obj = stage_input.obj
        if isinstance(obj, ExternalSource):
            found.add(obj)
        elif isinstance(obj, ProductIdentity):
            found.add(obj)
            upstream = by_identity.get(obj)
            if upstream is not None:
                found.update(_reachable_roots(upstream, registry, seen))
        else:
            found.update(lineage_roots(obj))
            upstream = producer.get(obj)
            if upstream is not None:
                found.update(_reachable_roots(upstream, registry, seen))
    return frozenset(found)


def check_stage_graph_acyclic(registry: StageRegistry) -> list[Finding]:
    """And it does NOT follow from the operations being sensible.

    Grouping is manual, so a bad grouping produces a stage cycle from a perfectly
    acyclic set of operations:

        op1 (stage A) -> op2 (stage B) -> op3 (stage A)

    The operations are fine. The stages deadlock: A cannot finish before B starts,
    and B cannot start before A finishes. This is the MAIN WAY A BAD GROUPING FAILS
    and it is invisible unless checked explicitly.

    The fix is always a regrouping, never a declaration change - which is exactly the
    property that separating ScratchHandles from DataObjects buys.
    """
    raise NotImplementedError(
        "Kahn over graph.derive_stage_dependencies; report the cycle members and, "
        "ideally, the object chain that induced it"
    )


def check_no_coarser_input(
    registry: StageRegistry,
    ranking: object,
) -> list[Finding]:
    """No input ranks coarser than the consuming stage's own scale.

    N25 reading N100 is an error. Free, because the ranking exists anyway. RAW ranks
    below everything so it never trips.
    """
    raise NotImplementedError


def check_no_self_read(registry: StageRegistry) -> list[Finding]:
    """No pipeline reads an identity it publishes.

    Not covered by check_one_producer - there is still exactly one producer. It is
    the failure mode of pointing a ladder input at your own scale: building_n100
    reading N100_BUILDING_POLYGONS, which is its own output.

    Now a symbol comparison rather than a (scale, dataset) string match, so it also
    catches the case where the two would have been spelled differently.
    """
    findings: list[Finding] = []
    for pipeline in registry.pipelines.values():
        published = {publish.identity for publish in pipeline.publishes}
        for stage in pipeline.stages:
            for obj in stage.consumes():
                if isinstance(obj, ProductIdentity) and obj in published:
                    findings.append(
                        _error(
                            stage.qualified_name,
                            f"reads {obj!r}, which this pipeline publishes - a "
                            "ladder input pointed at its own scale",
                        )
                    )
    return findings


def check_publications(
    registry: StageRegistry,
    rules: Sequence[object],
) -> list[Finding]:
    """Every publication destination is consistent with its classification.

    MUST RUN BEFORE ANY POD IS CREATED. Discovering at the end of a three-hour run
    that fan-in may not write its output is the worst available failure mode.

    Each publication defaults to policy.classification_of; `reclassify_to` overrides
    it, and policy.publication_classification is the two combined. A reclassification
    that is LESS restrictive is the single loud, greppable act in the whole design,
    and it takes effect at publication - physically the on-prem to cloud copy - so
    the guard fires at one discrete auditable point.

    The destination now comes from the Publish's ProductIdentity rather than from
    whichever pipeline happened to consume the product, which is what makes this
    checkable for a product nobody consumes.
    """
    raise NotImplementedError(
        "for each Publish: policy.publication_classification(publish.obj, ...) must "
        "permit storage at publish.identity.location; PREM_ONLY bound for gs:// is "
        "the error to catch"
    )


# ---------------------------------------------------------------------------
# One thing that cannot be checked here at all
# ---------------------------------------------------------------------------


def not_statically_checkable() -> None:
    """Recorded so nobody adds a weak proxy for it later.

    TWO CLAIMS ABOUT DATA, NOT ABOUT DECLARATIONS:

    1. That all operations in a stage genuinely share a partitioning.
    2. That context_radius_m is large enough for the whole chain in that stage.

    Both are validated the same way: run a stage at K=4 and K=16 and DIFF THE
    OUTPUTS. Genuinely partition-independent logic with an adequate halo produces
    identical results. Where they differ, there is either a partition dependence or
    an undersized radius, and the diff identifies which features.

    BUILD THAT HARNESS AGAINST THE CURRENT IMPLEMENTATION, BEFORE ANY K8S WORK. It
    finds today's violations mechanically rather than by team discipline, and it
    becomes the regression test for the rewrite - "did the rewrite preserve
    semantics" is otherwise very hard to answer for geometric logic, and it gets
    harder once the old implementation stops running.
    """
