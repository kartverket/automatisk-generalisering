"""TEMPLATE — not shipped. Target module: `src/ag/core/policy.py`.

Classification and placement.

TWO DIFFERENT QUESTIONS THAT USUALLY COINCIDE

    Placement       where the pod runs. Determined by REACHABILITY. If any external
                    input sits on Scality, the pipeline runs on-prem, because a
                    cloud pod cannot reach on-prem storage.
    Classification  where an output may be STORED. Determined by POLICY.

Location is evidence for placement. It is NOT evidence for classification. A
CLOUD_OK dataset that happens to live on s3:// forces on-prem placement and taints
nothing.

CLASSIFICATION IS COMPUTED OVER STAGE WIRING, NOT OVER `origin`

This is the subtle one, and getting it wrong leaks.

`origin` is lineage - what dataset an object IS. DISPLACED's origin is
BUILDING_N50, because no road data was merged into it. If classification joined over
origin, DISPLACED would come out CLOUD_OK.

But DISPLACED's geometry was determined by restricted NVDB_Roads positions.
Displaced building footprints partially encode the road centrelines they were pushed
away from - a real inference channel, not a theoretical one. So the rule is:

    EVERY ROOT THAT REACHED A STAGE TAINTS EVERYTHING THAT STAGE PRODUCES,
    context included.

Conservative by construction, and it never depends on a human correctly judging
whether an influence is also a leak. When generalization genuinely has removed what
made a source restricted, that judgement has exactly one home: `reclassify_to` on a
Publish, reviewed by a person.

ONLY ONE DIRECTION NEEDS GUARDING

On-prem data must not reach cloud. Cloud data flowing on-prem is always safe - it
moves into the more restrictive environment. One gate, not two, which is why the
common pattern (pull cloud inputs on-prem, process there, return outputs to cloud)
is legitimate by construction.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ag.core.types import Classification, DatasetName, Environment, Scale
from ag.core.data_objects import (
    DataObject,
    Derived,
    ExternalSource,
    LineageRoot,
    ProductIdentity,
)
from ag.core.pipeline import Pipeline, StageRegistry


@dataclass(frozen=True)
class ScaleRanking:
    """Finest to coarsest. A RANKING, NOT A SEQUENCE.

    Its only jobs are making "N25 must not read N100" checkable, and supplying a
    deterministic tie-break when several stages are ready at once. It never orders
    execution - order derives from IO, which is why arealdekke_n25 can start as soon
    as arealdekke_n10 finishes without waiting for road_n10.
    """

    order: tuple[Scale, ...]

    def rank(self, scale: Scale) -> int:
        """RAW ranks below everything, so anything may read it and it never trips
        the coarser-feeds-finer check."""
        return -1 if scale is Scale.RAW else self.order.index(scale)


@dataclass(frozen=True)
class ClassificationRule:
    """Rules live in ONE dedicated file, separate from pipeline code.

    That way a security reviewer can read the entire policy without reading any
    pipeline, and a change to it is a reviewable diff rather than an edit buried in
    a stage.

        ClassificationRule(scale=Scale.N10, dataset=None,       gives=PREM_ONLY)
        ClassificationRule(scale=None, dataset="NVDB_Roads",    gives=PREM_ONLY)

    A rule keys on VALUES - a scale and a dataset name - deliberately. It is written
    by a security reviewer against a policy document, not against this codebase's
    symbols, and it must be able to name a dataset that has no declaration here yet.
    """

    scale: Scale | None
    dataset: DatasetName | None
    gives: Classification

    def matches(self, root: LineageRoot) -> bool:
        return (self.scale is None or self.scale == root.scale) and (
            self.dataset is None or self.dataset == root.dataset
        )


def _from_rules(
    root: LineageRoot, rules: Sequence[ClassificationRule]
) -> Classification:
    result = Classification.PREM_ONLY  # fail closed
    matched = [rule.gives for rule in rules if rule.matches(root)]
    if matched:
        result = matched[0]
        for other in matched[1:]:
            result = result.join(other)
    return result


def external_classification(
    source: ExternalSource,
    rules: Sequence[ClassificationRule],
) -> Classification:
    """Monotone precedence, which makes conflict impossible by construction:

      - a rule supplies the classification for any source it matches
      - the declared ExternalSource.classification may be MORE restrictive than a
        matching rule, freely and with no ceremony
      - LESS restrictive is not expressible here AT ALL. Declassification lives only
        at a pipeline's Publish.
      - nothing matches: fail closed

    This dissolves the "which source of truth wins" question rather than answering
    it.

    RULES KEY ON THE SOURCE'S SCALE, NEVER THE CONSUMING PIPELINE'S. building_n100
    reads N50 products and unscaled NVDB simultaneously. A rule "N10 is PREM_ONLY"
    applies to the N10 INPUT and forces the pipeline on-prem even though the pipeline
    produces N100. Evaluating against the pipeline's own scale would silently
    under-restrict.

    An over-broad rule carries an invisible cost: nothing errors, work simply runs
    on-prem forever and outputs inherit restrictions they never needed. Fail-closed
    is the right default, but check each rule against what is genuinely restricted
    rather than adopting it as a conservative guess.
    """
    from_rules = _from_rules(source, rules)
    if from_rules.permits(source.classification):
        return source.classification
    raise ValueError(
        f"{source!r} declares {source.classification.value} but rules require "
        f"{from_rules.value}. Declassification is only expressible at a pipeline's "
        "Publish, never on an ExternalSource. A mismatch is human error and requires "
        "human oversight - it is never auto-resolved."
    )


def classification_of(
    obj: DataObject,
    registry: StageRegistry,
    rules: Sequence[ClassificationRule],
    _memo: dict[int, Classification] | None = None,
) -> Classification:
    """The join over every root that reached the stage producing this object.

    Walks backward through stage wiring, NOT through `origin`. Context inputs count:
    if an operation reads a PREM_ONLY table to produce its output, that output is
    tainted - restricted data was read to make it.

    THREE CASES, and the middle one is the one the old model could not express:

      ExternalSource   rules joined with its declared legality.
      ProductIdentity  if some pipeline in this registry publishes it, the answer is
                       that stage's computation with the Publish's `reclassify_to`
                       applied - so a consumer reading a declassified product gets
                       CLOUD_OK rather than the producer's raw PREM_ONLY. If nobody
                       here publishes it, fall back to rules and fail closed: an
                       identity produced outside this project is data we did not
                       make and cannot reason about.
      Derived          the join over its producing stage's inputs.

    Fails closed on an object with no producer.

    Memoized by object IDENTITY, not by value. All three types are eq=False now, and
    keying on the object itself is what stops two distinct handles or objects that
    look alike from sharing an answer.
    """
    memo = {} if _memo is None else _memo
    key = id(obj)
    if key in memo:
        return memo[key]

    if isinstance(obj, ExternalSource):
        return external_classification(obj, rules)

    if isinstance(obj, ProductIdentity):
        stage = registry.identity_producer().get(obj)
        if stage is None:
            return _from_rules(obj, rules)
        memo[key] = Classification.PREM_ONLY  # cycle guard, conservative
        computed = Classification.CLOUD_OK
        for stage_input in stage.inputs:
            computed = computed.join(
                classification_of(stage_input.obj, registry, rules, memo)
            )
        publish = registry.publish_of().get(obj)
        if publish is not None and publish.reclassify_to is not None:
            computed = publish.reclassify_to
        memo[key] = computed
        return computed

    producer = registry.producer_of().get(obj)
    if producer is None:
        return Classification.PREM_ONLY  # nothing makes it: fail closed

    memo[key] = Classification.PREM_ONLY  # cycle guard, conservative
    result = Classification.CLOUD_OK
    for stage_input in producer.inputs:
        result = result.join(classification_of(stage_input.obj, registry, rules, memo))
    memo[key] = result
    return result


def publication_classification(
    obj: Derived,
    registry: StageRegistry,
    rules: Sequence[ClassificationRule],
) -> Classification:
    """What a published object's classification is AFTER any reclassification.

    Separate from classification_of so the computed value and the asserted value are
    both visible at the one point that matters - check_publications compares this
    against the destination the ProductIdentity declares.
    """
    computed = classification_of(obj, registry, rules)
    for pipeline in registry.pipelines.values():
        for publish in pipeline.publishes:
            if publish.obj is obj and publish.reclassify_to is not None:
                return publish.reclassify_to
    return computed


def pipeline_environment(pipeline: Pipeline) -> Environment:
    """Placement, decided ONCE PER PIPELINE and never mid-pipeline.

    Three reasons the pipeline is the right grain, the first decisive:

      1. It is where the storage model already switches. Pipeline-to-pipeline
         handoff goes through the archive anyway, so a cross-environment switch
         BETWEEN pipelines is free. A switch INSIDE one would break precisely the
         case run-scratch exists to serve - the next stage could not read the
         previous stage's scratch output.
      2. It is where classification is already declared, so both become one
         computation over one declaration.
      3. Per-stage placement would rarely differ anyway. Once a stage runs on-prem
         and writes Scality, every downstream stage is pinned on-prem.

    The cost of switching is not scheduling - creating a Job in the other cluster is
    one API call. The expense is that the DATA cannot follow.

    Covers ProductIdentity inputs as well as ExternalSource ones: reading an s3://
    published product forces on-prem for exactly the same reachability reason.
    """
    if any(root.location.startswith("s3://") for root in pipeline.external_inputs):
        return Environment.ON_PREM
    return Environment.ON_CLOUD
