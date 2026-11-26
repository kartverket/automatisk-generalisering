"""The spellings and limits of `staging/workspace.py`: name legality at the two join
points, the trail renderer at the layer limit, identity rendering, the one bound on a
workspace name, and the arithmetic that makes it the only bound needed.
"""

from __future__ import annotations

import pytest

from ag.staging.errors import WorkspaceError
from ag.staging.workspace import (
    DIGEST_LENGTH,
    DIGEST_MARK,
    DIGEST_WINDOWS,
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
    full_name,
    join,
    legal_name,
    loose_files_path,
    name_digest,
    render_identity,
    render_trail,
    workspace_path,
)

ROOT = "/scratch"
SEP = LAYER_SEPARATOR
OVER = ("first", "x" * 70, "y" * 70, "tail")
"""A trail whose full name with the leaf `leaf` is 161 characters: one over the limit."""


def mark(trail: tuple[str, ...], leaf: str, *, window: int = 0) -> str:
    start = window * DIGEST_LENGTH
    return (
        DIGEST_MARK + name_digest(full_name(trail, leaf))[start : start + DIGEST_LENGTH]
    )


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


def test_a_name_at_the_limit_is_unchanged_and_one_over_is_shortened() -> None:
    trail = ("a" * 50, "b" * 50)
    leaf = "c" * (LAYER_NAME_LIMIT - 100 - 2 * len(SEP))
    assert len(full_name(trail, leaf)) == LAYER_NAME_LIMIT
    assert render_trail(trail, leaf) == full_name(trail, leaf)
    shortened = render_trail(trail, leaf + "c")
    assert len(shortened) <= LAYER_NAME_LIMIT
    assert shortened != full_name(trail, leaf + "c")


def test_a_shortened_name_keeps_the_leaf_the_tail_and_the_first_label() -> None:
    assert len(full_name(OVER, "leaf")) == LAYER_NAME_LIMIT + 1
    shortened = render_trail(OVER, "leaf")
    assert shortened == SEP.join(
        ("first", mark(OVER, "leaf"), "y" * 70, "tail", "leaf")
    )
    assert len(shortened) <= LAYER_NAME_LIMIT


def test_the_first_label_is_dropped_when_it_does_not_fit() -> None:
    trail = ("f" * 70, "x" * 70, "y" * 70)
    shortened = render_trail(trail, "leaf")
    assert shortened == SEP.join((mark(trail, "leaf"), "y" * 70, "leaf"))


def test_names_differing_only_in_case_shorten_alike() -> None:
    upper = tuple(label.upper() for label in OVER)
    assert (
        render_trail(upper, "LEAF").casefold() == render_trail(OVER, "leaf").casefold()
    )


def test_the_digest_is_of_the_full_name() -> None:
    other = ("first", "z" * 70, "y" * 70, "tail")
    assert render_trail(OVER, "leaf") != render_trail(other, "leaf")
    assert render_trail(OVER, "leaf").endswith(SEP.join(("y" * 70, "tail", "leaf")))


def test_a_window_selects_another_slice_of_the_digest() -> None:
    first, second = (render_trail(OVER, "leaf", window=w) for w in (0, 1))
    assert first != second
    assert second == SEP.join(
        ("first", mark(OVER, "leaf", window=1), "y" * 70, "tail", "leaf")
    )
    with pytest.raises(ValueError):
        render_trail(OVER, "leaf", window=DIGEST_WINDOWS)


def test_a_leaf_too_long_beside_the_digest_is_refused() -> None:
    room = LAYER_NAME_LIMIT - len(DIGEST_MARK) - DIGEST_LENGTH - len(SEP)
    assert render_trail(("a" * 20,), "x" * room).endswith(SEP + "x" * room)
    with pytest.raises(WorkspaceError) as caught:
        render_trail(("a" * 20,), "x" * (room + 1))
    assert "author's choice" in str(caught.value)


def test_join_refuses_a_layer_name_over_the_limit() -> None:
    assert join("/s.gdb", "x" * LAYER_NAME_LIMIT).endswith("x" * LAYER_NAME_LIMIT)
    with pytest.raises(WorkspaceError):
        join("/s.gdb", "x" * (LAYER_NAME_LIMIT + 1))


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
