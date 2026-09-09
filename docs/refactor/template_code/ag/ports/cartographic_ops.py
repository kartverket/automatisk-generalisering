"""TEMPLATE — not shipped. Target module: `src/ag/ports/cartographic_ops.py`.

Named generalization operators. 8-12 methods.

THE RESIDUE, AND WHY IT IS ITS OWN PORT. Most arcpy calls have near-1:1 equivalents
elsewhere; the ones that do not are concentrated here. In the current codebase the
cartography toolbox is 78 of 2801 tool call sites across 16 distinct tools - small and
enumerable, but each member needs hundreds to thousands of lines to reproduce. Keeping
them behind their own port is what lets the migration be incremental: `GeometryOps` and
`TableOps` can get a second adapter long before this one does. ADR-0002.

NAMES COME FROM THE ICA OPERATOR TAXONOMY, so each one describes what the cartographer
wanted rather than which vendor button was pressed, and each maps to a published
literature trail for whoever reimplements it:

    ResolveBuildingConflicts, ResolveRoadConflicts   displacement    displace_features
    PropagateDisplacement                            displacement    propagate_displacement
    ThinRoadNetwork                                  selection       select_network
    SimplifyLine, SimplifyPolygon                    simplification  simplify
    SmoothLine                                       smoothing       smooth
    AggregatePolygons                                aggregation     aggregate
    MergeDividedRoads, CollapseDualLinesToCenterline collapse        collapse_to_centerline
    polygon-to-point                                 collapse        collapse_to_point

Q-B IS STILL OPEN: whether this should be several ports rather than one. Displacement
and network selection share no vocabulary, and if their reimplementations are
independent projects, splitting per operator lets them land separately. Deferred until
at least one is reimplemented, and settled by measurement rather than by interface
segregation (03-architecture §4.7).

THIS FILE IMPORTS `geometry_ops` FOR ONE NAME. `select_network` takes a `Predicate` for
the exempt set, because the alternative is a second selection vocabulary that means the
same thing. That import is not the port layering of §4.3 - that constraint is about an
IMPLEMENTATION written against other ports, which is an `adapters/` concern, and it is
enforced there.
"""

from __future__ import annotations

from typing import Protocol

from ag.core.operations import ScratchHandle
from ag.ports.geometry_ops import Predicate


class CartographicOps(Protocol):
    """The named generalization operators."""

    # -- simplification and smoothing ---------------------------------------

    def simplify(
        self,
        *,
        input: ScratchHandle,
        output: ScratchHandle,
        tolerance_m: float,
        collapsed_points: ScratchHandle | None = None,
    ) -> None:
        """Vertex reduction, for lines or polygons alike.

        ONE METHOD FOR SimplifyLine AND SimplifyPolygon. The geometry kind is a
        property of the input, not a choice the caller makes, and an adapter can read
        it. Two methods would make every caller restate what its own data already
        says.

        `collapsed_points` IS OPTIONAL AND DECLARING IT MATTERS. The tool emits a
        point feature class for features that collapse below the tolerance; passing
        None discards them. Threading it through is what lets a finalize step account
        for every input feature rather than silently losing the small ones.
        """
        ...

    def smooth(
        self,
        *,
        input: ScratchHandle,
        output: ScratchHandle,
        tolerance_m: float,
        barriers: ScratchHandle | None = None,
    ) -> None:
        """Bend smoothing. `barriers` are features the result may not cross."""
        ...

    # -- aggregation and collapse -------------------------------------------

    def aggregate(
        self,
        *,
        input: ScratchHandle,
        output: ScratchHandle,
        distance_m: float,
        minimum_area_m2: float | None = None,
        minimum_hole_area_m2: float | None = None,
    ) -> None: ...

    def collapse_to_centerline(
        self,
        *,
        input: ScratchHandle,
        output: ScratchHandle,
        max_separation_m: float,
        pairs: ScratchHandle | None = None,
    ) -> None:
        """Dual carriageways and dual lines into a single line.

        `pairs` is an optional precomputed pairing table, which is how
        `merge_divided_highways` supplies its own matching rather than accepting the
        tool's.
        """
        ...

    def collapse_to_point(
        self, *, input: ScratchHandle, output: ScratchHandle
    ) -> None: ...

    # -- selection ----------------------------------------------------------

    def select_network(
        self,
        *,
        input: ScratchHandle,
        output: ScratchHandle,
        dropped: ScratchHandle,
        minimum_length_m: float,
        weight_field: str | None = None,
        exempt: Predicate | None = None,
    ) -> None:
        """Density-based network thinning, preserving connectivity.

        `dropped` IS REQUIRED, NOT OPTIONAL, unlike `simplify`'s collapsed points.
        What a thinning operation removed is not a diagnostic here - `resolve_ramps`
        reads it to reinstate ramp stubs that connectivity alone would discard - so
        the contract makes discarding it impossible rather than merely discouraged.
        """
        ...

    # -- displacement -------------------------------------------------------

    def displace_features(
        self,
        *,
        input: ScratchHandle,
        output: ScratchHandle,
        barriers: ScratchHandle,
        minimum_clearance_m: float,
        displacement: ScratchHandle | None = None,
    ) -> None:
        """Move features apart until they are legible at the target scale.

        ONE METHOD FOR ResolveRoadConflicts AND ResolveBuildingConflicts. Both are
        the displacement operator; what differs is the data and the symbology, not
        the operation. `.lyrx` does not appear here - producing one is an
        implementation detail inside the arcpy adapter, which is how the migration
        avoids inheriting it (03-architecture §7.5).
        """
        ...

    def propagate_displacement(
        self,
        *,
        input: ScratchHandle,
        displacement: ScratchHandle,
        output: ScratchHandle,
    ) -> None:
        """Apply a displacement computed for one layer to another that must follow
        it, so the two do not disagree after the fact."""
        ...
