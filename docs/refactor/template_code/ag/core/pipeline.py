"""TEMPLATE — not shipped. Target module: `src/ag/core/pipeline.py`.

Stage, Pipeline, and the binding between the two IO vocabularies.

THE STAGE IS THE ONLY PLACE THE TWO VOCABULARIES MEET

    StageInput   a DataObject, the ScratchHandle it materializes into, and its role.
                 "Download this, put it there, and it is what we partition on."
    StageOutput  a Derived, and the ScratchHandle it is produced in.
                 "When the operations are done, upload what is here, as that."

Everything between those two declarations is ScratchHandles. An operation output that
no StageOutput names never leaves the pod - it has no identity, no location, and
nothing uploads it. That is not an optimisation to implement; it is what happens
when nobody declares it.

THE PIPELINE ASYMMETRY

A pipeline is (scale, object). REAL from a development perspective: it has
production timeline goals, someone carefully sequences it, and its parameters get
tuned. ABSENT at runtime: flatten() produces a stage registry and the pipeline stops
mattering. Scale and object survive as TAGS on each stage, used to scope a run and
to compute placement per tag group. Nothing walks a hierarchy.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ag.core.types import (
    Classification,
    InputRole,
    ObjectName,
    PipelineKey,
    Scale,
    StageName,
)
from ag.core.data_objects import DataObject, Derived, LineageRoot, ProductIdentity
from ag.core.operations import OperationCall, ScratchHandle


def _check_declared(handle: ScratchHandle, where: str) -> None:
    if not handle.namespace:
        raise TypeError(
            f"{where}: received an undeclared handle. handle() is only legal as a "
            "class attribute - outside a class body __set_name__ never fires, so "
            "the handle has no name and would render a path ending in a separator."
        )


@dataclass(frozen=True)
class StageInput:
    """One thing the stage downloads, and where it lands."""

    obj: DataObject
    handle: ScratchHandle
    role: InputRole
    """PROCESSING or CONTEXT. Consumed by FAN-OUT, never by an operation.

    Processing inputs are partitioned - split by extent, one subset per pod - and
    drive fan-in, where center-in features are kept and the rest discarded. Context
    inputs are selected within the stage's context_radius_m to inform the work, and
    are not carried into the output.

    A non-spatial lookup table is CONTEXT in the operative sense: replicated whole to
    every pod, not partitioned, not in the output. Fan-out writes it ONCE at a shared
    key rather than K times, which at K=50 is the difference between one transfer and
    fifty for identical bytes.
    """

    def __post_init__(self) -> None:
        _check_declared(self.handle, f"StageInput({self.obj!r})")


@dataclass(frozen=True)
class StageOutput:
    """One thing the stage uploads, and where it was produced.

    `obj` is a Derived and only a Derived. A stage produces new objects; promoting
    one to a published identity is a separate act, at the pipeline boundary, in a
    Publish.
    """

    obj: Derived
    handle: ScratchHandle

    def __post_init__(self) -> None:
        _check_declared(self.handle, f"StageOutput({self.obj!r})")


@dataclass(frozen=True)
class Stage:
    """The partitioned envelope, and the only thing the runtime schedules.

    Expands into three Kubernetes Jobs: fan-out, an Indexed Job of K partition pods,
    and fan-in. That triple is the cost that grouping operations amortizes.

    THE GROUPING CRITERION: a stage is the span between re-partitionings. Operations
    belong together when they prefer the same partition size. That is a judgement
    about data - you know when an operation changes the data enough that
    re-partitioning is needed - and it is NOT derivable from code.

    Operations run in LISTED ORDER. There is deliberately no intra-stage DAG: within
    one process in one workspace, a list is enough, and the author grouped them
    deliberately.

    Scale and object are TAGS, not workspaces. They are REPEATED on every stage
    rather than inherited from the Pipeline, which is accepted: it is two to nine
    call sites per pipeline, they are enum members so a typo does not compile, and
    the alternative - a Stage that cannot say what it is without being looked up in
    a Pipeline - makes every consumer of a bare Stage worse. A plan-time check
    confirms each Stage agrees with its Pipeline; it cannot be an import-time check
    because the Stage is constructed first.
    """

    name: StageName
    scale: Scale
    object_name: ObjectName
    handles: type
    """The handle class this stage's declarations must come from.

    `type`, not `type[Handles]`: naming is done by ScratchHandle.__set_name__ in any
    class body, and nothing should depend on the marker base.

    Declaring it is what makes CROSS-STAGE HANDLE LEAKAGE checkable. A
    ConflictResolution operation referencing `Network.merged` - the ordinary
    copy-paste - is otherwise undetectable statically: it type-checks, it is a
    perfectly good ScratchHandle, and it fails in the pod as a missing dataset after
    fan-out has already moved the data. See
    validation.check_stage_uses_own_handles.
    """

    inputs: tuple[StageInput, ...]
    outputs: tuple[StageOutput, ...]
    operations: tuple[OperationCall, ...]
    context_radius_m: float
    """The halo. A STAGE parameter, applied by fan-out, invisible to operations.

    It belongs here and not on an operation for two reasons. Fan-out builds one
    partition payload for the whole stage, so there is one radius to apply. And an
    operation must be unaware of partitioning entirely - an operation that knew its
    halo would be an operation that could behave differently near a partition edge,
    which is precisely what must never happen.

    THE REQUIREMENT IS TRANSITIVE. Not "covers features that affect mine" but
    "covers features that affect features that affect mine", for as many hops as the
    logic propagates. Displacement chains: displace A, A now conflicts with B,
    displacing B, which affects C. Required radius is search distance x propagation
    depth, and depth is data-dependent - dense urban extents chain further than
    sparse ones.

    It COMPOUNDS ACROSS THE OPERATIONS IN THIS STAGE, since each works on the last
    one's output. That is the cost side of grouping: more operations per stage means
    fewer round trips but a wider halo, and halo width costs context data in every
    pod. There is a crossover point and it is measurable rather than guessable.

    NOT DERIVABLE FROM CODE. Measured with the partition-invariance harness - run
    the stage at K=4 and K=16 and diff. Where the outputs differ, the halo is too
    small and the diff names the features. A radius tuned on a rural test extent can
    be correct there and silently wrong in Oslo, producing slightly-wrong geometry
    rather than an error.
    """

    @property
    def key(self) -> PipelineKey:
        return (self.scale, self.object_name)

    @property
    def qualified_name(self) -> str:
        return f"{self.scale}/{self.object_name}/{self.name}"

    def consumes(self) -> tuple[DataObject, ...]:
        return tuple(i.obj for i in self.inputs)

    def produces(self) -> tuple[Derived, ...]:
        return tuple(o.obj for o in self.outputs)

    def processing_inputs(self) -> tuple[StageInput, ...]:
        return tuple(i for i in self.inputs if i.role is InputRole.PROCESSING)

    def all_handles(self) -> tuple[ScratchHandle, ...]:
        """Every declared handle this stage touches, in declaration order."""
        return (
            tuple(i.handle for i in self.inputs)
            + tuple(o.handle for o in self.outputs)
            + tuple(h for call in self.operations for h in call.handles())
        )

    def __repr__(self) -> str:
        return f"Stage({self.qualified_name})"


@dataclass(frozen=True)
class Publish:
    """Promotes a derived object to a published identity, at the pipeline boundary.

    Publication policy is the one thing NOT derived - which outputs are products
    that external consumers depend on is a human decision.

    `identity` IS A SYMBOL, not a dataset string. That is what gives the product a
    location of its own, declared once in products.py, rather than having its
    destination written down by whichever pipeline happens to consume it. It also
    makes StageRegistry.identity_producer a lookup keyed on the object.

    THE ONE PLACE A HUMAN MAY ASSERT A PRODUCT IS LESS RESTRICTED than what produced
    it. Given that classification is computed over stage wiring (policy.py), and
    that wiring is deliberately conservative - every root reaching a stage taints
    everything it produces - this is the designed escape hatch. "The N100 product no
    longer reveals what made NVDB_Roads restricted" is a claim about content that a
    person can evaluate; the machine cannot.

    It takes effect at the moment of publication, which is physically the on-prem to
    cloud copy, so the guard fires at one discrete auditable point rather than being
    smeared across a run.

    Per output rather than per pipeline: a pipeline publishing a generalized product
    may also publish diagnostics that retained the detail, and a blanket
    reclassification would cover those silently.
    """

    obj: Derived
    identity: ProductIdentity
    reclassify_to: Classification | None = None


@dataclass(frozen=True)
class Pipeline:
    """(scale, object). A development artifact, not a runtime one.

    WHAT IT ACTUALLY OWNS, now that the DAG comes from stage IO:

      stages     the membership list. Needed because something has to enumerate
                 which stages exist - the alternative is scanning modules. It is
                 NOT an order; tuple position is only a tie-break.
      publishes  the only genuinely underivable thing here. Which outputs are
                 products external consumers depend on is a human decision, and it
                 is the one place reclassification may be asserted.

    WHAT IT DOES NOT OWN:

      external_inputs  a derived property, not a declaration. See below.
      order            derives from stage IO.
      legality         declared on the ExternalSource objects in sources.py, and
                       computed for everything else.
      locations        declared on ExternalSource and ProductIdentity, in the two
                       leaf modules.
    """

    scale: Scale
    object_name: ObjectName
    stages: tuple[Stage, ...]
    publishes: tuple[Publish, ...] = ()

    @property
    def key(self) -> PipelineKey:
        return (self.scale, self.object_name)

    @property
    def external_inputs(self) -> tuple[LineageRoot, ...]:
        """Every ExternalSource and ProductIdentity this pipeline's stages read.

        DERIVED, not declared. It used to be a hand-written tuple, which was a
        second artifact restating what the stages already say - exactly the pattern
        rejected for dependency edges, and with the same failure mode: add a stage
        input, forget the list, and placement is computed from stale data. Since
        placement is the ONLY consumer, a stale list means a pipeline silently
        scheduled in the wrong environment.

        It covers BOTH kinds of root, because both carry a location and placement is
        a reachability question. A pipeline reading an s3:// published product must
        run on-prem for exactly the same reason as one reading an s3:// external
        source.
        """
        seen: dict[int, LineageRoot] = {}
        for stage in self.stages:
            for stage_input in stage.inputs:
                if not isinstance(stage_input.obj, Derived):
                    seen.setdefault(id(stage_input.obj), stage_input.obj)
        return tuple(seen.values())


@dataclass(frozen=True)
class StageRegistry:
    """Every stage in the system, flat. This is what the runtime sees."""

    stages: tuple[Stage, ...]
    pipelines: Mapping[PipelineKey, Pipeline]

    def producer_of(self) -> Mapping[Derived, Stage]:
        """Which stage produces each derived object.

        The one-producer rule is what makes this a function rather than a relation,
        and it is a PRECONDITION for derivation rather than hygiene: two producers
        makes the edge ambiguous and derivation silently picks one.
        """
        producer: dict[Derived, Stage] = {}
        for stage in self.stages:
            for obj in stage.produces():
                producer.setdefault(obj, stage)
        return producer

    def published(self) -> frozenset[Derived]:
        return frozenset(
            publish.obj
            for pipeline in self.pipelines.values()
            for publish in pipeline.publishes
        )

    def identity_producer(self) -> Mapping[ProductIdentity, Stage]:
        """Which stage produces each PUBLISHED IDENTITY.

        THIS IS WHAT LINKS PIPELINES TOGETHER, and it is easy to miss.

        building_n100 reads N100_ROAD - from building's point of view it is external
        data with a location. road_n100 produces it as a `Derived` and promotes it
        with a Publish. Those are different objects, so matching on the Derived finds
        nothing and no edge appears.

        The link is the IDENTITY. Both sides now reference the same ProductIdentity
        symbol, so this is a plain lookup rather than the (scale, dataset) string
        match it used to be. Without it, road_n100 and building_n100 look independent
        and could be scheduled in either order - producing a building product
        displaced against last week's roads, with no error anywhere.

        A ProductIdentity that no pipeline here publishes simply has no entry, and
        consumers read its declared archive location. Which of the two applies is
        resolved at pin time - this run first, archive second.
        """
        producer: dict[ProductIdentity, Stage] = {}
        produced_by = self.producer_of()
        for pipeline in self.pipelines.values():
            for publish in pipeline.publishes:
                stage = produced_by.get(publish.obj)
                if stage is not None:
                    producer.setdefault(publish.identity, stage)
        return producer

    def publish_of(self) -> Mapping[ProductIdentity, Publish]:
        """The Publish that promotes each identity. Carries `reclassify_to`, which
        classification needs when one pipeline reads another's product."""
        return {
            publish.identity: publish
            for pipeline in self.pipelines.values()
            for publish in pipeline.publishes
        }

    def pipeline_of(self, stage: Stage) -> Pipeline:
        return self.pipelines[stage.key]


def flatten(pipelines: Sequence[Pipeline]) -> StageRegistry:
    """Where the pipeline stops existing."""
    return StageRegistry(
        stages=tuple(stage for pipeline in pipelines for stage in pipeline.stages),
        pipelines={pipeline.key: pipeline for pipeline in pipelines},
    )
