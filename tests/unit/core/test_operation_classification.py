"""What `@operation` reads off a signature, and the one thing that would break it silently.

What: the classifier recognises a runtime-injected parameter with
`isinstance(hint, type) and issubclass(hint, Injected)`. Under
`from __future__ import annotations`, which every module here uses, annotations are
strings at runtime; if the classifier ever read raw `__annotations__` instead of
`get_type_hints`, the hint would be a string, the check would be False, and the parameter
would be misclassified with no error anywhere.

Why: `test_annotations_are_strings_at_runtime` asserts the precondition, so the test
below it cannot pass vacuously if someone removes the `__future__` import. The toolbox
lives above `core` and is not imported here; a local `Injected` subclass plays its part.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Annotated, Any

import pytest

from ag.core.handles import (
    INJECTED,
    Direction,
    In,
    Mutates,
    Out,
    ParentsOut,
    ScratchHandle,
    ScratchScope,
    handle,
)
from ag.core.injection import Injected
from ag.core.operations import OperationCall, OperationDeclaration, operation


class Ports(Injected):
    """Stands in for the toolbox: a second injected kind with a sentinel default."""


NO_PORTS = Ports()


@dataclass(frozen=True)
class ExampleConfig:
    tolerance_m: float


@dataclass
class MutableConfig:
    tolerance_m: float


@dataclass(frozen=True)
class ListConfig:
    classes: list[int]


@dataclass(frozen=True, eq=False)
class IdentityConfig:
    classes: list[int]


class Example:
    roads = handle()
    output = handle()


@operation
def worked(
    *,
    roads: In,
    output: Out,
    config: ExampleConfig,
    tb: Ports = NO_PORTS,
    scratch: ScratchScope = INJECTED,
) -> None: ...


type Hidden = Annotated[ScratchHandle, Direction.IN]
"""The spelling `In` must never take: a `type` statement hides the metadata."""


def _declare() -> OperationCall:
    return worked(
        roads=Example.roads, output=Example.output, config=ExampleConfig(30.0)
    )


# ---------------------------------------------------------------------------
# The string-annotation check
# ---------------------------------------------------------------------------


def test_annotations_are_strings_at_runtime() -> None:
    """The precondition. If this fails, the test below checks a resolved class against
    a resolved class and verifies nothing."""
    assert worked.fn.__annotations__["tb"] == "Ports"
    assert worked.fn.__annotations__["scratch"] == "ScratchScope"


def test_a_string_annotation_still_classifies_as_injected() -> None:
    """`get_type_hints` resolves `"Ports"` against this module's globals, so the
    classifier receives a class object and `issubclass` works."""
    call = worked(
        roads=Example.roads, output=Example.output, config=ExampleConfig(30.0)
    )
    assert call.injected == {Ports: "tb", ScratchScope: "scratch"}


def test_both_injected_kinds_are_recognised_by_the_marker() -> None:
    assert issubclass(Ports, Injected)
    assert issubclass(ScratchScope, Injected)


# ---------------------------------------------------------------------------
# What the classifier records
# ---------------------------------------------------------------------------


def test_the_declaration_records_the_signature() -> None:
    call = worked(
        roads=Example.roads, output=Example.output, config=ExampleConfig(30.0)
    )
    assert call.operation == "worked"
    assert call.qualified_name == f"{__name__}.worked"
    assert set(call.inputs) == {"roads"}
    assert set(call.outputs) == {"output"}
    assert call.parameters == {"config": ExampleConfig(30.0)}
    assert call.wants_scratch is True
    assert call.handles() == (Example.roads, Example.output)


def test_the_declaration_object_exposes_its_shape() -> None:
    """What `functools.update_wrapper` used to hide behind `__wrapped__`."""
    assert isinstance(worked, OperationDeclaration)
    assert worked.name == "worked"
    assert worked.qualified_name == f"{__name__}.worked"
    assert worked.directions == {"roads": Direction.IN, "output": Direction.OUT}
    assert worked.config_type is ExampleConfig


def test_the_mappings_are_read_only_views() -> None:
    call = worked(
        roads=Example.roads, output=Example.output, config=ExampleConfig(30.0)
    )
    for mapping in (
        worked.directions,
        worked.injected,
        call.inputs,
        call.outputs,
        call.parameters,
        call.injected,
    ):
        assert isinstance(mapping, MappingProxyType)


def test_two_identical_declarations_are_two_calls() -> None:
    first = _declare()
    second = _declare()
    assert first != second
    assert len({first, second}) == 2


def test_the_injected_parameter_name_is_not_load_bearing() -> None:
    """The risk: an entry point that looks the scope up by a fixed name hands nothing
    to an operation that named it differently, and the sentinel fails in the pod. The
    mapping carries the name, so the entry point never guesses it."""

    @operation
    def named_differently(
        *,
        roads: In,
        output: Out,
        toolbox: Ports = NO_PORTS,
        scope: ScratchScope = INJECTED,
    ) -> None: ...

    call = named_differently(roads=Example.roads, output=Example.output)
    assert call.injected == {Ports: "toolbox", ScratchScope: "scope"}


def test_an_operation_may_take_no_injected_kind_at_all() -> None:
    @operation
    def portless(*, roads: In, output: Out) -> None: ...

    call = portless(roads=Example.roads, output=Example.output)
    assert call.injected == {}
    assert call.wants_scratch is False


# ---------------------------------------------------------------------------
# What it rejects at decoration
# ---------------------------------------------------------------------------


def test_two_parameters_of_one_injected_kind_are_rejected() -> None:
    with pytest.raises(TypeError, match="both Ports"):

        @operation
        def two_toolboxes(  # pyright: ignore[reportUnusedFunction]
            *, roads: In, a: Ports = NO_PORTS, b: Ports = NO_PORTS
        ) -> None: ...


def test_the_bare_injected_base_is_rejected() -> None:
    with pytest.raises(TypeError, match="bare Injected base"):

        @operation
        def generic(*, roads: In, tb: Injected = NO_PORTS) -> None: ...  # pyright: ignore[reportUnusedFunction]


def test_an_injected_parameter_without_a_default_is_rejected() -> None:
    with pytest.raises(TypeError, match="needs that kind's sentinel"):

        @operation
        def undefaulted(*, roads: In, tb: Ports) -> None: ...  # pyright: ignore[reportUnusedFunction]


def test_an_injected_default_of_the_wrong_kind_is_rejected() -> None:
    with pytest.raises(TypeError, match="needs that kind's sentinel"):

        @operation
        def mismatched(*, roads: In, tb: Ports = INJECTED) -> None: ...  # pyright: ignore[reportUnusedFunction, reportArgumentType]


def test_a_union_containing_an_injected_kind_is_rejected() -> None:
    with pytest.raises(TypeError, match="union containing the injected kind Ports"):

        @operation
        def optional(*, roads: In, tb: Ports | None = None) -> None: ...  # pyright: ignore[reportUnusedFunction]


def test_a_loose_tuning_parameter_is_rejected() -> None:
    with pytest.raises(TypeError, match="not a recognised kind"):

        @operation
        def loose(*, roads: In, minimum_length_m: float) -> None: ...  # pyright: ignore[reportUnusedFunction]


def test_a_generic_alias_is_rejected_without_crashing_the_classifier() -> None:
    with pytest.raises(TypeError, match="not a recognised kind"):

        @operation
        def listed(*, roads: In, classes: list[int]) -> None: ...  # pyright: ignore[reportUnusedFunction]


def test_an_unannotated_parameter_is_rejected() -> None:
    with pytest.raises(TypeError, match="no annotation"):

        @operation
        def unannotated(*, roads: In, whatever) -> None: ...  # pyright: ignore[reportUnusedFunction, reportMissingParameterType, reportUnknownParameterType]


def test_a_positional_parameter_is_rejected() -> None:
    with pytest.raises(TypeError, match="keyword-only"):

        @operation
        def positional(roads: In) -> None: ...  # pyright: ignore[reportUnusedFunction]


def test_the_mutates_marker_is_rejected_on_an_operation() -> None:
    with pytest.raises(TypeError, match="port-only marker Mutates"):

        @operation
        def mutating(*, roads: Mutates) -> None: ...  # pyright: ignore[reportUnusedFunction]


def test_the_parents_out_marker_is_rejected_on_an_operation() -> None:
    with pytest.raises(TypeError, match="port-only marker ParentsOut"):

        @operation
        def minting(*, roads: In, parents: ParentsOut) -> None: ...  # pyright: ignore[reportUnusedFunction]


def test_a_defaulted_handle_is_rejected() -> None:
    with pytest.raises(TypeError, match="has a default"):

        @operation
        def defaulted(*, roads: In, output: Out = Example.output) -> None: ...  # pyright: ignore[reportUnusedFunction]


def test_a_defaulted_config_is_rejected() -> None:
    with pytest.raises(TypeError, match="config has a default"):

        @operation
        def defaulted(  # pyright: ignore[reportUnusedFunction]
            *, roads: In, config: ExampleConfig = ExampleConfig(1.0)
        ) -> None: ...


def test_a_mutable_config_type_is_rejected() -> None:
    with pytest.raises(TypeError, match="not a frozen dataclass type"):

        @operation
        def tunable(*, roads: In, config: MutableConfig) -> None: ...  # pyright: ignore[reportUnusedFunction]


def test_a_config_that_is_not_a_dataclass_type_is_rejected() -> None:
    with pytest.raises(TypeError, match="not a frozen dataclass type"):

        @operation
        def tunable(*, roads: In, config: float) -> None: ...  # pyright: ignore[reportUnusedFunction]


def test_a_frozen_config_type_without_equality_is_rejected() -> None:
    """With `eq=False` a frozen dataclass hashes by identity, so a list field would
    slip past the hashability check at the declaration site."""
    with pytest.raises(TypeError, match="not a frozen dataclass type with equality"):

        @operation
        def tunable(*, roads: In, config: IdentityConfig) -> None: ...  # pyright: ignore[reportUnusedFunction]


def test_a_type_statement_alias_is_never_silently_misclassified() -> None:
    """A `type` statement wraps the alias in a `TypeAliasType`, which `get_origin` does
    not see through. The invariant is that such a parameter is rejected, never accepted
    as something else."""
    with pytest.raises(TypeError, match="not a recognised kind"):

        @operation
        def hidden(*, roads: Hidden) -> None: ...  # pyright: ignore[reportUnusedFunction]


# ---------------------------------------------------------------------------
# What it rejects at a declaration site
# ---------------------------------------------------------------------------


def test_an_injected_argument_may_not_be_passed_at_a_declaration_site() -> None:
    """Both sentinels type-check at a call site, so this has to be a runtime rejection."""
    with pytest.raises(TypeError, match="declaration site"):
        worked(
            roads=Example.roads,
            output=Example.output,
            config=ExampleConfig(30.0),
            tb=NO_PORTS,
        )
    with pytest.raises(TypeError, match="declaration site"):
        worked(
            roads=Example.roads,
            output=Example.output,
            config=ExampleConfig(30.0),
            scratch=INJECTED,
        )


def test_an_unknown_keyword_is_rejected_with_the_operation_named() -> None:
    extra: dict[str, Any] = {"tolerance": 1.0}
    with pytest.raises(
        TypeError, match=r"worked: .*unexpected keyword argument 'tolerance'"
    ):
        worked(
            roads=Example.roads,
            output=Example.output,
            config=ExampleConfig(30.0),
            **extra,
        )


def test_an_undeclared_handle_is_rejected() -> None:
    with pytest.raises(TypeError, match="undeclared handle"):
        worked(roads=handle(), output=Example.output, config=ExampleConfig(30.0))


def test_a_config_of_another_type_is_rejected() -> None:
    with pytest.raises(TypeError, match="instance of ExampleConfig"):
        worked(
            roads=Example.roads,
            output=Example.output,
            config=ExampleConfig,  # pyright: ignore[reportArgumentType]
        )


def test_a_frozen_config_with_a_list_field_is_rejected_as_unhashable() -> None:
    @operation
    def tunable(*, roads: In, config: ListConfig) -> None: ...

    with pytest.raises(TypeError, match="hashable"):
        tunable(roads=Example.roads, config=ListConfig([1, 2]))
