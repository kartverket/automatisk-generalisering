"""The scratch manager over the in-memory `TableOps`: every workspace and the
loose-files directory created once, workspace names from the call identity and the pod
stem, the guards on calls and names, declared and internal handles, and the manifest.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from ag.adapters.fakes.memory.store import MemoryStore
from ag.adapters.fakes.memory.table_ops import MemoryTableOps
from ag.core.handles import ScratchHandle
from ag.core.types import DataType, PodRole
from ag.ports.errors import PortContractError
from ag.staging.errors import StagingError, WorkspaceError
from ag.staging.scratch import ScratchFileManager
from ag.staging.workspace import FORMAT, LAYER_SEPARATOR

STAGE = "n100/road/thin_roads"
"""A stage's qualified name, as T2.13 shapes it; opaque to the manager."""

CALLS = (f"{STAGE}:dissolve", f"{STAGE}:dissolve_2")
"""Call identities carrying the stage and the operation; the two separators the
rendering must keep out of a path."""


def manager(
    root: Path,
    *,
    calls: tuple[str, ...] = CALLS,
    role: PodRole = PodRole.POD,
    partition_index: int | None = 3,
    store: MemoryStore | None = None,
) -> ScratchFileManager:
    return ScratchFileManager(
        root=str(root),
        stage=STAGE,
        calls=calls,
        role=role,
        partition_index=partition_index,
        table=MemoryTableOps(store=store or MemoryStore()),
    )


def test_create_workspaces_creates_each_workspace_and_the_loose_files_directory(
    tmp_path: Path,
) -> None:
    store = MemoryStore()
    made = manager(tmp_path, store=store)
    made.create_workspaces()
    workspaces = (made.stage_workspace(), *(made.operation_workspace(c) for c in CALLS))
    assert len(set(workspaces)) == 3
    assert all(store.is_workspace(path) for path in workspaces)
    assert os.path.isdir(made.loose_files())
    assert made.loose_files() == made.stage_workspace().removesuffix(FORMAT.suffix)


def test_workspace_names_carry_the_rendered_identity_and_the_pod_stem(
    tmp_path: Path,
) -> None:
    made = manager(tmp_path)
    names = [os.path.basename(made.operation_workspace(c)) for c in CALLS]
    assert names == [
        f"n100_road_thin_roads_dissolve__pod00003{FORMAT.suffix}",
        f"n100_road_thin_roads_dissolve_2__pod00003{FORMAT.suffix}",
    ]
    assert os.path.basename(made.stage_workspace()) == (
        f"n100_road_thin_roads__pod00003{FORMAT.suffix}"
    )


def test_no_identity_separator_reaches_the_workspace_path(tmp_path: Path) -> None:
    root = tmp_path / "r"
    root.mkdir()
    made = manager(root)
    for call in CALLS:
        relative = os.path.relpath(made.operation_workspace(call), root)
        assert "/" not in relative and ":" not in relative


@pytest.mark.parametrize(
    ("role", "index", "stem"),
    [(PodRole.FAN_OUT, None, "fan_out"), (PodRole.FAN_IN, None, "fan_in")],
)
def test_a_pod_without_an_index_renders_its_role_alone(
    tmp_path: Path, role: PodRole, index: int | None, stem: str
) -> None:
    made = manager(tmp_path, role=role, partition_index=index)
    assert made.stage_workspace().endswith(f"__{stem}{FORMAT.suffix}")


@pytest.mark.parametrize(
    ("role", "index"), [(PodRole.POD, None), (PodRole.FAN_OUT, 1), (PodRole.FAN_IN, 0)]
)
def test_an_index_pairs_with_the_partition_role_only(
    tmp_path: Path, role: PodRole, index: int | None
) -> None:
    with pytest.raises(StagingError):
        manager(tmp_path, role=role, partition_index=index)


def test_an_unknown_call_is_refused(tmp_path: Path) -> None:
    made = manager(tmp_path)
    with pytest.raises(StagingError):
        made.operation_workspace(f"{STAGE}:other")
    with pytest.raises(StagingError):
        made.scope_for(f"{STAGE}:other")


