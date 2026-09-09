"""TEMPLATE — not shipped. Target: `tests/unit/`.

What `@operation` reads off a signature, and the one thing that would break it
silently.

THE FAILURE THIS FILE EXISTS FOR

`@operation` classifies a runtime-injected parameter with
`isinstance(hint, type) and issubclass(hint, Injected)` (ADR-0014). Under
`from __future__ import annotations` - which EVERY module in this package uses -
annotations are strings at runtime. If the classifier ever saw the raw
`__annotations__` instead of `get_type_hints()` output, `hint` would be the string
`"Toolbox"`, `isinstance(hint, type)` would be False, and the parameter would fall
through to... nothing, or worse, be mistaken for something else.

That is the same failure SHAPE as the `wants_scratch` bug this replaced: a wrong
classification, no error at import, and a blow-up in a pod three hours in. So it is
tested directly rather than assumed from the presence of `get_type_hints`.

`test_annotations_are_strings_at_runtime` is the load-bearing one. It asserts the
precondition - that the raw annotation really is a string in a module written the way
this project writes modules - so the test below it cannot pass vacuously if someone
removes the `__future__` import and quietly changes what is being verified.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from ag.core.injection import Injected
from ag.core.operations import (
    INJECTED,
    In,
    Out,
    ScratchScope,
    handle,
    operation,
)
from ag.ports import NOT_INJECTED, Toolbox


@dataclass(frozen=True)
class ExampleConfig:
    tolerance_m: float


class Example:
    roads = handle()
    output = handle()


@operation
def worked(
    *,
    roads: In,
    output: Out,
    config: ExampleConfig,
    tb: Toolbox = NOT_INJECTED,
    scratch: ScratchScope = INJECTED,
) -> None:
    tb.cartographic.smooth(
        input=roads, output=output, tolerance_m=config.tolerance_m
    )


# ---------------------------------------------------------------------------
# The string-annotation check
# ---------------------------------------------------------------------------


def test_annotations_are_strings_at_runtime() -> None:
    """The precondition. If this fails, the test below is no longer testing
    anything - it would be checking a resolved class against a resolved class."""
    assert worked.__wrapped__.__annotations__["tb"] == "Toolbox"  # type: ignore[attr-defined]
    assert worked.__wrapped__.__annotations__["scratch"] == "ScratchScope"  # type: ignore[attr-defined]


def test_a_string_annotation_still_classifies_as_injected() -> None:
    """`get_type_hints` resolves `"Toolbox"` against the OPERATION MODULE's globals -
    this module, which imports it - so the classifier receives a class object and
    `issubclass` works. `core/` never needs the name, which is the whole point of the
    marker base (ADR-0014).

    Without `get_type_hints`, `isinstance("Toolbox", type)` is False and `tb` is
    misclassified with no error raised anywhere.
    """
    call = worked(roads=Example.roads, output=Example.output, config=ExampleConfig(30.0))
    assert call.injected == {Toolbox: "tb", ScratchScope: "scratch"}


def test_both_injected_kinds_are_recognised_by_the_marker() -> None:
    assert issubclass(Toolbox, Injected)
    assert issubclass(ScratchScope, Injected)


# ---------------------------------------------------------------------------
# What the classifier records
# ---------------------------------------------------------------------------


def test_the_declaration_records_the_signature() -> None:
    call = worked(roads=Example.roads, output=Example.output, config=ExampleConfig(30.0))
    assert call.operation == "worked"
    assert set(call.inputs) == {"roads"}
    assert set(call.outputs) == {"output"}
    assert set(call.parameters) == {"config"}
    assert call.wants_scratch is True


def test_the_injected_parameter_name_is_not_load_bearing() -> None:
    """`tb` and `toolbox` are both correct, and neither is written twice.

    THIS IS THE BUG THE MAPPING FIXED. Under `wants_scratch: bool` the entry point
    hardcoded `kwargs["scratch"]`, so an operation naming its scope anything else
    classified correctly, reported that it wanted one, and then never received it -
    it kept the sentinel and failed at the first `scratch(...)` call, in a pod.
    """

    @operation
    def named_differently(
        *, roads: In, output: Out, toolbox: Toolbox = NOT_INJECTED, scope: ScratchScope = INJECTED
    ) -> None: ...

    call = named_differently(roads=Example.roads, output=Example.output)
    assert call.injected == {Toolbox: "toolbox", ScratchScope: "scope"}


def test_an_operation_may_take_no_toolbox() -> None:
    """`data_selection` in the building example is this shape: three handles and
    nothing else. An operation that calls no port declares none."""

    @operation
    def portless(*, roads: In, output: Out) -> None: ...

    assert portless(roads=Example.roads, output=Example.output).injected == {}


# ---------------------------------------------------------------------------
# What it rejects, all of it at import
# ---------------------------------------------------------------------------


def test_an_injected_argument_may_not_be_passed_at_a_declaration_site() -> None:
    """Both sentinels type-check at a call site - they are real values with the
    declared type - so this has to be a runtime rejection. A declaration is evaluated
    at import, where there is no workspace to allocate in and no adapter chosen."""
    for kwargs in ({"tb": NOT_INJECTED}, {"scratch": INJECTED}):
        with pytest.raises(TypeError, match="declaration site"):
            worked(
                roads=Example.roads,
                output=Example.output,
                config=ExampleConfig(30.0),
                **kwargs,  # type: ignore[arg-type]
            )


def test_two_parameters_of_one_injected_kind_are_rejected() -> None:
    """The entry point supplies one of each kind, so the second would silently
    receive the same object."""
    with pytest.raises(TypeError, match="both Toolbox"):

        @operation
        def two_toolboxes(
            *, roads: In, a: Toolbox = NOT_INJECTED, b: Toolbox = NOT_INJECTED
        ) -> None: ...


def test_a_loose_tuning_parameter_is_rejected() -> None:
    """Without this, `minimum_length_m=400` returns at the first deadline and
    `OperationCall.parameters` stops being a uniform tuning record."""
    with pytest.raises(TypeError, match="not a recognised kind"):

        @operation
        def loose(*, roads: In, minimum_length_m: float) -> None: ...


def test_an_unannotated_parameter_is_rejected() -> None:
    with pytest.raises(TypeError, match="no annotation"):

        @operation
        def unannotated(*, roads: In, whatever) -> None: ...  # type: ignore[no-untyped-def]


def test_a_positional_parameter_is_rejected() -> None:
    with pytest.raises(TypeError, match="keyword-only"):

        @operation
        def positional(roads: In) -> None: ...
