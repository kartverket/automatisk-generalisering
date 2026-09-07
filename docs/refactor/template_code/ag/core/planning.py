"""TEMPLATE — not shipped. Target module: `src/ag/core/planning.py`.

Planning: selection plus pinning, producing a RunPlan.

Everything in this module is PURE. No cluster, no credentials, no data, no arcpy.
That is the point: the entire planning layer is testable on a laptop, and CI runs
exactly the same code the orchestrator runs at startup.

The split between this module and execution.py is the most important structural
decision in the orchestrator. Plan is a function; execute is a loop.

Every path this module assigns comes from locations.py. Nothing here builds a string.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ag.core.types import (
    Classification,
    Environment,
    InputRole,
    Location,
    PipelineKey,
    RunId,
    StorageScope,
)
from ag.core.data_objects import DataObject, Derived
from ag.core.locations import StorageRoots
from ag.core.pipeline import Stage, StageRegistry


@dataclass(frozen=True)
class PinnedInput:
    """An input resolved to a concrete version at plan time.

    Pinning ONCE is what stops a publish landing mid-run from giving two stages
    different vintages of the same input. A pod never resolves anything - it
    receives the answer.
    """

    obj: DataObject
    location: Location
    role: InputRole


@dataclass(frozen=True)
class PlannedOutput:
    obj: Derived
    location: Location
    classification: Classification
    scope: StorageScope


@dataclass(frozen=True)
class PlannedStage:
    stage: Stage
    environment: Environment
    roots: StorageRoots
    inputs: tuple[PinnedInput, ...]
    outputs: tuple[PlannedOutput, ...]

    @property
    def job_name_prefix(self) -> str:
        """Job names MUST include scale, object and stage.

        The prototype uses f"{RUN_ID}-partitions" and deletes any Job of that name
        before creating, so stage 2 would delete stage 1's Job. That blocks
        sequencing more than one stage and should be fixed first.
        """
        s = self.stage
        return f"{s.scale}-{s.object_name}-{s.name}"


@dataclass(frozen=True)
class RunPlan:
    run_id: RunId
    stages: tuple[PlannedStage, ...]  # already in execution order
    environments: Mapping[PipelineKey, Environment]


def build_run_plan(
    request: object,  # RunRequest
    registry: StageRegistry,
    ranking: object,  # ScaleRanking
    rules: Sequence[object],  # ClassificationRule
) -> RunPlan:
    """THE SUBTLE PART, and the one most likely to be implemented wrong.

    If an object is produced by an EARLIER STAGE IN THIS SAME RUN, it pins to that
    stage's planned output location - NOT to whatever is currently in the archive.

        road_n100 runs and publishes N100_ROAD.
        building_n100 runs later in the same run and reads N100_ROAD.
        It must get THIS RUN's road output, not last week's.

    This is also what makes the ladder work at all: N10 -> N25 -> N50 -> N100 within
    one run is entirely this case. Get it wrong and the run silently generalizes
    from stale data - no error, just quietly wrong maps.
    """
    raise NotImplementedError(
        "1. errors = validate(registry, ranking, rules); abort on any ERROR\n"
        "2. selected = select_stages(request, registry)\n"
        "3. check_upstream_available(selected, registry)  -> errors, not expansion\n"
        "4. order  = topological_order(selected, ties by ranking.rank then\n"
        "            declaration order in the pipeline)\n"
        "5. per stage: environment from its pipeline (once per tag group), then\n"
        "   roots = StorageRoots.for_environment(environment)\n"
        "6. pin inputs: produced-in-this-run FIRST (locations.scratch_location or\n"
        "   locations.archive_location for a published one), archive SECOND\n"
        "   (locations.archive_location / locations.source_location)\n"
        "7. assign output locations: locations.scratch_location unless published,\n"
        "   in which case locations.archive_location, checked against\n"
        "   policy.classification_of and the Publish's reclassify_to"
    )


def downstream_closure(plan: RunPlan, invalidate_from: str) -> tuple[PlannedStage, ...]:
    """`run --invalidate-from <stage>` runs the downstream closure over the DECLARED
    GRAPH - not "that stage and everything after it in the list".

    DELIBERATELY NOT BUILT: fingerprint-based invalidation. A human forgetting is
    visible and recoverable; an incomplete fingerprint reporting a stale cache as
    valid is silent. The person who edited the operation is the person rerunning it.

    Invalidation and versioning are separable. Invalidation needs one bit. Keeping N
    historical copies is a different feature, addable later without changing this.
    """
    raise NotImplementedError
