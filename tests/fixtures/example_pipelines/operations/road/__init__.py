"""TEMPLATE / EXAMPLE — a worked pipeline. Target: `src/ag/operations/road/`.

Road generalization operations and their config types.

SCALE-AGNOSTIC: nothing here knows about N100. The same `thin_road_network` runs at
N50 with a different config.

THREE HALVES, AND NONE OF THEM IS BOILERPLATE

    the CONFIG    a frozen dataclass per operation, holding everything tunable.
                  Declared here, next to the operation it constrains, because its
                  FIELDS change when the operation changes. Its VALUES change per
                  scale and live in the tuning modules.
    the FUNCTION  In/Out handles, one `config`, a Toolbox and a ScratchScope.
                  @operation makes it its own declaration factory.
    the HELPERS   undecorated, never named in a stage, taking whatever they need.
                  They receive `tb` and a derived scope exactly as an operation does.

WHAT CHANGED WHEN PORTS ARRIVED. These functions used to raise NotImplementedError
with the arcpy tools they would have run. Now they run port calls, and the arcpy tool
names live in `adapters/arcpy/` where a second adapter can replace them. Read any
function below and the ONLY vendor-shaped thing left is the CQL2 in an `Attr(...)`,
which names fields in data we do not own and is a value, not a vendor idiom.

That move is also the design's own acceptance test. If an operation could not be
written without reaching for something arcpy-specific, the port surface would be
wrong - and twice it was: `Identity` and `FeatureToPoint(inside=...)` had no OGC
counterpart, and both decomposed into standard operations plus an explicit rule
rather than becoming a method. See `_attach_area_attributes`.

NO `scale` FIELD IN ANY CONFIG. If an operation can read the scale it can branch on
it, and "an operation never knows what scale it is running at" stops being enforced by
anything. The scale selects WHICH config; it is never IN the config.

Note what appears NOWHERE in this file: ExternalSource, ProductIdentity, Derived,
location, scale, role, context radius, run id, partition index, an adapter, or
`import arcpy`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ag.core.operations import INJECTED, In, Out, ScratchScope, operation
from ag.core.types import DataType
from ag.ports import (
    NOT_INJECTED,
    Attr,
    DissolveOption,
    Field,
    FieldType,
    Intersects,
    Row,
    Toolbox,
    VertexPosition,
)

TABLE = DataType.TABLE


# ---------------------------------------------------------------------------
# Configs
#
# Frozen, with __post_init__ constraints. This is the first place in the design with
# anywhere to put a constraint on a VALUE - a stage cannot check that a tolerance is
# positive, because until now the tolerance was a loose keyword argument.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NetworkWeightsConfig:
    """Relative importance by road class. Consumed by TWO operations.

    THE CASE THAT EARNS NESTING. `calculate_road_hierarchy` assigns the ranks and
    `thin_road_network` spends them; if the two disagree, thinning drops arterials
    and keeps farm tracks, with no error. Declaring it once per scale and
    referencing it from both configs is what makes disagreement unrepresentable.
    """

    arterial: float
    collector: float
    local: float

    def __post_init__(self) -> None:
        if not (self.arterial >= self.collector >= self.local > 0):
            raise ValueError(
                f"weights must be positive and non-increasing by importance, got "
                f"{self.arterial}/{self.collector}/{self.local}"
            )


@dataclass(frozen=True)
class SelectSourceRoadsConfig:
    minimum_class: int

    def __post_init__(self) -> None:
        if self.minimum_class < 1:
            raise ValueError(f"minimum_class must be >= 1, got {self.minimum_class}")


@dataclass(frozen=True)
class JoinAdminConfig:
    search_radius_m: float

    def __post_init__(self) -> None:
        if self.search_radius_m < 0:
            raise ValueError("search_radius_m must not be negative")


@dataclass(frozen=True)
class HierarchyConfig:
    weights: NetworkWeightsConfig
    repaired_geometry_penalty: int


@dataclass(frozen=True)
class MergeDividedConfig:
    max_separation_m: float

    def __post_init__(self) -> None:
        if self.max_separation_m <= 0:
            raise ValueError("max_separation_m must be positive")


@dataclass(frozen=True)
class ThinRoadConfig:
    minimum_length_m: float
    weights: NetworkWeightsConfig

    def __post_init__(self) -> None:
        if self.minimum_length_m <= 0:
            raise ValueError("minimum_length_m must be positive")


@dataclass(frozen=True)
class RampConfig:
    cluster_radius_m: float


@dataclass(frozen=True)
class SnapConfig:
    tolerance_m: float

    def __post_init__(self) -> None:
        if self.tolerance_m <= 0:
            raise ValueError("tolerance_m must be positive")


@dataclass(frozen=True)
class RailwayClearanceConfig:
    min_clearance_m: float


@dataclass(frozen=True)
class SimplifyConfig:
    tolerance_m: float


@dataclass(frozen=True)
class SmoothConfig:
    tolerance_m: float


# ---------------------------------------------------------------------------
# Field names
#
# LITERALS, DELIBERATELY. These name columns in data the project does not own -
# NVDB's schema and the published product schema - so by ADR-0011's identifier/value
# test they are values. A different string could be correct here; only the data
# decides.
# ---------------------------------------------------------------------------

ROAD_CLASS = "vegkategori"
RANK = "rank"
MUNICIPALITY = "kommunenummer"
FEATURE_ID = "feature_id"

_MATCH_REPORT_FIELDS = (
    Field(name=FEATURE_ID, type=FieldType.LONG),
    Field(name="reason", type=FieldType.TEXT, length=32),
)


# ---------------------------------------------------------------------------
# Shared helper tools
#
# A helper receives `tb` and a derived scope the way an operation does - derive
# downward. It never learns its own trail, which is what makes it reusable from
# anywhere. Its files land in the CALLING OPERATION's workspace, under the label the
# caller chose.
#
# Helpers are NOT decorated: they are not operations, they never appear in a stage,
# and they take whatever arguments they need.
# ---------------------------------------------------------------------------


def _repair_geometry(*, features: In, output: Out, errors: Out, tb: Toolbox) -> None:
    """Fix self-intersections and null geometry, reporting what it touched.

    TWO PORT CALLS AND NO SCRATCH AT ALL, where the pre-port version needed two
    intermediates. `validate_geometry` writes its findings straight to `errors` and
    `make_valid` writes straight to `output`; there is nothing in between to hold.
    That is the ordinary shape of this change - a port method that names the whole
    operation absorbs the plumbing the tool sequence used to need.
    """
    tb.geometry.validate_geometry(input=features, output=errors)
    tb.geometry.make_valid(input=features, output=output)


def _build_topology(
    *, roads: In, nodes: Out, edges: Out, tb: Toolbox, scratch: ScratchScope
) -> None:
    """Node/edge topology over a line network.

    THE ONLY CALLER OF `GraphOps` IN EITHER WORKED PIPELINE, and the shape Q-C is
    about. The graph work is three lines in the middle, and note what they operate
    on: plain `(int, int)` tuples. `tb.graph` never sees a ScratchHandle, a workspace
    or a geometry - reading the dataset is this helper's job, and deciding which
    fields carry the node ids is a domain question answered here rather than a port
    parameter every adapter would have to honour.

    Called TWICE inside thin_road_network, which is the case that forces
    ScratchScope.child to auto-index: the first call's files render under
    `build_topology__`, the second under `build_topology_reranked__`. Neither
    developer has to know about the other.
    """
    endpoints = scratch("endpoints")
    tb.geometry.extract_vertices(
        input=roads, output=endpoints, position=VertexPosition.BOTH_ENDS
    )

    rows = list(tb.table.read_rows(input=endpoints, fields=(FEATURE_ID,)))
    # BOTH_ENDS emits start then end per feature, so the rows pair off two at a time.
    edge_list = [
        (_node_id(start), _node_id(end)) for start, end in zip(rows[::2], rows[1::2])
    ]
    degrees = tb.graph.degree(edges=edge_list)
    components = tb.graph.connected_components(edges=edge_list)

    tb.table.write_table(
        output=nodes,
        fields=(
            Field(name="node_id", type=FieldType.LONG),
            Field(name="degree", type=FieldType.LONG),
            Field(name="component", type=FieldType.LONG),
        ),
        rows=_node_rows(degrees, components),
    )
    tb.geometry.copy(input=roads, output=edges)


def _node_id(row: Row) -> int:
    """Narrow one attribute to the int `GraphOps` needs.

    ONE GUARD AT THE BOUNDARY, rather than a cast at every read. `Row.attributes` is
    a union over what a cell can hold, so this is where the assumption "feature_id is
    a LONG field" is stated and checked - instead of being silently asserted by a
    `cast` and surfacing later as a TypeError inside a graph algorithm, or worse, as
    a graph built over string keys that never matches anything.
    """
    value = row.attributes[FEATURE_ID]
    if not isinstance(value, int):
        raise TypeError(
            f"{FEATURE_ID} must be a LONG field to serve as a node id, got "
            f"{type(value).__name__}. Topology is built over feature ids, so a TEXT "
            "or null id means the edge list is not the network."
        )
    return value


def _node_rows(
    degrees: Mapping[int, int], components: tuple[frozenset[int], ...]
) -> tuple[Row, ...]:
    """Two `GraphOps` results into rows `write_table` accepts.

    ORDINARY PYTHON OVER PLAIN VALUES, and that is the point of the pure `GraphOps`
    shape: the graph port returned a mapping and a tuple of frozensets, so turning
    them into rows needs no adapter, no fixture and no geometry. Under a
    dataset-aware `GraphOps` this function would not exist and the same logic would
    be inside an adapter, where a test would need a workspace to reach it.
    """
    component_of = {
        node: index for index, part in enumerate(components) for node in part
    }
    return tuple(
        Row(
            attributes={
                "node_id": node,
                "degree": degree,
                "component": component_of.get(node, -1),
            }
        )
        for node, degree in degrees.items()
    )


def _vertex_deltas(
    *, before: In, after: In, output: Out, tb: Toolbox, scratch: ScratchScope
) -> None:
    """Per-vertex displacement between two versions of the same features."""
    vertices_before = scratch("vertices_before")
    vertices_after = scratch("vertices_after")
    paired = scratch("paired", TABLE)

    tb.geometry.extract_vertices(input=before, output=vertices_before)
    tb.geometry.extract_vertices(input=after, output=vertices_after)
    tb.geometry.nearest_neighbors(
        input=vertices_before,
        near=vertices_after,
        output=paired,
        search_radius_m=1000.0,
    )
    tb.table.join_field(
        input=paired,
        key="near_fid",
        join=vertices_after,
        join_key=FEATURE_ID,
        fields=(FEATURE_ID,),
    )
    tb.table.write_table(
        output=output,
        fields=(
            Field(name=FEATURE_ID, type=FieldType.LONG),
            Field(name="delta_m", type=FieldType.DOUBLE),
        ),
        rows=tb.table.read_rows(input=paired),
    )


def _attach_area_attributes(
    *, roads: In, areas: In, output: Out, tb: Toolbox, scratch: ScratchScope
) -> None:
    """arcpy's Identity, decomposed. THE GENERAL FORM, WRITTEN OUT ONCE.

    `Identity` keeps every input feature, splits those that cross an overlay
    boundary, and attaches the overlay's attributes where they coincide. It has no
    OGC counterpart, and it is not a primitive - it is two standard operations and
    one rule about what to do with the remainder:

        intersection    the parts that fall inside an area, carrying its attributes
        difference      the parts that fall in no area, carrying none
        merge           put them back together

    A method named `identity` on the port would have looked like one operation and
    been a vendor composite. Expressed this way, a SQL or dataframe adapter has three
    things it already implements, and the rule that combines them is visible in the
    domain layer where someone can argue with it.

    This recurs across the cartography toolbox - see the module docstring.
    """
    inside = scratch("inside")
    outside = scratch("outside")
    tb.geometry.intersection(input=roads, overlay=areas, output=inside)
    tb.geometry.difference(input=roads, overlay=areas, output=outside)
    tb.geometry.merge(inputs=(inside, outside), output=output)


# ---------------------------------------------------------------------------
# Selection stage
# ---------------------------------------------------------------------------


@operation
def select_source_roads(
    *,
    source: In,
    output: Out,
    geometry_errors: Out,
    config: SelectSourceRoadsConfig,
    tb: Toolbox = NOT_INJECTED,
    scratch: ScratchScope = INJECTED,
) -> None:
    """Filter the N50 product down to the classes that survive at this scale.

    TWO OUTPUTS. `geometry_errors` is not a by-product to be thrown away - the
    hierarchy operation later in this stage reads it to downgrade features whose
    geometry had to be repaired. That is why it is a declared handle rather than
    internal scratch: something else in the stage reads it.
    """
    singlepart = scratch("singlepart")
    selected = scratch("selected")

    tb.geometry.explode_multipart(input=source, output=singlepart)
    tb.geometry.select(
        input=singlepart,
        where=Attr(f"{ROAD_CLASS} <= {config.minimum_class}"),
        output=selected,
    )
    _repair_geometry(features=selected, output=output, errors=geometry_errors, tb=tb)


@operation
def join_admin_attributes(
    *,
    roads: In,
    areas: In,
    output: Out,
    match_report: Out,
    config: JoinAdminConfig,
    tb: Toolbox = NOT_INJECTED,
    scratch: ScratchScope = INJECTED,
) -> None:
    """Merge municipality and county attributes into the road records.

    THIS IS A GENUINE JOIN - attribute data from `areas` ends up inside the output
    records. That is what makes the resulting object multi-origin, and it is the
    contrast with displacement, where roads influence geometry but contribute no data.

    `match_report` is a TABLE recording which roads got no admin match. It is read by
    the next operation, so an unmatched road is ranked conservatively rather than
    silently. `config.search_radius_m` is the fallback reach for a road that falls
    just outside every polygon - a real case along the coastline.
    """
    normalized = scratch("normalized")
    attributed = scratch("attributed")
    unmatched = scratch("unmatched")
    nearest = scratch("nearest", TABLE)

    _normalize_admin_codes(
        areas=areas,
        output=normalized,
        tb=tb,
        scratch=scratch.child("normalize_codes"),
    )
    _attach_area_attributes(
        roads=roads,
        areas=normalized,
        output=attributed,
        tb=tb,
        scratch=scratch.child("attach_areas"),
    )
    tb.geometry.select(
        input=attributed, where=Attr(f"{MUNICIPALITY} IS NULL"), output=unmatched
    )
    tb.geometry.nearest_neighbors(
        input=unmatched,
        near=normalized,
        output=nearest,
        search_radius_m=config.search_radius_m,
    )
    tb.table.join_field(
        input=attributed,
        key=FEATURE_ID,
        join=nearest,
        join_key="input_fid",
        fields=(MUNICIPALITY,),
    )
    tb.geometry.copy(input=attributed, output=output)
    tb.table.write_table(
        output=match_report,
        fields=_MATCH_REPORT_FIELDS,
        rows=tb.table.read_rows(input=unmatched, fields=(FEATURE_ID,)),
    )


def _normalize_admin_codes(
    *, areas: In, output: Out, tb: Toolbox, scratch: ScratchScope
) -> None:
    """Zero-pad municipality codes and drop superseded boundaries."""
    padded = scratch("padded")

    tb.geometry.copy(input=areas, output=padded)
    tb.table.calculate_field(
        input=padded,
        field=MUNICIPALITY,
        expression=f"lpad(cast({MUNICIPALITY} as varchar), 4, '0')",
    )
    tb.geometry.select(input=padded, where=Attr("valid_to IS NULL"), output=output)


@operation
def calculate_road_hierarchy(
    *,
    roads: In,
    geometry_errors: In,
    match_report: In,
    output: Out,
    rank_table: Out,
    config: HierarchyConfig,
    tb: Toolbox = NOT_INJECTED,
    scratch: ScratchScope = INJECTED,
) -> None:
    """Derive the importance ranking that network thinning consumes downstream.

    THREE INPUTS, TWO OUTPUTS, and every one of the five is a declared handle in the
    stage workspace - two of them written by earlier operations in this same stage,
    two of them leaving the stage as objects.

    Reads `config.weights`, the SAME NetworkWeightsConfig instance thin_road_network
    reads, so the ranks assigned here and the ranks spent there cannot disagree.

    Note this writes an OUTPUT rather than mutating `roads` in place. The equivalent
    in the current codebase - calculate_polygon_values - does mutate, declares no
    output, and is therefore invisible in the dependency graph. That is the bug
    validation.check_operations_produce_something exists to catch.
    """
    with_fields = scratch("with_fields")
    penalised = scratch("penalised")
    weights = config.weights

    tb.geometry.copy(input=roads, output=with_fields)
    tb.table.add_field(input=with_fields, field=Field(name=RANK, type=FieldType.DOUBLE))
    tb.table.calculate_field(
        input=with_fields,
        field=RANK,
        expression=(
            f"case when {ROAD_CLASS} = 1 then {weights.arterial} "
            f"when {ROAD_CLASS} = 2 then {weights.collector} "
            f"else {weights.local} end"
        ),
    )
    tb.table.join_field(
        input=with_fields,
        key=FEATURE_ID,
        join=geometry_errors,
        join_key=FEATURE_ID,
        fields=("problem",),
    )
    tb.table.join_field(
        input=with_fields,
        key=FEATURE_ID,
        join=match_report,
        join_key=FEATURE_ID,
        fields=("reason",),
    )
    tb.geometry.copy(input=with_fields, output=penalised)
    tb.table.calculate_field(
        input=penalised,
        field=RANK,
        expression=(
            f"{RANK} - case when problem is not null or reason is not null "
            f"then {config.repaired_geometry_penalty} else 0 end"
        ),
    )
    tb.geometry.copy(input=penalised, output=output)
    tb.table.write_table(
        output=rank_table,
        fields=(
            Field(name=FEATURE_ID, type=FieldType.LONG),
            Field(name=RANK, type=FieldType.DOUBLE),
        ),
        rows=tb.table.read_rows(input=penalised, fields=(FEATURE_ID, RANK)),
    )


# ---------------------------------------------------------------------------
# Network stage
# ---------------------------------------------------------------------------


@operation
def merge_divided_highways(
    *,
    roads: In,
    output: Out,
    merge_report: Out,
    config: MergeDividedConfig,
    tb: Toolbox = NOT_INJECTED,
    scratch: ScratchScope = INJECTED,
) -> None:
    """Collapse dual carriageways into a single centreline.

    `merge_report` names which output centrelines are synthetic. Thinning reads it,
    because a merged centreline must not be judged by the length rule that applies to
    a real one.
    """
    candidates = scratch("candidates")
    paired = scratch("paired", TABLE)

    tb.geometry.select(input=roads, where=Attr("divided = 1"), output=candidates)
    _pair_carriageways(
        roads=candidates,
        output=paired,
        tb=tb,
        scratch=scratch.child("pair_carriageways"),
        separation_m=config.max_separation_m,
    )
    tb.cartographic.collapse_to_centerline(
        input=candidates,
        output=output,
        max_separation_m=config.max_separation_m,
        pairs=paired,
    )
    tb.table.write_table(
        output=merge_report,
        fields=(Field(name=FEATURE_ID, type=FieldType.LONG),),
        rows=tb.table.read_rows(input=paired, fields=(FEATURE_ID,)),
    )


def _pair_carriageways(
    *,
    roads: In,
    output: Out,
    tb: Toolbox,
    scratch: ScratchScope,
    separation_m: float,
) -> None:
    """Match opposing carriageways within a separation tolerance."""
    buffered = scratch("buffered")

    tb.geometry.buffer(input=roads, output=buffered, distance_m=separation_m)
    tb.geometry.spatial_join(target=buffered, join=roads, output=output)


@operation
def thin_road_network(
    *,
    roads: In,
    ranks: In,
    merge_report: In,
    output: Out,
    dropped: Out,
    config: ThinRoadConfig,
    tb: Toolbox = NOT_INJECTED,
    scratch: ScratchScope = INJECTED,
) -> None:
    """Density-based network selection.

    The widest-reaching operation in the pipeline: whether a segment survives depends
    on the connectivity of the network around it, not on the segment itself. This is
    what drives the network stage's large context radius.

    THE HELPER IS CALLED TWICE, which is the case ScratchScope.child auto-indexes.
    Both calls create `nodes` and `edges`; they land under different trail segments
    (`build_topology__` and `build_topology_reranked__`) so neither collides, and the
    ScratchFileManager's manifest maps both rendered names back to their full trails.

    `dropped` is not a diagnostic dead end - resolve_ramps reads it to reinstate ramp
    stubs that connectivity alone would discard. `select_network` makes it a required
    parameter for that reason.
    """
    dissolved = scratch("dissolved")
    nodes = scratch("nodes", TABLE)
    edges = scratch("edges")
    reranked_nodes = scratch("reranked_nodes", TABLE)
    reranked_edges = scratch("reranked_edges")
    weighted = scratch("weighted")

    tb.geometry.dissolve(
        input=roads,
        output=dissolved,
        fields=(ROAD_CLASS,),
        option=DissolveOption.SINGLE_PART,
    )
    _build_topology(
        roads=dissolved,
        nodes=nodes,
        edges=edges,
        tb=tb,
        scratch=scratch.child("build_topology"),
    )
    tb.geometry.copy(input=edges, output=weighted)
    tb.table.join_field(
        input=weighted, key=FEATURE_ID, join=ranks, join_key=FEATURE_ID, fields=(RANK,)
    )
    _build_topology(
        roads=weighted,
        nodes=reranked_nodes,
        edges=reranked_edges,
        tb=tb,
        scratch=scratch.child("build_topology", "reranked"),
    )
    tb.cartographic.select_network(
        input=reranked_edges,
        output=output,
        dropped=dropped,
        minimum_length_m=config.minimum_length_m,
        weight_field=RANK,
        exempt=Attr(f"{FEATURE_ID} in (select {FEATURE_ID} from merge_report)"),
    )


@operation
def resolve_ramps(
    *,
    roads: In,
    dropped: In,
    output_lines: Out,
    output_points: Out,
    config: RampConfig,
    tb: Toolbox = NOT_INJECTED,
    scratch: ScratchScope = INJECTED,
) -> None:
    """Collapse interchange ramps, emitting simplified lines AND junction points.

    TWO OUTPUTS FROM ONE OPERATION, and they end differently. `output_lines`
    continues to the next operation and dies in the pod; `output_points` is named by
    a StageOutput and becomes a published product. One operation, two handles, and
    only one of them ever acquires an identity.
    """
    ramp_candidates = scratch("ramp_candidates")
    reinstated = scratch("reinstated")
    collapsed = scratch("collapsed")

    tb.geometry.select(input=roads, where=Attr("is_ramp = 1"), output=ramp_candidates)
    tb.geometry.merge(inputs=(ramp_candidates, dropped), output=reinstated)
    tb.cartographic.collapse_to_centerline(
        input=reinstated, output=collapsed, max_separation_m=config.cluster_radius_m
    )
    tb.geometry.copy(input=collapsed, output=output_lines)
    _representative_points(
        features=collapsed,
        output=output_points,
        tb=tb,
        scratch=scratch.child("representative_points"),
        cluster_radius_m=config.cluster_radius_m,
    )


def _representative_points(
    *,
    features: In,
    output: Out,
    tb: Toolbox,
    scratch: ScratchScope,
    cluster_radius_m: float,
) -> None:
    """One point per interchange, at a point guaranteed to lie on its ramp cluster.

    `point_on_surface` RATHER THAN `centroid`, and the distinction is load-bearing
    here: an interchange cluster is horseshoe-shaped often enough that its centroid
    falls in the middle of the field it encircles.
    """
    clusters = scratch("clusters")

    tb.geometry.cluster_points(
        input=features, output=clusters, search_radius_m=cluster_radius_m
    )
    tb.geometry.point_on_surface(input=clusters, output=output)


@operation
def snap_to_source_geometry(
    *,
    roads: In,
    reference: In,
    output: Out,
    displacement: Out,
    config: SnapConfig,
    tb: Toolbox = NOT_INJECTED,
    scratch: ScratchScope = INJECTED,
) -> None:
    """Pull generalized centrelines back onto authoritative source positions.

    `reference` is raw NVDB. The operation does not know that data is restricted,
    does not know it arrived as halo context, and does not know it is why the whole
    pipeline runs on-prem. It sees a ScratchHandle.

    `displacement` is the reason SNAP_DISPLACEMENT carries NVDB_ROADS in its ORIGIN
    while THINNED_ROADS does not. Snapping only moves vertices, so no NVDB data ends
    up inside the roads. A displacement measurement, on the other hand, IS NVDB data:
    add it back to the output and you have reconstructed the source positions.
    """
    before_snap = scratch("before_snap")
    snapped = scratch("snapped")

    tb.geometry.copy(input=roads, output=before_snap)
    tb.geometry.snap(
        input=before_snap,
        reference=reference,
        output=snapped,
        tolerance_m=config.tolerance_m,
    )
    tb.geometry.copy(input=snapped, output=output)
    _vertex_deltas(
        before=before_snap,
        after=snapped,
        output=displacement,
        tb=tb,
        scratch=scratch.child("vertex_deltas"),
    )


# ---------------------------------------------------------------------------
# Conflict resolution stage
# ---------------------------------------------------------------------------


@operation
def resolve_road_railway_conflicts(
    *,
    roads: In,
    railway: In,
    output: Out,
    conflicts: Out,
    config: RailwayClearanceConfig,
    tb: Toolbox = NOT_INJECTED,
    scratch: ScratchScope = INJECTED,
) -> None:
    """Displace roads away from railway lines that would collide at this scale.

    `conflicts` records where a displacement was applied and by how much. It is read
    by finalize_road_attributes, which flags the affected features in the published
    schema rather than leaving the edit invisible.

    THE SELECTION IS A PREDICATE VALUE, not a layer plus two mutating calls. The
    pre-port version was `Buffer -> SelectLayerByLocation -> ResolveRoadConflicts`;
    the buffer existed only to give the location selection something to test against,
    and `DWithin` says the same thing without materializing it. That is 616 call
    sites of the same shape in the current codebase. ADR-0001.
    """
    intersecting = scratch("intersecting")

    tb.geometry.select(
        input=roads,
        where=Intersects(railway) | Attr("bridge = 0"),
        output=intersecting,
    )
    tb.cartographic.displace_features(
        input=intersecting,
        output=output,
        barriers=railway,
        minimum_clearance_m=config.min_clearance_m,
        displacement=conflicts,
    )


@operation
def simplify_road_geometry(
    *,
    roads: In,
    output: Out,
    collapsed_points: Out,
    config: SimplifyConfig,
    tb: Toolbox = NOT_INJECTED,
    scratch: ScratchScope = INJECTED,
) -> None:
    """Vertex reduction.

    TWO OUTPUTS BECAUSE THE OPERATOR HAS TWO. Simplification emits a point per
    feature that collapses below the tolerance. Declaring it rather than discarding
    it is what lets the finalize step account for every input feature - which is why
    `simplify` takes `collapsed_points` as a parameter rather than dropping them.
    """
    densified = scratch("densified")

    tb.geometry.densify(
        input=roads, output=densified, max_deviation_m=config.tolerance_m / 10.0
    )
    tb.cartographic.simplify(
        input=densified,
        output=output,
        tolerance_m=config.tolerance_m,
        collapsed_points=collapsed_points,
    )


@operation
def smooth_road_geometry(
    *,
    roads: In,
    barriers: In,
    output: Out,
    config: SmoothConfig,
    tb: Toolbox = NOT_INJECTED,
    scratch: ScratchScope = INJECTED,
) -> None:
    """Bend smoothing, held off the railway.

    `barriers` is the SAME stage input handle that resolve_road_railway_conflicts
    reads. Reading is unconstrained - check_one_writer_per_handle only restricts
    WRITING - so one downloaded input serves both operations at no extra transfer.
    """
    prepared = scratch("prepared")
    segments = scratch("segments")

    tb.geometry.copy(input=roads, output=prepared)
    _split_at_barriers(
        roads=prepared,
        barriers=barriers,
        output=segments,
        tb=tb,
        scratch=scratch.child("split_at_barriers"),
    )
    tb.cartographic.smooth(
        input=segments,
        output=output,
        tolerance_m=config.tolerance_m,
        barriers=barriers,
    )


def _split_at_barriers(
    *, roads: In, barriers: In, output: Out, tb: Toolbox, scratch: ScratchScope
) -> None:
    """Break lines where a barrier crosses, so smoothing cannot pull across one."""
    crossings = scratch("crossings")

    tb.geometry.intersection(input=roads, overlay=barriers, output=crossings)
    tb.geometry.split_at_points(input=roads, points=crossings, output=output)


@operation
def finalize_road_attributes(
    *,
    roads: In,
    ranks: In,
    conflicts: In,
    collapsed_points: In,
    output: Out,
    tb: Toolbox = NOT_INJECTED,
    scratch: ScratchScope = INJECTED,
) -> None:
    """Drop working fields and set the published schema.

    NO CONFIG, and that is the point of `config` being optional: an operation with
    nothing to tune declares nothing to tune. Its OperationCall.parameters is empty,
    and the run manifest records that honestly rather than an empty config object.

    FOUR INPUTS, three of them diagnostics produced earlier: the rank lookup from
    stage 1, the displacement record from the first operation in this stage, and the
    collapse points from the second. Every handle any operation in this pipeline
    writes is read by something or named by a StageOutput - nothing is written and
    abandoned, which is what warn_unused_handles reports on.
    """
    joined = scratch("joined")
    flagged = scratch("flagged")

    tb.geometry.copy(input=roads, output=joined)
    tb.table.join_field(
        input=joined, key=FEATURE_ID, join=ranks, join_key=FEATURE_ID, fields=(RANK,)
    )
    tb.geometry.copy(input=joined, output=flagged)
    tb.table.add_field(input=flagged, field=Field(name="edited", type=FieldType.SHORT))
    tb.table.calculate_field(
        input=flagged,
        field="edited",
        expression=(
            f"case when {FEATURE_ID} in (select {FEATURE_ID} from conflicts) "
            f"or {FEATURE_ID} in (select {FEATURE_ID} from collapsed_points) "
            "then 1 else 0 end"
        ),
    )
    _apply_product_schema(
        features=flagged, output=output, tb=tb, scratch=scratch.child("product_schema")
    )


def _apply_product_schema(
    *, features: In, output: Out, tb: Toolbox, scratch: ScratchScope
) -> None:
    """Field mapping into the published schema. The last thing before upload.

    `keep_unmapped=False` is the default on `map_fields` for this call site: the
    point of the step is to DROP the working fields, and a default that kept them
    would make forgetting silent.
    """
    tb.table.map_fields(
        input=features,
        output=output,
        mapping={
            FEATURE_ID: "objid",
            ROAD_CLASS: "vegkategori",
            RANK: "prioritet",
            "edited": "redigert",
        },
    )
