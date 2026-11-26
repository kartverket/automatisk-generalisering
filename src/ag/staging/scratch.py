"""The scratch manager: every path inside the pod scratch root, and nothing else.

What: `ScratchFileManager` names the stage workspace, one operation workspace per call
and the loose-files directory; materialises a declared handle into the stage workspace
and binds one `ScratchScope` per call; creates the workspaces through
`TableOps.create_workspace` and the directory itself; and keeps the manifest, every
internal path it issued against the call, trail and leaf it stands for.

How: a workspace stem is the rendered stage, or the rendered call identity, followed by
the pod stem, the role's value with the partition index on a partition pod, so a dump
sorts by stage and call and two pods' workspaces never share a name. With the stage
`n100/road/thin_roads` and the calls `dissolve` and `dissolve_2` on partition pod 3:

    n100_road_thin_roads__pod00003.gdb             declared handles
    n100_road_thin_roads__pod00003/                loose files
    n100_road_thin_roads_dissolve__pod00003.gdb    internal scratch of one call
    n100_road_thin_roads_dissolve_2__pod00003.gdb  the second call of the same operation

The stage and the call identities are opaque strings: `Stage` computes the identities
(A29) and the manager only renders them, refusing a call it was not given and any two of
the stage and the calls whose rendered names agree without regard to case. Every path
the manager issues enters a map keyed on the casefolded path, because the engine treats
two names that differ only in case as one and, with overwrite on, the second silently
replaces the first (A34): a repeated (trail, leaf) in one call raises, a declared handle
whose name is case-equal to another's raises, and the same declared handle asked twice
gets the same path. Every path is settled in the constructor, so a bad name fails before
anything is created. No timestamps: the root starts empty and dies with the pod, and a
deterministic path is one that two runs' listings can be diffed on.

Why: the call sits in the workspace and not in the layer name, so a trail keeps the
whole layer-name budget. The manager holds the paths and `workspace.py` the spellings,
so no caller learns the format. Creation goes through the toolbox's `TableOps`, so
staging imports no engine (A5.7, import row 9); the loose-files directory is an ordinary
directory, `os.makedirs` makes it, and `FileExistsError` refuses a taken path as the
port refuses a taken workspace path. ADR-0021 ST-D26 names the role segments; B37 asks
what a stage's identity is.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ag.core.errors import ErrorContext
from ag.core.handles import ScratchHandle, ScratchScope
from ag.core.types import DataType, PodRole
from ag.ports.table_ops import TableOps
from ag.staging.errors import StagingError, WorkspaceError
from ag.staging.workspace import (
    FORMAT,
    join,
    loose_files_path,
    render_identity,
    render_trail,
    workspace_path,
)

STEM_SEPARATOR = "__"
"""Between the rendered identity and the pod stem in a workspace name. Two underscores
so the pod stem reads apart from the identity, whose own separators render as one."""

PARTITION_INDEX_DIGITS = 5
"""Width of the partition index in a pod stem, zero-padded so pods sort by index."""


@dataclass(frozen=True, slots=True, kw_only=True)
class _Issued:
    """One internal path and what it stands for: the call identity, the trail and the
    leaf."""

    path: str
    trail: tuple[str, ...]


class ScratchFileManager:
    """Owns every path in the pod's scratch root. See the module docstring."""

    def __init__(
        self,
        *,
        root: str,
        stage: str,
        calls: Sequence[str],
        role: PodRole,
        partition_index: int | None = None,
        table: TableOps,
    ) -> None:
        if (partition_index is None) == (role is PodRole.POD):
            raise StagingError(
                f"role {role.value!r} with partition index {partition_index!r}: only a "
                f"{PodRole.POD.value!r} pod has an index, and every one does."
            )
        self._table = table
        pod = _pod_stem(role, partition_index)
        self._stage_workspace = workspace_path(
            root, f"{render_identity(stage)}{STEM_SEPARATOR}{pod}"
        )
        self._workspaces = {
            call: workspace_path(root, f"{stem}{STEM_SEPARATOR}{pod}")
            for call, stem in _render_calls(calls, stage=stage).items()
        }
        self._issued: dict[str, _Issued] = {}
        self._declared: dict[str, ScratchHandle] = {}

    @property
    def calls(self) -> tuple[str, ...]:
        """The call identities this pod runs, in declaration order."""
        return tuple(self._workspaces)

    def stage_workspace(self) -> str:
        """The workspace every declared handle lives in."""
        return self._stage_workspace

    def operation_workspace(self, call: str) -> str:
        """The workspace holding the internal scratch of `call`."""
        workspace = self._workspaces.get(call)
        if workspace is None:
            raise StagingError(
                f"call identity {call!r} is not one this pod runs: {self.calls!r}."
            )
        return workspace

    def loose_files(self) -> str:
        """The directory for files a geodatabase cannot hold, beside the stage
        workspace."""
        return loose_files_path(self._stage_workspace)

    def handle(self, declared: ScratchHandle) -> ScratchHandle:
        """`declared` materialised into the stage workspace under its own name, no
        trail: the name is a class attribute and unique in the stage by construction.
        A second handle whose name is case-equal is refused; the same handle again gets
        the same path."""
        path = join(self._stage_workspace, declared.name)
        key = path.casefold()
        before = self._declared.setdefault(key, declared)
        if before != declared:
            raise WorkspaceError(
                f"{declared!r} would be at {path!r}, which {before!r} already holds "
                "without regard to case; the engine treats the two names as one.",
                context=ErrorContext(handle=path),
            )
        return declared.materialize(path)

    def scope_for(self, call: str) -> ScratchScope:
        """The root scope handed to `call`: its trail starts empty, since the call is
        already in its workspace, and its namespace is the call identity."""
        workspace = self.operation_workspace(call)

        def materialize(trail: tuple[str, ...], leaf: str, data_type: DataType) -> str:
            path = join(workspace, render_trail(trail, leaf))
            key = path.casefold()
            before = self._issued.get(key)
            if before is not None:
                raise WorkspaceError(
                    f"scratch path {path!r} was already issued in this pod for "
                    f"{before.trail!r}; a repeated leaf within one scope is a mistake, "
                    "and the engine treats two names differing only in case as one. "
                    "Use scratch.child(...) where two tools need the same leaf.",
                    context=ErrorContext(handle=path),
                )
            self._issued[key] = _Issued(path=path, trail=(call, *trail, leaf))
            return path

        return ScratchScope(namespace=call, trail=(), materialize=materialize)

    def manifest(self) -> Mapping[str, tuple[str, ...]]:
        """Every internal path issued, against (call identity, *trail, leaf). Shipped
        with the scratch dump so a rendered name is always readable back."""
        return {issued.path: issued.trail for issued in self._issued.values()}

    def create_workspaces(self) -> None:
        """Creates the stage workspace, one workspace per call and the loose-files
        directory, each once; a taken path is the port's or the filesystem's refusal."""
        self._table.create_workspace(path=self._stage_workspace, fmt=FORMAT)
        for workspace in self._workspaces.values():
            self._table.create_workspace(path=workspace, fmt=FORMAT)
        os.makedirs(self.loose_files())


def _pod_stem(role: PodRole, partition_index: int | None, /) -> str:
    """The role's value, with the partition index zero-padded on a partition pod."""
    if partition_index is None:
        return role.value
    return f"{role.value}{partition_index:0{PARTITION_INDEX_DIGITS}d}"


def _render_calls(calls: Sequence[str], *, stage: str) -> dict[str, str]:
    """Each call identity against its rendered stem. A repeated identity is refused, and
    so is a stem that agrees, without regard to case, with another call's or with the
    stage's: the stage and every call share one pod stem, so equal stems would be one
    workspace."""
    stems: dict[str, str] = {}
    seen: dict[str, str] = {render_identity(stage).casefold(): stage}
    for call in calls:
        if call in stems:
            raise StagingError(f"call identity {call!r} is given twice.")
        stem = render_identity(call)
        other = seen.setdefault(stem.casefold(), call)
        if other != call:
            raise WorkspaceError(
                f"identities {other!r} and {call!r} both render to the workspace name "
                f"{stem!r} without regard to case.",
                context=ErrorContext(handle=stem),
            )
        stems[call] = stem
    return stems
