"""TEMPLATE / EXAMPLE — a worked pipeline. Target: `src/ag/operations/building/`.

Building generalization operations and their config types.

In reality this is `generalization/building/operations.py`, and it is SCALE-AGNOSTIC:
written once, reused by every scale that wants it.

Note what does NOT appear anywhere in this file: ExternalSource, ProductIdentity,
Derived, location, scale, role, context radius, run id, partition index. An operation
deals in ScratchHandles, one config, the ports the runtime injects, and a
ScratchScope. That is the whole vocabulary - and the Toolbox adds capability to it,
never context: an operation can call `tb.geometry.buffer` and can still learn nothing
about where it is running.

CI EVALUATES THESE DECLARATIONS TO BUILD THE GRAPH, so calling a decorated operation
must be safe with no data and no arcpy - guarded by a test that blocks both in a
subprocess. @operation satisfies that: the wrapper builds an OperationCall and never
touches the body.
"""

from __future__ import annotations

from dataclasses import dataclass

from ag.core.operations import INJECTED, In, Out, ScratchScope, operation
from ag.ports import NOT_INJECTED, Attr, DissolveOption, Toolbox


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
def data_selection(
    *, source: In, codes: In, output: Out, tb: Toolbox = NOT_INJECTED
) -> None:
    """Copy and subselect external input.

    THREE HANDLES AND A TOOLBOX - no config, no scratch. This still runs on a laptop
    against a directory of gdbs with no credentials, no cluster and no mocking; what
    changed is that the toolbox is now one of the things handed in rather than an
    `import arcpy` at the top of the module. A test constructs a fake and passes it,
    which is strictly easier than monkeypatching a global. See
    tests/unit/test_road_operations.py.

    `codes` is a NON-SPATIAL LOOKUP TABLE, replicated whole to every pod rather than
    partitioned. It is the case that earns `TableOps` its separation from
    `GeometryOps` (03-architecture §2.1).
    """
    tb.geometry.select(
        input=source,
        where=Attr("byggtyp_nbr in (select code from codes)"),
        output=output,
    )


@operation
def simplify_polygons(
    *,
    input: In,
    output: Out,
    config: SimplifyPolygonsConfig,
    tb: Toolbox = NOT_INJECTED,
    scratch: ScratchScope = INJECTED,
) -> None:
    """ONE `simplify` FOR LINES AND POLYGONS ALIKE. arcpy has SimplifyLine and
    SimplifyPolygon; the geometry kind is a property of the input, not a choice the
    caller makes, so the port has one method and the adapter reads the kind. Compare
    `simplify_road_geometry`, which is the same two calls over lines."""
    densified = scratch("densified")
    tb.geometry.densify(
        input=input, output=densified, max_deviation_m=config.tolerance_m / 10.0
    )
    tb.cartographic.simplify(
        input=densified, output=output, tolerance_m=config.tolerance_m
    )


@operation
def build_displacement_feature(
    *,
    roads: In,
    generalized_roads: In,
    output: Out,
    config: DisplacementFeatureConfig,
    tb: Toolbox = NOT_INJECTED,
    scratch: ScratchScope = INJECTED,
) -> None:
    """The operation that makes a genuinely NEW object out of road data."""
    buffered = scratch("buffered")
    merged = scratch("merged")
    tb.geometry.buffer(input=roads, output=buffered, distance_m=config.buffer_m)
    tb.geometry.merge(inputs=(buffered, generalized_roads), output=merged)
    tb.geometry.dissolve(
        input=merged, output=output, option=DissolveOption.SINGLE_PART
    )


@operation
def propagate_displacement(
    *,
    input: In,
    displacement: In,
    output: Out,
    tb: Toolbox = NOT_INJECTED,
    scratch: ScratchScope = INJECTED,
) -> None:
    """Note this operation has no idea it is running on a partition, and no idea how
    much halo was included around it.

    That ignorance is load-bearing. An operation that knew its context radius could
    behave differently near a partition edge - and a feature appearing as center-in
    for one partition and as halo context for another must be displaced IDENTICALLY
    in both, or fan-in stitches together geometry that disagrees with itself.

    THE TOOLBOX DOES NOT WEAKEN THAT. It carries capability and no context: there is
    nothing on `tb` that could tell this function which partition it is in, and the
    adapter behind `tb.cartographic` is the same object in every pod of the stage.
    """
    prepared = scratch("prepared")
    tb.geometry.copy(input=input, output=prepared)
    tb.cartographic.propagate_displacement(
        input=prepared, displacement=displacement, output=output
    )
