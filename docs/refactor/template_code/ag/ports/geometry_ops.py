"""TEMPLATE — not shipped. Target module: `src/ag/ports/geometry_ops.py`.

Operations on spatial datasets, plus the selection predicate algebra.

VOCABULARY COMES FROM OGC, NOT FROM ARCPY (03-architecture §2.2). No second adapter is
planned, so the value delivered by this file is entirely in the SHAPE of the contract:
a port modelled on arcpy's spelling would pass every test today and be worthless on the
day it is needed. Hence `difference` rather than `erase`, `s_intersects` rather than
`INTERSECT`, `explode_multipart` rather than `MultipartToSinglepart`.

THE METHOD SURFACE IS DERIVED, NOT INVENTED. Every method here exists because a call
site in `ag/operations/` needs it; the two worked pipelines name 29 distinct arcpy
tools between them, and this file plus `table_ops` and `cartographic_ops` is what those
29 map onto. A method with no caller is not shipped.

CONVENTIONS, all three from 03-architecture §2.3:

    ScratchHandle, never DataObject      identity and legality are the planning
                                         layer's; a port that saw them would drag it
                                         into every adapter. ADR-0003.
    project enums, never vendor strings  `end_cap: EndCap`, not `flat: bool`
    keyword-only, units in the name      `distance_m`, `tolerance_m`, `search_radius_m`
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from ag.core.operations import ScratchHandle


class Relation(Enum):
    """Spatial predicates, named as OGC CQL2 spells them over the DE-9IM model.

    These names carry the same meaning in PostGIS, GEOS, shapely and DuckDB, which is
    the entire point: an adapter author who knows any of those already knows what
    `s_within` must do, and does not have to guess what arcpy meant by
    `HAVE_THEIR_CENTER_IN`.

    TWO ARCPY RELATIONS ARE ABSENT, DELIBERATELY:

      WITHIN_A_DISTANCE      is DWITHIN plus `distance_m`, which is how CQL2 spells
                             it and what a SQL adapter can compile.
      HAVE_THEIR_CENTER_IN   is not a relation at all. It is
                             `s_within(centroid(geom), other)`, and it is the rule
                             fan-in uses to decide feature ownership. Expressing it
                             as a magic relation would leave a future adapter with a
                             primitive nothing else has; expressing it as a composite
                             leaves it with two it already has.
    """

    INTERSECTS = "s_intersects"
    WITHIN = "s_within"
    CONTAINS = "s_contains"
    TOUCHES = "s_touches"
    CROSSES = "s_crosses"
    OVERLAPS = "s_overlaps"
    DISJOINT = "s_disjoint"
    EQUALS = "s_equals"
    DWITHIN = "s_dwithin"


class EndCap(Enum):
    ROUND = "round"
    FLAT = "flat"


class JoinStyle(Enum):
    ROUND = "round"
    MITRE = "mitre"
    BEVEL = "bevel"


class DissolveOption(Enum):
    """Whether dissolved features may be multipart.

    SINGLE_PART is the one to reach for: the pipeline explodes multiparts early
    (`explode_multipart`) because per-feature reasoning downstream assumes one
    geometry per row.
    """

    MULTI_PART = "multi_part"
    SINGLE_PART = "single_part"


class VertexPosition(Enum):
    """Which vertices `vertices_to_points` emits."""

    ALL = "all"
    START = "start"
    END = "end"
    BOTH_ENDS = "both_ends"
    MIDPOINT = "midpoint"
    DANGLE = "dangle"


# ---------------------------------------------------------------------------
# The predicate algebra
#
# ADR-0001: selection is a composable predicate VALUE, not a held selection. A
# mutable selection is the arcpy idiom, not the concept, and exposing it would force
# every future adapter to emulate it. It is also lazier - nothing materializes until
# `select`.
#
# This collapses the largest idiom cluster in the current codebase, the 616-site
# make-layer/select-by-attribute/select-by-location triple, into two methods and a
# value type.
# ---------------------------------------------------------------------------


class Predicate:
    """A selection expression. Combine with `&`, `|` and `~`.

    NOT AN ABC AND NOT A PROTOCOL: a closed set of five variants that an adapter
    pattern-matches exhaustively. Structural typing would be actively wrong here -
    an adapter compiling this tree needs to know it has seen every case, and
    `match` over a closed set is what gives it that.
    """

    def __and__(self, other: Predicate) -> Predicate:
        return And((self, other))

    def __or__(self, other: Predicate) -> Predicate:
        return Or((self, other))

    def __invert__(self) -> Predicate:
        return Not(self)


@dataclass(frozen=True)
class Attr(Predicate):
    """An attribute predicate, as a CQL2 text expression.

    A STRING, AND IT STAYS ONE. It names fields in data the program does not own, so
    by the identifier/value test in ADR-0011 it is a value. CQL2-Text rather than SQL
    because SQL dialects differ per backend and CQL2 is the standard both a SQL and a
    dataframe adapter can compile to.
    """

    cql: str


@dataclass(frozen=True)
class Spatial(Predicate):
    """A spatial predicate against another dataset."""

    relate_to: ScratchHandle
    relation: Relation
    distance_m: float | None = None

    def __post_init__(self) -> None:
        needs_distance = self.relation is Relation.DWITHIN
        if needs_distance and self.distance_m is None:
            raise ValueError("DWITHIN requires distance_m")
        if not needs_distance and self.distance_m is not None:
            raise ValueError(
                f"{self.relation.value} takes no distance_m. Only DWITHIN is a "
                "distance relation; passing one anywhere else means the caller "
                "expected a buffer that will not happen."
            )


@dataclass(frozen=True)
class And(Predicate):
    terms: tuple[Predicate, ...]


@dataclass(frozen=True)
class Or(Predicate):
    terms: tuple[Predicate, ...]


@dataclass(frozen=True)
class Not(Predicate):
    term: Predicate


def Intersects(other: ScratchHandle) -> Spatial:
    """Sugar, so a call site reads as the cartographer would say it."""
    return Spatial(relate_to=other, relation=Relation.INTERSECTS)


def Within(other: ScratchHandle) -> Spatial:
    return Spatial(relate_to=other, relation=Relation.WITHIN)


def DWithin(other: ScratchHandle, distance_m: float) -> Spatial:
    return Spatial(relate_to=other, relation=Relation.DWITHIN, distance_m=distance_m)


# ---------------------------------------------------------------------------
# The port
# ---------------------------------------------------------------------------


class GeometryOps(Protocol):
    """Operations on spatial datasets. 25-35 methods; ADR-0002 for the split.

    COARSE ON PURPOSE. Interface segregation applies when clients depend on different
    subsets, and here any operation potentially uses any geometry method
    (03-architecture §4.7). Splitting this further is settled by measurement, not by
    ISP.
    """

    # -- selection (ADR-0001) ----------------------------------------------

    def select(
        self, *, input: ScratchHandle, where: Predicate, output: ScratchHandle
    ) -> None:
        """Materialize the features matching `where`."""
        ...

    def count(self, *, input: ScratchHandle, where: Predicate | None = None) -> int:
        """How many features match, without materializing them.

        NO `any()` TWIN. It only pays when a backend can short-circuit (SQL `EXISTS`,
        `LIMIT 1`), and arcpy's `GetCount` cannot. Comparing this to zero covers the
        boolean case at the one cost that matters.
        """
        ...

    # -- dataset shape ------------------------------------------------------

    def copy(self, *, input: ScratchHandle, output: ScratchHandle) -> None: ...

    def merge(
        self, *, inputs: tuple[ScratchHandle, ...], output: ScratchHandle
    ) -> None:
        """Concatenate several datasets of the same geometry kind."""
        ...

    def explode_multipart(self, *, input: ScratchHandle, output: ScratchHandle) -> None:
        """One row per part. arcpy calls this MultipartToSinglepart."""
        ...

    def dissolve(
        self,
        *,
        input: ScratchHandle,
        output: ScratchHandle,
        fields: tuple[str, ...] = (),
        option: DissolveOption = DissolveOption.SINGLE_PART,
    ) -> None: ...

    # -- OGC Simple Features -----------------------------------------------

    def buffer(
        self,
        *,
        input: ScratchHandle,
        output: ScratchHandle,
        distance_m: float,
        end_cap: EndCap = EndCap.ROUND,
        join_style: JoinStyle = JoinStyle.ROUND,
    ) -> None: ...

    def intersection(
        self, *, input: ScratchHandle, overlay: ScratchHandle, output: ScratchHandle
    ) -> None:
        """arcpy calls this Intersect."""
        ...

    def difference(
        self, *, input: ScratchHandle, overlay: ScratchHandle, output: ScratchHandle
    ) -> None:
        """arcpy calls this Erase. The OGC name is `difference`, and it is the one a
        PostGIS or shapely adapter author already knows."""
        ...

    def union(
        self, *, inputs: tuple[ScratchHandle, ...], output: ScratchHandle
    ) -> None: ...

    def clip(
        self, *, input: ScratchHandle, boundary: ScratchHandle, output: ScratchHandle
    ) -> None:
        """Dataset-level, unlike `intersection`, which is geometry-level. The two are
        genuinely different operations and arcpy is right to separate them."""
        ...

    # arcpy's Identity IS ABSENT, and its absence is the general rule in miniature.
    # It has no OGC counterpart, and it decomposes without residue into two standard
    # operations plus one explicit rule:
    #
    #     identity(input, overlay) == merge(intersection(input, overlay),
    #                                       difference(input, overlay))
    #
    # `helpers`-style decomposition, written out at the one call site that wants it
    # (`_attach_area_attributes` in operations/road). See 03-architecture §2.2 on the
    # same treatment for HAVE_THEIR_CENTER_IN.

    def centroid(self, *, input: ScratchHandle, output: ScratchHandle) -> None: ...

    def convex_hull(self, *, input: ScratchHandle, output: ScratchHandle) -> None: ...

    # -- geometry quality ---------------------------------------------------

    def validate_geometry(self, *, input: ScratchHandle, output: ScratchHandle) -> None:
        """A table of validity problems. Does not modify `input`.

        NOT `ST_IsValid`, which is a boolean per row. This reports WHAT is wrong and
        WHERE, because the caller's next move is to downgrade the affected features
        rather than to filter them - see `select_source_roads`, whose `geometry_errors`
        output the hierarchy operation reads.
        """
        ...

    def make_valid(self, *, input: ScratchHandle, output: ScratchHandle) -> None:
        """OGC's name for it, and PostGIS's. arcpy calls this RepairGeometry."""
        ...

    def densify(
        self, *, input: ScratchHandle, output: ScratchHandle, max_deviation_m: float
    ) -> None: ...

    def snap(
        self,
        *,
        input: ScratchHandle,
        reference: ScratchHandle,
        output: ScratchHandle,
        tolerance_m: float,
    ) -> None: ...

    # -- derived points and topology helpers --------------------------------

    def extract_vertices(
        self,
        *,
        input: ScratchHandle,
        output: ScratchHandle,
        position: VertexPosition = VertexPosition.ALL,
    ) -> None:
        """The vertices as points. PostGIS spells this ST_DumpPoints."""
        ...

    def point_on_surface(self, *, input: ScratchHandle, output: ScratchHandle) -> None:
        """One representative point per feature, guaranteed to lie ON the feature.

        SEPARATE FROM `centroid`, NOT A FLAG ON IT. arcpy's FeatureToPoint takes an
        `inside` boolean and switches between two genuinely different operations - a
        centroid can fall outside a concave polygon or off a curved line, which is
        exactly when a caller cares. OGC and PostGIS name them separately
        (ST_PointOnSurface, ST_Centroid); collapsing them into a boolean would have
        been the vendor's spelling of a distinction the standard makes.
        """
        ...

    def split_at_points(
        self,
        *,
        input: ScratchHandle,
        points: ScratchHandle,
        output: ScratchHandle,
        search_radius_m: float = 0.0,
    ) -> None: ...

    def cluster_points(
        self,
        *,
        input: ScratchHandle,
        output: ScratchHandle,
        search_radius_m: float,
        minimum_count: int = 2,
    ) -> None: ...

    # -- proximity ----------------------------------------------------------

    def nearest_neighbors(
        self,
        *,
        input: ScratchHandle,
        near: ScratchHandle,
        output: ScratchHandle,
        search_radius_m: float,
        closest_count: int = 1,
    ) -> None:
        """For each input feature, its k closest features in `near`, as a table.

        A k-nearest-neighbour join, which is what every target engine calls it and
        what each can compile: a KNN index scan in PostGIS, `STRtree.nearest` in
        shapely, a LATERAL join in SQL. arcpy's name for it is GenerateNearTable, and
        03-architecture §3.3 names it as one of the six things `line_topology.py`
        decomposes into.
        """
        ...

    def spatial_join(
        self,
        *,
        target: ScratchHandle,
        join: ScratchHandle,
        output: ScratchHandle,
        relation: Relation = Relation.INTERSECTS,
        search_radius_m: float | None = None,
    ) -> None: ...
