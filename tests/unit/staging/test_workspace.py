"""The spellings and limits of `staging/workspace.py`: name legality at the two join
points, the trail renderer at the layer limit, identity rendering, the one bound on a
workspace name, and the arithmetic that makes it the only bound needed.
"""

from __future__ import annotations

import pytest

from ag.staging.errors import WorkspaceError
from ag.staging.workspace import (
    FORMAT,
    INTERNAL_FILE_NAME_LENGTH,
    LAYER_NAME_LIMIT,
    LAYER_SEPARATOR,
    LOOSE_FILE_NAME_ROOM,
    WINDOWS_FILE_PATH_LIMIT,
    WINDOWS_FOLDER_PATH_LIMIT,
    WINDOWS_ROOT_ALLOWANCE,
    WORKSPACE_NAME_BYTES,
    WORKSPACE_NAME_LIMIT,
    join,
    legal_name,
    loose_files_path,
    render_identity,
    render_trail,
    workspace_path,
)

ROOT = "/scratch"


@pytest.mark.parametrize("name", ["_x", "x1", "a__b", "Roads", "_"])
def test_legal_names_pass_unchanged(name: str) -> None:
    assert legal_name(name) == name


@pytest.mark.parametrize("name", ["2nd", "a-b", "aæ", "a.b", "a/b", "a:b", "", "a b"])
def test_illegal_names_are_refused_not_rewritten(name: str) -> None:
    with pytest.raises(WorkspaceError) as caught:
        legal_name(name)
    assert caught.value.context.handle == name


def test_join_checks_the_layer_name_and_spells_the_path() -> None:
    assert join("/scratch/s.gdb", "a") == "/scratch/s.gdb/a"
    with pytest.raises(WorkspaceError):
        join("/scratch/s.gdb", "2nd")


def test_render_trail_joins_with_the_separator() -> None:
    assert render_trail(("a", "b_2"), "leaf") == LAYER_SEPARATOR.join(
        ("a", "b_2", "leaf")
    )
    assert render_trail((), "leaf") == "leaf"


def test_render_trail_allows_the_limit_and_refuses_one_over() -> None:
    at_limit = "x" * LAYER_NAME_LIMIT
    assert render_trail((), at_limit) == at_limit
    with pytest.raises(WorkspaceError) as caught:
        render_trail((), at_limit + "x")
    assert str(LAYER_NAME_LIMIT) in str(caught.value)


def test_render_identity_replaces_every_separator_with_an_underscore() -> None:
    rendered = render_identity("pkg.mod:stage/op_2")
    assert rendered == "pkg_mod_stage_op_2"
    assert "/" not in rendered and ":" not in rendered and "." not in rendered


def test_workspace_path_adds_the_suffix_under_the_root() -> None:
    assert workspace_path(ROOT, "stem") == f"{ROOT}/stem{FORMAT.suffix}"


def test_workspace_path_checks_the_stem_for_legality() -> None:
    with pytest.raises(WorkspaceError):
        workspace_path(ROOT, "2nd")


def test_workspace_name_at_the_limit_passes_and_one_over_is_refused() -> None:
    stem = "w" * (WORKSPACE_NAME_LIMIT - len(FORMAT.suffix))
    assert workspace_path(ROOT, stem).endswith(stem + FORMAT.suffix)
    with pytest.raises(WorkspaceError) as caught:
        workspace_path(ROOT, stem + "w")
    assert str(WORKSPACE_NAME_LIMIT) in str(caught.value)


def test_loose_files_path_is_the_workspace_without_its_suffix() -> None:
    workspace = workspace_path(ROOT, "stem")
    assert loose_files_path(workspace) == f"{ROOT}/stem"


def test_the_workspace_bound_is_the_one_that_binds() -> None:
    """The file-path bound on a geodatabase's internal files is below the Windows folder
    bound and the Linux name bound, so the one check in `workspace_path` covers all
    three; a change to any constant that breaks this ordering must add the check it
    needs."""
    assert WORKSPACE_NAME_LIMIT == (
        WINDOWS_FILE_PATH_LIMIT - WINDOWS_ROOT_ALLOWANCE - 1 - INTERNAL_FILE_NAME_LENGTH
    )
    assert WORKSPACE_NAME_LIMIT <= WINDOWS_FOLDER_PATH_LIMIT - WINDOWS_ROOT_ALLOWANCE
    assert WORKSPACE_NAME_LIMIT <= WORKSPACE_NAME_BYTES
    longest_directory = WORKSPACE_NAME_LIMIT - len(FORMAT.suffix)
    assert (
        WINDOWS_ROOT_ALLOWANCE + longest_directory + 1 + LOOSE_FILE_NAME_ROOM
        == WINDOWS_FILE_PATH_LIMIT
    )
    assert LOOSE_FILE_NAME_ROOM > INTERNAL_FILE_NAME_LENGTH
