"""TEMPLATE — not shipped. Target module: `src/ag/orchestrator/execute.py`.

Execution: a loop, not a scheduler.

Everything in planning.py is pure and testable on a laptop. This is the only module
that needs a cluster - and it is deliberately small. No queueing, no backpressure,
no resource arbitration, no run-state persistence. Those are the genuinely hard
parts of a workflow engine and none are needed.

WHY WE WRITE THIS OURSELVES RATHER THAN USING ARGO WORKFLOWS

Not only because Argo Workflows is unavailable. Three reasons that hold either way:

  - Our DAG is DERIVED, not authored. Argo's central offering is declarative DAG
    execution; using it would mean compiling our derived graph into a Workflow spec,
    keeping all the derivation code and adding a translation layer.
  - Two clusters. A workflow controller schedules pods in its own cluster. We choose
    an environment per pipeline across two clusters, so we would need two installs
    plus a coordinator above them - which is this file.
  - We have declined resumability, which is the most expensive thing it would give.

What remains is the run UI. Real, but not design-shaping.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from ag.core.types import Environment, Location, RunId
from ag.core.locations import payload_location
from ag.core.planning import PlannedStage, RunPlan


def execute(plan: RunPlan, clusters: Mapping[Environment, object]) -> None:
    """`clusters` maps an environment to a Kubernetes client.

    The one place in this whole design where a Protocol genuinely pays: a fake
    client lets the executor's failure paths be tested without a cluster. Do NOT
    apply the pattern to the planner - configuration is data with many VALUES, not a
    capability with many IMPLEMENTATIONS, and a Protocol over it is a category
    error.

    FAILURE ABORTS THE RUN. No partial continuation, no sibling reconciliation. If
    the orchestrator itself dies, the run fails and a human reruns with
    --invalidate-from. Building resumability would mean state persistence,
    reconciliation and orphan cleanup - a controller - to avoid a manual step
    already accepted.

    ON CONCURRENCY. plan.stages is a valid sequential schedule, but the graph
    permits running independent stages at once. Two notes for whoever turns it on:

      - The in-place-mutation blocker does NOT apply across tag groups. The
        one-producer rule already guarantees no two pipelines write the same
        identity, and their intermediates live under different scratch prefixes.
        This is safe in a way concurrent stages WITHIN a pipeline currently are not.
      - The real gate is capacity. Each stage is already parallel across K partition
        pods, so if K saturates the cluster, concurrency buys contention rather than
        throughput.
    """
    for planned in plan.stages:
        run_stage(plan.run_id, planned, clusters[planned.environment])


def run_stage(run_id: RunId, planned: PlannedStage, cluster: object) -> None:
    """Three Kubernetes Jobs per stage - exactly the cost that grouping operations
    into a stage amortizes.

    1. FAN-OUT - one pod.
       Stages declared inputs down, partitions on the PROCESSING inputs, writes K
       payloads plus any shared context, and writes run metadata INCLUDING K.

    2. PARTITION - Job with completionMode: Indexed, completions=K, parallelism=P.
       Each pod reads JOB_COMPLETION_INDEX as its partition id, resolves its own
       payload from it, and runs the stage's operations IN LISTED ORDER against its
       own workspace with no transfer between them. The Job reaching `completions`
       IS the fan-in barrier - no separate synchronisation needed.

       An operation running here does not know it is in a pod, does not know the
       data is a partition, and does not know K. It sees ScratchHandles.

    3. FAN-IN - one pod.
       Collects K outputs, merges, discards non-center-in features, stages declared
       outputs up, writes run metadata.

    K FLOWS BACK UP by the orchestrator reading fan-out's metadata output. That is
    metadata, not data - consistent with the orchestrator never touching a feature
    class. It is the only value that flows upward.

    PARTITION PODS MUST BE IDEMPOTENT. Kubernetes retries failed pods
    (backoffLimit), and OOM on a dense partition is plausible. A retried pod must
    produce the same result as a fresh one, which holds as long as it reads only its
    own payload and writes only its own outputs. THIS REQUIRES ALL APPENDING TO
    HAPPEN IN FAN-IN - PartitionIterator currently appends incrementally as
    partitions complete, which double-appends under retry.

    POLL, DO NOT WATCH. read_namespaced_job on a ~2-minute interval. Polling is
    stateless and retries naturally across a dropped link; a watch is a long-lived
    connection that firewalls and proxies close without telling either end,
    surfacing as a run that hangs rather than one that errors. Stage transitions at
    2-minute granularity are irrelevant against hours of arcpy.

    CLEANUP. ownerReferences CANNOT CROSS CLUSTERS - an owner reference must point
    at an object in the same cluster. Remote-cluster Jobs need explicit cleanup by
    label selector, with ttlSecondsAfterFinished as a backstop. Note TTL only fires
    on completion, so it does not help with a Job orphaned by an orchestrator crash.
    """
    raise NotImplementedError


def partition_count_from_metadata(run_id: RunId, planned: PlannedStage) -> int:
    """Read K from fan-out's metadata object. Metadata only, never feature data."""
    raise NotImplementedError


def indexed_job_spec(
    run_id: RunId,
    planned: PlannedStage,
    partition_count: int,
    parallelism: int,
) -> object:
    """Build the Indexed Job.

    Known risks inherited from the WIP prototype, recorded so they are not repeated:

      - `/tmp` mounted as emptyDir(medium="Memory") is TMPFS, counted against pod
        memory. Every gdb, work file and arcpy intermediate consumes RAM. Combined
        with resources={} (no requests or limits) a partition pod eats node memory
        until something is evicted. Fine at PARTITION_COUNT=2 on test data; will not
        survive real partitions. Use node-backed disk, or set an explicit sizeLimit
        plus real memory limits.
      - readOnlyRootFilesystem=True means the workspace is the ONLY writable path.
        arcpy's scratch workspace, arcpy.env.workspace and TMPDIR/TEMP must all point
        there.
      - Scope the ServiceAccount before review: create/get/delete/watch on Jobs and
        read on pod logs, in ONE namespace. No cluster-admin. Cheap up front,
        awkward to retrofit.
    """
    raise NotImplementedError


def fan_out_payload_locations(
    run_id: RunId,
    planned: PlannedStage,
    partition_count: int,
) -> Sequence[Location]:
    """What fan-out writes, and what each worker independently recomputes.

    Every name comes from locations.payload_location - three call sites, one
    function, which is what stops a worker reading nothing or fan-in silently
    merging K-1 partitions.

    Note the shared-versus-per-partition distinction: an unpartitioned CONTEXT input
    is written ONCE and read by all K workers. Writing K copies of a lookup table
    costs K times the transfer for identical bytes - at K=50 that is the difference
    between one transfer and fifty.
    """
    raise NotImplementedError(
        "for each input: PROCESSING -> payload_location(...) per partition index; "
        "CONTEXT that is not partitioned -> one call with partition_index=None"
    )


__all__ = [
    "execute",
    "run_stage",
    "partition_count_from_metadata",
    "indexed_job_spec",
    "fan_out_payload_locations",
    "payload_location",
]
