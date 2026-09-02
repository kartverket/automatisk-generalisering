"""TEMPLATE / EXAMPLE — a worked pipeline. Target: `src/ag/operations/building/`.

Building generalization operations and their config types.

In reality this is `generalization/building/operations.py`, and it is SCALE-AGNOSTIC:
written once, reused by every scale that wants it.

Note what does NOT appear anywhere in this file: ExternalSource, ProductIdentity,
Derived, location, scale, role, context radius, run id, partition index. An operation
deals in ScratchHandles, one config, and an optional ScratchScope. That is the whole
vocabulary.

CI EVALUATES THESE DECLARATIONS TO BUILD THE GRAPH, so calling a decorated operation
must be safe with no data and no arcpy - guarded by a test that blocks both in a
subprocess. @operation satisfies that: the wrapper builds an OperationCall and never
touches the body.
"""

from __future__ import annotations

from dataclasses import dataclass

from ag.core.operations import INJECTED, In, Out, ScratchScope, operation


@dataclass(frozen=True)
class SimplifyPolygonsConfig:
    tolerance_m: float

    def __post_init__(self) -> None:
        if self.tolerance_m <= 0:
            raise ValueError("tolerance_m must be positive")


@dataclass(frozen=True)
class DisplacementFeatureConfig:
    buffer_m: float


@operation
def data_selection(*, source: In, codes: In, output: Out) -> None:
    """Copy and subselect external input.

    Three ScratchHandles and nothing else - no config, no scratch. This runs on a
    laptop against a directory of gdbs with no credentials, no cluster, and no
    mocking, which is the property worth protecting and the reason read/write
    callables must not appear here. See test_example_road_operations.py.
    """
    raise NotImplementedError("arcpy.conversion.FeatureClassToFeatureClass(...)")


@operation
def simplify_polygons(
    *,
    input: In,
    output: Out,
    config: SimplifyPolygonsConfig,
    scratch: ScratchScope = INJECTED,
) -> None:
    densified = scratch("densified")
    raise NotImplementedError(
        f"Densify -> {densified}, SimplifyPolygon at {config.tolerance_m}m -> {output}"
    )


@operation
def build_displacement_feature(
    *,
    roads: In,
    generalized_roads: In,
    output: Out,
    config: DisplacementFeatureConfig,
    scratch: ScratchScope = INJECTED,
) -> None:
    """The operation that makes a genuinely NEW object out of road data."""
    buffered = scratch("buffered")
    merged = scratch("merged")
    raise NotImplementedError(
        f"Buffer({roads}, {config.buffer_m}) -> {buffered}, merge with "
        f"{generalized_roads} -> {merged}, dissolve -> {output}"
    )


@operation
def propagate_displacement(
    *, input: In, displacement: In, output: Out, scratch: ScratchScope = INJECTED
) -> None:
    """Note this operation has no idea it is running on a partition, and no idea how
    much halo was included around it.

    That ignorance is load-bearing. An operation that knew its context radius could
    behave differently near a partition edge - and a feature appearing as center-in
    for one partition and as halo context for another must be displaced IDENTICALLY
    in both, or fan-in stitches together geometry that disagrees with itself.
    """
    prepared = scratch("prepared")
    raise NotImplementedError(
        f"CopyFeatures({input}) -> {prepared}, "
        f"PropagateDisplacement using {displacement} -> {output}"
    )
