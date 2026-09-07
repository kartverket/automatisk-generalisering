"""TEMPLATE — not shipped. Target module: `src/ag/staging/scratch.py`.

The ScratchFileManager: every path inside the pod scratch root, and nothing else.

LOCAL PATHS HERE, REMOTE PATHS IN `ag.core.locations`. This module owns workspace
paths, layer names and the trail budget. Every remote path — payloads, stage outputs,
scratch dumps, the archive — is built in one place for the reason this module's own
argument gives: fan-out writes partition i's payload where worker i will look, and
worker i writes its output where fan-in will look, so three components independently
compute the same name. Split across modules it drifts, and the failure is a worker
reading nothing, or fan-in silently merging K-1 partitions and reporting success.

The format itself is `ag.staging.workspace`: this module asks how to spell a path, it
does not know whether the answer is a `.gdb`, a `.gpkg` or a directory.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum

from ag.core.operations import ScratchHandle, ScratchScope
from ag.core.pipeline import Stage
from ag.core.types import DataType
from ag.staging.workspace import (
    WorkspaceFormat,
    join,
    name_budget,
    render_trail,
    sidecar,
    workspace_path,
)

__all__ = ["Tier", "ScratchFileManager", "sidecar"]


class Tier(Enum):
    """Which pod is running. Constructor context for the ScratchFileManager."""

    FAN_OUT = "fan_out"
    PARTITION = "part"
    FAN_IN = "fan_in"


# ---------------------------------------------------------------------------
# The manager
# ---------------------------------------------------------------------------


@dataclass
class ScratchFileManager:
    """Owns every path in the pod's ephemeral workspace. Nothing else.

    One imprecision in the name, accepted knowingly: a materialized stage input is
    not really scratch, it is the actual data. But from the pod's point of view
    everything local is ephemeral, and "scratch" aligns with vocabulary a developer
    already knows from arcpy.env.scratchWorkspace.

    TWO WORKSPACE TIERS:

      stage workspace      every DECLARED handle: stage inputs, inter-operation
                           handles, stage outputs. Names are just the handle name,
                           NO TRAIL, because they are class attributes of the
                           stage's Handles class and two attributes in one class
                           body cannot collide. Operation B must be able to read
                           what operation A wrote, so these cannot live in a
                           per-operation workspace.

      operation workspace  internal scratch created via a ScratchScope. Names carry
                           the trail below the operation.

    Putting the operation name in the WORKSPACE rather than the layer name buys back
    one level of trail budget - free on Linux, cheap on Windows - and organizes the
    scratch dump for free.

    Each workspace has a SIBLING DIRECTORY for files a gdb cannot hold - .lyrx,
    .csv, logs, .prj:

        /tmp/n100_road_network_part00003.gdb/            layers
        /tmp/n100_road_network_part00003/                loose files

    Removed from the current implementation: `_modify_path` and its \\w+\\d0 regex
    scrape of the scale segment (work file paths carry no scale and no project
    layout - that regex exists only because work file location was derived from a
    durable file's location), and `_session_prefix` from datetime.now() at import.

    NO TIMESTAMPS. The pod's workspace starts empty and dies with the pod, so there
    is nothing to collide with. The session prefix exists in the current code
    precisely because the old system shared a disk across runs - that reason is gone.
    Determinism buys something concrete: the same failure produces the same path
    every time, and two runs' file listings can be diffed. Run isolation lives in the
    run_id in the REMOTE path, where it is actually needed.
    """

    root: str
    stage: Stage
    tier: Tier
    partition_index: int | None = None
    fmt: WorkspaceFormat = WorkspaceFormat.FILE_GDB
    windows: bool = False

    _issued: dict[str, tuple[str, ...]] = field(default_factory=dict, repr=False)
    """rendered layer name -> full trail. The manifest, and the leaf-collision check."""

    # -- naming ------------------------------------------------------------

    def prefix(self) -> str:
        """n100_road_network_part00003

        No `.lower()`: Scale and ObjectName are StrEnums whose values are already
        the lowercase path segments, so there is nothing to normalize and nothing
        that changes if one path builder forgets to.
        """
        stage = self.stage
        parts = [stage.scale, stage.object_name, stage.name]
        if self.tier is Tier.PARTITION and self.partition_index is not None:
            parts.append(f"{Tier.PARTITION.value}{self.partition_index:05d}")
        else:
            parts.append(self.tier.value)
        return "_".join(parts)

    def stage_workspace(self) -> str:
        return self._workspace(self.prefix())

    def operation_workspace(self, operation: str) -> str:
        return self._workspace(f"{self.prefix()}__{operation}")

    def _workspace(self, stem: str) -> str:
        return workspace_path(self.root, stem, self.fmt)

    def _join(self, workspace: str, layer: str, data_type: DataType) -> str:
        return join(workspace, layer, data_type, self.fmt)

    # -- declared handles --------------------------------------------------

    def handle(self, declared: ScratchHandle) -> ScratchHandle:
        """Materialize a DECLARED handle into the stage workspace.

        No trail: the name comes from a class attribute, so it is already unique
        within the stage by construction - see operations.Handles. Keeping declared
        names short is what stops the long trails from ever applying to the IO
        flowing between operations.
        """
        workspace = self.stage_workspace()
        return declared.materialize(
            self._join(workspace, declared.name, declared.data_type)
        )

    # -- internal scratch --------------------------------------------------

    def scope_for(self, operation: str) -> ScratchScope:
        """The root scope handed to one operation. Its trail starts empty, because
        the operation name is already in its workspace."""

        def materialize(
            trail: tuple[str, ...], leaf: str, data_type: DataType
        ) -> ScratchHandle:
            workspace = self.operation_workspace(operation)
            budget = name_budget(workspace, self.windows)
            layer = render_trail(trail, leaf, budget)
            previous = self._issued.get(layer)
            if previous is not None:
                raise ValueError(
                    f"scratch name {layer!r} was already issued in this pod. A "
                    "repeated leaf name within one scope is a genuine mistake, not "
                    "a legitimate repeat - use scratch.child(...) if two tools need "
                    "the same leaf name, which auto-indexes."
                )
            self._issued[layer] = (operation, *trail, leaf)
            return ScratchHandle(name=layer, data_type=data_type).materialize(
                self._join(workspace, layer, data_type)
            )

        return ScratchScope(trail=(), materialize=materialize)

    def manifest(self) -> Mapping[str, tuple[str, ...]]:
        """rendered name -> full trail.

        Written into the workspace and shipped with the scratch dump, so a trail that
        gets elided later is always recoverable. This is what makes the
        first-two + hash + last-two strategy strictly better than plain hashing.
        """
        return dict(self._issued)

    def create_workspaces(self) -> None:
        raise NotImplementedError(
            "CreateFileGDB for the stage workspace and one per operation, plus "
            "makedirs for each sidecar. Three or four per pod, not forty - which is "
            "why workspace-per-operation is affordable."
        )
