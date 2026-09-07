"""TEMPLATE — not shipped. Target module: `src/ag/staging/transfer.py`.

Getting bytes in and out of the pod, and the scratch dump.

WHAT THIS REPLACES. The old FileManager was to resolve declared IO to a location and a
client, materialize inputs, publish outputs, and assert residency. Resolution now
happens at PLAN time, so a pod never receives declarations — it receives PinnedInputs
with the answer in them. What is left is transfer.

SUBSTRATE IS NOT MODEL. Everything above this module is substrate-independent. This is
the only place that knows whether a scope is backed by object storage or a shared
filesystem.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from ag.core.locations import StorageRoots, scratch_dump_location
from ag.core.data_objects import DataObject
from ag.core.operations import ScratchHandle
from ag.core.types import Location, RunId, StorageScope
from ag.staging.scratch import ScratchFileManager

# ---------------------------------------------------------------------------
# Substrate
#
# INTRA_STAGE and RUN_SCRATCH are object storage today. If the platform can offer a
# ReadWriteMany volume (NFS) reachable by every pod in a stage, both can move there:
#
#   - NO PACK/UNPACK. A .gdb is a DIRECTORY TREE. Putting one in object storage means
#     archiving it to a single object and unarchiving on the other side, with all
#     arcpy handles released first or the archive captures .lock files and unflushed
#     state. On a shared filesystem the directory is simply there. Probably the
#     biggest single win - CPU, wall clock, and a class of bugs.
#   - Transfer volume collapses: ~2K transfers per stage becomes ~0.
#
# Recommended shape if NFS arrives: NFS as TRANSPORT, /tmp as WORKING storage. A
# worker copies its partition directory from NFS to local disk (a plain copy, no
# untar), runs every operation locally at full speed, copies the output back. That
# keeps the no-pack win and sidesteps the arcpy-on-NFS performance question, because
# arcpy never touches NFS.
#
# Open before relying on it: arcpy on NFS with tens of concurrent clients; NFS server
# throughput ceiling versus horizontally-scaling object storage; fixed PVC capacity
# versus an unbounded bucket (run-scratch retention IS the resume window); one export
# per environment, since a PREM_ONLY intermediate cannot sit on a cloud-side share.
# ---------------------------------------------------------------------------

SUBSTRATE: Mapping[StorageScope, str] = {
    StorageScope.POD_LOCAL: "tmp",
    StorageScope.INTRA_STAGE: "object_storage",  # or "nfs"
    StorageScope.RUN_SCRATCH: "object_storage",  # or "nfs"
    StorageScope.ARCHIVE: "object_storage",  # always
}


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------


class ArchiveClient(Protocol):
    """Transport. Given a location, get bytes down or push bytes up.

    A Protocol rather than an ABC, in order of weight: dependency direction (with an
    ABC the adapter must import and inherit the port; with a Protocol nothing imports
    anything and adapters satisfy it structurally); ports stay narrow, which is why
    the WIP's interface.py declares six methods when only two are called anywhere;
    third-party clients and plain test doubles can satisfy it without a wrapper; and
    trivial fakes.

    Tradeoffs: no shared implementation, and no runtime enforcement -
    @runtime_checkable plus isinstance checks method NAMES only, not signatures.

    Ship it with two methods until a third has a caller.
    """

    def read(self, location: Location, into: ScratchHandle) -> ScratchHandle: ...

    def write(self, source: ScratchHandle, location: Location) -> None: ...


def stage_down(
    inputs: Sequence[object],  # PinnedInput
    sfm: ScratchFileManager,
    clients: Mapping[str, ArchiveClient],
) -> Mapping[DataObject, ScratchHandle]:
    """Materialize pinned inputs into the stage workspace.

    `clients` is keyed by URI scheme. Several clients in one pod is expected, not
    exceptional: an on-prem pipeline routinely reads gs:// published products
    alongside s3:// restricted sources.

    Geodatabases are directories. Release all arcpy handles - clear
    arcpy.env.workspace, delete layers - before packing or unpacking, or the archive
    captures .lock files and possibly unflushed state. On an NFS substrate this step
    largely disappears.
    """
    raise NotImplementedError


def stage_up(
    outputs: Mapping[DataObject, ScratchHandle],
    planned: Sequence[object],  # PlannedOutput
    clients: Mapping[str, ArchiveClient],
) -> None:
    """Assert classification, then upload. The backstop for the plan-time check."""
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Scratch dump
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScratchDumpPolicy:
    """Whether the pod's whole workspace is preserved for debugging.

    A job parameter. Total run-scratch is 0.5-3 GB globally and each dump is far
    smaller, so the cost of always having the trail is trivial against one afternoon
    of not having it - `enabled` defaults True.

    The dump ships the manifest alongside, so an elided trail stays readable, and it
    shares a prefix with the fan-out/fan-in run metadata so one download gets counts,
    timings, drift AND the features they describe.
    """

    enabled: bool = True
    on_failure_only: bool = False


def dump_scratch(
    run_id: RunId,
    roots: StorageRoots,
    sfm: ScratchFileManager,
    policy: ScratchDumpPolicy,
    failed: bool,
    clients: Mapping[str, ArchiveClient],
) -> None:
    """Called by every pod tier at exit - fan-out, each worker, and fan-in.

    The destination comes from locations.scratch_dump_location, which carries the
    argument for why writing run-scoped data to the runtime environment's own
    storage is always equally or more restrictive than the data requires. The dump
    is the sharpest case for that argument, because it contains MORE detail than the
    published product.

    Note the gap in `on_failure_only`: a stage that SUCCEEDS and produces wrong data
    is exactly when the trail is most wanted and least expected. That is why the
    default is on rather than on-failure.
    """
    destination: Location = scratch_dump_location(
        roots, run_id, sfm.stage, sfm.prefix()
    )
    raise NotImplementedError(
        "if not policy.enabled: return; if policy.on_failure_only and not failed: "
        "return; write sfm.manifest() into the workspace, then upload every "
        f"workspace and sidecar under {destination}"
    )
