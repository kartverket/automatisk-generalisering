"""Handle naming, handle identity and the scratch scope.

What: a handle object bound in two class bodies is refused instead of being silently
renamed; internal handles created by two operations, or at two points of one operation's
trail, are different values; equality ignores `path`; `namespace` is in equality; the
markers carry their direction and stay `Annotated` aliases; the sentinels fail with a
sentence.
"""

from __future__ import annotations

import os
from typing import Annotated, get_args, get_origin

import pytest

from ag.core.errors import InjectionError
from ag.core.handles import (
    INJECTED,
    TRAIL_SEPARATOR,
    Direction,
    In,
    Mutates,
    Out,
    ParentsOut,
    ScratchHandle,
    ScratchScope,
    handle,
)
from ag.core.types import DataType


class Network:
    roads = handle()
    paired = handle(DataType.TABLE)
    final = handle()


class ConflictResolution:
    final = handle()


def _fake_materialize(trail: tuple[str, ...], leaf: str, data_type: DataType) -> str:
    """A scratch manager stand-in: a path, and nothing about identity."""
    return f"/scratch/{'__'.join((*trail, leaf))}"


def _scope(namespace: str) -> ScratchScope:
    return ScratchScope(namespace=namespace, trail=(), materialize=_fake_materialize)


# ---------------------------------------------------------------------------
# Declared handles
# ---------------------------------------------------------------------------


def test_a_class_attribute_names_its_handle() -> None:
    assert Network.roads.name == "roads"
    assert Network.roads.namespace == f"{__name__}.Network"
    assert Network.paired.data_type is DataType.TABLE
    assert repr(Network.roads) == f"ScratchHandle({__name__}.Network.roads)"


def test_a_handle_outside_a_class_body_stays_undeclared() -> None:
    loose = handle()
    assert loose.name == ""
    assert loose.namespace == ""
    assert repr(loose) == "ScratchHandle('', UNDECLARED)"


def test_the_namespace_tells_two_stages_handles_apart() -> None:
    """Both classes have a `final`; without `namespace` in equality they would be one
    key in every structure keyed by handle."""
    assert Network.final != ConflictResolution.final
    assert len({Network.final, ConflictResolution.final}) == 2


def test_a_handle_bound_in_two_class_bodies_is_refused() -> None:
    """One object in two class bodies would otherwise be renamed by the second, leaving
    the first class wired to a handle that is not its own."""
    shared = handle()

    class First:
        h = shared

    with pytest.raises(TypeError, match="already named"):

        class Second:  # pyright: ignore[reportUnusedClass]
            h = shared

    assert First.h.namespace == f"{__name__}.{First.__qualname__}"


def test_a_prenamed_handle_is_refused_as_a_class_attribute() -> None:
    with pytest.raises(TypeError, match="already named"):

        class Owner:  # pyright: ignore[reportUnusedClass]
            h = ScratchHandle(name="elsewhere")


# ---------------------------------------------------------------------------
# Materialisation
# ---------------------------------------------------------------------------


def test_a_materialised_copy_equals_its_declaration() -> None:
    """The stage entry point builds {declared: materialised} and looks one up by the
    other, which is why `path` is excluded from equality."""
    runtime = Network.roads.materialize("/scratch/stage.gdb/roads")
    assert runtime == Network.roads
    assert hash(runtime) == hash(Network.roads)
    assert runtime is not Network.roads
    assert Network.roads.path is None
    assert runtime.path == "/scratch/stage.gdb/roads"
    assert repr(runtime).endswith(", path='/scratch/stage.gdb/roads')")


def test_a_materialised_handle_is_a_path() -> None:
    runtime = Network.roads.materialize("/scratch/stage.gdb/roads")
    assert os.fspath(runtime) == "/scratch/stage.gdb/roads"


def test_a_declaration_used_as_a_path_raises_injection_error() -> None:
    with pytest.raises(InjectionError, match="never materialised"):
        os.fspath(Network.roads)


# ---------------------------------------------------------------------------
# The markers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("marker", "direction"),
    [
        (In, Direction.IN),
        (Out, Direction.OUT),
        (Mutates, Direction.MUTATES),
        (ParentsOut, Direction.PARENTS_OUT),
    ],
)
def test_each_marker_carries_its_direction(
    marker: object, direction: Direction
) -> None:
    """Also the pin that keeps the markers `TypeAlias` statements: a PEP 695 `type`
    statement wraps the alias in a `TypeAliasType`, `get_origin` returns None, and this
    test fails on the first line."""
    assert get_origin(marker) is Annotated
    assert direction in get_args(marker)[1:]


