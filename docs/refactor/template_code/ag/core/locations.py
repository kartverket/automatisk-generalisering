"""TEMPLATE — not shipped. Target module: `src/ag/core/locations.py`.

Every remote path in the system. One module, four functions.

WHY THIS EXISTS

staging.py's own argument for centralizing payload naming - three components
independently computing the same name will drift, and the failure is a worker
reading nothing or fan-in silently merging K-1 partitions - applies to all of it.
Before this module there were three builders in two modules
(`planning.scratch_location`, `staging.scratch_dump_location`, `staging.payload_key`)
and a fourth, the archive location, that had no home at all.

They also shared an unnamed dependency. Two of them returned a bucketless
`run-scratch/...` while `Location` is documented as `gs://bucket/path`, so something
unwritten applied the environment prefix. `scratch_dump_location` carried the safety
argument for that prefixing in its docstring; `scratch_location` needed the same
argument and did not state it. One module, one `StorageRoots`, one place to get it
wrong.

THE SAFETY ARGUMENT, STATED ONCE FOR ALL RUN-SCOPED PATHS

    Running in cloud requires no s3:// external inputs. PREM_ONLY data lives on
    s3://. So cloud placement implies nothing restricted was read, which implies all
    run-scoped data is CLOUD_OK.

Writing run-scoped data to the runtime environment's own storage is therefore always
equally or MORE restrictive than the data requires, never less. That covers payloads,
stage outputs and scratch dumps alike - the dump is the sharpest case, because it
contains MORE detail than the published product, including intermediates that still
had whatever sensitivity generalization later removed.

THIS HOLDS ONLY WHILE "PREM_ONLY implies stored on-prem" HOLDS. If anyone ever
allows a PREM_ONLY dataset to sit on gs://, this reasoning collapses for every
function below at once.

ARCHIVE IS THE EXCEPTION and does not take roots. A published product's location is
declared on its ProductIdentity in products.py, because it outlives the run and is
read by pipelines that know nothing about the run that made it.
"""

from __future__ import annotations

from dataclasses import dataclass

from ag.core.types import Environment, Location, RunId
from ag.core.data_objects import Derived, LineageRoot, ProductIdentity
from ag.core.pipeline import Stage


@dataclass(frozen=True)
class StorageRoots:
    """The per-environment prefixes every run-scoped path is built on.

    Deployment configuration, resolved once at orchestrator startup and carried on
    the RunPlan. A pod receives the finished Location, never these.
    """

    payloads: Location
    run_scratch: Location

    @staticmethod
    def for_environment(environment: Environment) -> StorageRoots:
        """The one place environment becomes a bucket."""
        if environment is Environment.ON_PREM:
            return StorageRoots(
                payloads="s3://kv-run-prem/payloads",
                run_scratch="s3://kv-run-prem/run-scratch",
            )
        return StorageRoots(
            payloads="gs://kv-run-cloud/payloads",
            run_scratch="gs://kv-run-cloud/run-scratch",
        )


def archive_location(identity: ProductIdentity) -> Location:
    """Where a published product lives. Declared, not computed.

    Here only so that all four location questions have one module to look in - the
    body is deliberately trivial, and the fact that it is trivial is the point:
    a published identity's location is a declaration in products.py, and nothing
    derives it from a run.
    """
    return identity.location


def source_location(root: LineageRoot) -> Location:
    """Where an external input is read from. Also declared, also trivial, also here
    so nobody goes looking for it anywhere else."""
    return root.location


def scratch_location(
    roots: StorageRoots, run_id: RunId, stage: Stage, obj: Derived
) -> Location:
    """Where an unpublished stage output goes. Derived mechanically.

    Keyed by the PRODUCING STAGE, not by the object's origin. SELECTED_ROADS has
    ADMIN_AREAS in its origin and still lands under n100/road/selection/ - origin
    drives identity and lineage and plays no part in placement.

    Giving intermediates registry entries would recreate the 187-entry
    file_manager_buildings.py problem in new clothes. The Derived does not know its
    stage, which is what makes regrouping operations across stages a free edit.

    RETENTION ON THIS PREFIX IS THE RESUME WINDOW: you can only resume from stage N
    if stage N-1's output still exists. Beyond it, rerun from the last archived
    boundary. That is a lifecycle policy, not a feature.

    There is no equivalent for operation-to-operation objects inside a stage - those
    live in the pod's workspace and never get a URI at all.
    """
    return (
        f"{roots.run_scratch}/{run_id}/{stage.scale}/{stage.object_name}/"
        f"{stage.name}/{obj.name}"
    )


def payload_location(
    roots: StorageRoots,
    run_id: RunId,
    stage: Stage,
    obj: object,
    partition_index: int | None,
) -> Location:
    """Where a partition payload lives between fan-out, a worker, and fan-in.

    Called by fan-out when writing, by each worker when reading its own, and by
    fan-in when collecting. Three call sites, one function - that is the point.

    TWO SHAPES, and the distinction is worth real money:

      per-partition  the processing data for one partition. K distinct objects.
      shared         a context input that is not partitioned - a lookup table, or
                     anything replicated to every pod. ONE object all K workers read.
                     `partition_index=None`.

    Writing K copies of an unpartitioned context input costs K times the transfer for
    identical bytes. At K=50 with a few hundred MB of context that is the difference
    between one transfer and fifty. Fan-out already knows which is which, because the
    input's role is declared.
    """
    name = obj.name if isinstance(obj, Derived) else _dataset_of(obj)
    base = f"{roots.payloads}/{run_id}/{stage.scale}/{stage.object_name}/{stage.name}"
    if partition_index is None:
        return f"{base}/shared/{name}"
    return f"{base}/part-{partition_index:05d}/{name}"


def scratch_dump_location(
    roots: StorageRoots, run_id: RunId, stage: Stage, pod_prefix: str
) -> Location:
    """Where a pod's whole workspace goes when the dump policy is on.

    Keep per-pod workspaces separate rather than merging them: knowing WHICH
    PARTITION misbehaved is most of the diagnostic value.
    """
    return (
        f"{roots.run_scratch}/{run_id}/{stage.scale}/{stage.object_name}/"
        f"{stage.name}/_scratch/{pod_prefix}"
    )


def _dataset_of(obj: object) -> str:
    dataset = getattr(obj, "dataset", None)
    if not isinstance(dataset, str):
        raise TypeError(f"cannot build a payload name for {obj!r}")
    return dataset