def test_a_repeated_call_identity_is_refused(tmp_path: Path) -> None:
    with pytest.raises(StagingError):
        manager(tmp_path, calls=(CALLS[0], CALLS[0]))


def test_two_identities_rendering_alike_without_regard_to_case_are_refused(
    tmp_path: Path,
) -> None:
    with pytest.raises(WorkspaceError) as caught:
        manager(tmp_path, calls=(f"{STAGE}/Op", f"{STAGE}:op"))
    assert caught.value.context.handle is not None


def test_a_call_rendering_like_the_stage_is_refused(tmp_path: Path) -> None:
    """The stage and every call share one pod stem, so a call whose rendered identity
    equals the stage's would be the stage workspace."""
    with pytest.raises(WorkspaceError) as caught:
        manager(tmp_path, calls=(STAGE.replace("/", ":").upper(),))
    assert caught.value.context.handle == "N100_ROAD_THIN_ROADS"


def test_a_scope_is_bound_to_its_call_and_renders_the_trail(tmp_path: Path) -> None:
    made = manager(tmp_path)
    scope = made.scope_for(CALLS[0])
    assert scope.namespace == CALLS[0]
    scope.child("build")
    handle = scope.child("build").child("sub")("nodes", DataType.TABLE)
    assert handle.namespace == CALLS[0]
    expected = LAYER_SEPARATOR.join(("build_2", "sub", "nodes"))
    assert handle.path == f"{made.operation_workspace(CALLS[0])}/{expected}"
    assert made.manifest() == {handle.path: (CALLS[0], "build_2", "sub", "nodes")}


def test_the_same_leaf_in_two_calls_gives_two_unequal_handles(tmp_path: Path) -> None:
    made = manager(tmp_path)
    first = made.scope_for(CALLS[0])("x")
    second = made.scope_for(CALLS[1])("x")
    assert first != second
    assert first.path != second.path


def test_a_repeated_trail_and_leaf_in_one_call_raises(tmp_path: Path) -> None:
    scope = manager(tmp_path).scope_for(CALLS[0])
    scope("x")
    with pytest.raises(WorkspaceError):
        scope("x")


def test_a_leaf_differing_only_in_case_raises(tmp_path: Path) -> None:
    made = manager(tmp_path)
    scope = made.scope_for(CALLS[0])
    scope("Roads")
    with pytest.raises(WorkspaceError) as caught:
        scope("roads")
    assert caught.value.context.handle == f"{made.operation_workspace(CALLS[0])}/roads"


def test_a_leaf_over_the_layer_limit_raises_without_issuing(tmp_path: Path) -> None:
    made = manager(tmp_path)
    with pytest.raises(WorkspaceError):
        made.scope_for(CALLS[0])("x" * 161)
    assert made.manifest() == {}


def test_a_declared_handle_lives_in_the_stage_workspace_under_its_name(
    tmp_path: Path,
) -> None:
    made = manager(tmp_path)
    declared = ScratchHandle(name="roads", namespace="pkg.Handles")
    materialised = made.handle(declared)
    assert materialised == declared
    assert materialised.path == f"{made.stage_workspace()}/roads"
    assert made.handle(declared).path == materialised.path


def test_two_declared_handles_differing_only_in_case_are_refused(
    tmp_path: Path,
) -> None:
    made = manager(tmp_path)
    made.handle(ScratchHandle(name="Roads", namespace="pkg.Handles"))
    with pytest.raises(WorkspaceError):
        made.handle(ScratchHandle(name="roads", namespace="pkg.Handles"))
    with pytest.raises(WorkspaceError):
        made.handle(ScratchHandle(name="Roads", namespace="other.Handles"))


def test_a_taken_loose_files_directory_is_refused(tmp_path: Path) -> None:
    made = manager(tmp_path)
    os.makedirs(made.loose_files())
    with pytest.raises(FileExistsError):
        made.create_workspaces()


def test_a_second_create_is_the_ports_refusal(tmp_path: Path) -> None:
    made = manager(tmp_path)
    made.create_workspaces()
    with pytest.raises(PortContractError):
        made.create_workspaces()