def test_parents_out_is_optional_and_the_others_are_not() -> None:
    assert get_args(ParentsOut)[0] == ScratchHandle | None
    for marker in (In, Out, Mutates):
        assert get_args(marker)[0] is ScratchHandle


# ---------------------------------------------------------------------------
# The scratch scope
# ---------------------------------------------------------------------------


def test_internal_handles_of_two_operations_are_different_values() -> None:
    """Identity comes from the scope, not from the scratch manager: two operations
    asking for `dissolved` get two handles, or every structure keyed by handle would
    conflate them."""
    first = _scope("thin_road_network")("dissolved")
    second = _scope("resolve_ramps")("dissolved")
    assert first != second
    assert len({first: 1, second: 2}) == 2
    assert first.namespace == "thin_road_network"
    assert first.name == "dissolved"


def test_the_same_leaf_at_three_points_of_one_trail_is_three_handles() -> None:
    root = _scope("op")
    at_root = root("x")
    in_first_child = root.child("h")("x")
    in_second_child = root.child("h")("x")
    assert at_root != in_first_child
    assert in_first_child != in_second_child
    assert at_root != in_second_child
    assert len({at_root, in_first_child, in_second_child}) == 3
    assert in_first_child.name == f"h{TRAIL_SEPARATOR}x"
    assert in_second_child.name == f"h_2{TRAIL_SEPARATOR}x"


def test_a_scope_creates_a_materialised_handle_of_the_asked_type() -> None:
    created = _scope("op")("paired", DataType.TABLE)
    assert created.data_type is DataType.TABLE
    assert created.path == "/scratch/paired"
    assert os.fspath(created) == "/scratch/paired"


def test_a_child_scope_keeps_the_namespace_and_extends_the_trail() -> None:
    root = _scope("op")
    child = root.child("build_topology")
    assert child.namespace == "op"
    assert child.trail == ("build_topology",)
    assert child("nodes").path == "/scratch/build_topology__nodes"


def test_repeated_child_labels_take_the_first_unused_index() -> None:
    root = _scope("op")
    segments = [
        root.child("a").trail[-1],
        root.child("a").trail[-1],
        root.child("a", tag="2").trail[-1],
    ]
    assert segments == ["a", "a_2", "a_2_2"]
    assert len(set(segments)) == 3


def test_a_tagged_label_and_a_label_spelled_like_it_are_two_segments() -> None:
    root = _scope("op")
    tagged = root.child("a", tag="b").trail[-1]
    spelled = root.child("a_b").trail[-1]
    assert tagged == "a_b"
    assert spelled == "a_b_2"


def test_a_label_or_tag_that_cannot_be_a_layer_name_part_is_refused() -> None:
    root = _scope("op")
    for bad in ("", "a__b", "_a", "a-b", "a b", "a/b"):
        with pytest.raises(ValueError, match="letters, digits and single underscores"):
            root.child(bad)
    with pytest.raises(ValueError, match="scope tag"):
        root.child("a", tag="x__y")


def test_a_leaf_that_cannot_be_a_layer_name_part_is_refused() -> None:
    """A separator inside a leaf would make `scratch("a/b")` equal to
    `scratch.child("a")("b")`, and a double underscore would collide in the rendered
    layer name."""
    root = _scope("op")
    for bad in ("a/b", "a__b", "", "a b"):
        with pytest.raises(ValueError, match="scope leaf"):
            root(bad)


def test_a_scope_has_identity_equality_and_is_hashable() -> None:
    one = _scope("op")
    other = _scope("op")
    assert one != other
    assert one == one
    assert len({one, other}) == 2


def test_the_injected_sentinel_fails_with_a_sentence() -> None:
    with pytest.raises(InjectionError, match="never bound"):
        INJECTED("dissolved")


def test_the_injected_sentinel_reports_the_missing_binding_before_the_leaf() -> None:
    """An unbound scope is the larger fault; a bad leaf on it must not hide it."""
    with pytest.raises(InjectionError, match="never bound"):
        INJECTED("a/b")


def test_the_injected_sentinel_refuses_a_child_before_any_bookkeeping() -> None:
    with pytest.raises(InjectionError, match="never bound"):
        INJECTED.child("build_topology")
    # The bookkeeping is the issued-segment set; private access is the point of the test.
    assert INJECTED._issued == set()  # pyright: ignore[reportPrivateUsage]
