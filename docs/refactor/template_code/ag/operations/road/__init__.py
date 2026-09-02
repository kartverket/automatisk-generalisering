"""TEMPLATE / EXAMPLE — a worked pipeline. Target: `src/ag/operations/road/`.

Road generalization operations and their config types.

In reality this is `generalization/road/operations.py`. SCALE-AGNOSTIC: nothing here
knows about N100. The same `thin_road_network` is used at N50 with a different
config.

TWO HALVES, AND NEITHER IS BOILERPLATE

    the CONFIG    a frozen dataclass per operation, holding everything tunable.
                  Declared here, next to the operation it constrains, because its
                  FIELDS change when the operation changes. Its VALUES change per
                  scale and live in the tuning modules.
    the FUNCTION  In/Out handles, one `config`, and an optional ScratchScope.
                  @operation makes it its own declaration factory.

The hand-written factory twin that used to sit under each function is gone;
@operation reads the operation name, the parameter names, the input/output split and
`wants_scratch` off the signature.

WHY CONFIG IS A SEPARATE OBJECT AND IO IS NOT

They have different reasons to change. `minimum_length_m` gets retuned at N100
without this file changing at all - that is a second axis and it earns its own
record. `roads`, `ranks`, `output` and `dropped` change exactly when the signature
changes, which is the same reason and the same moment, so wrapping them in a second
dataclass would be structure with nothing behind it.

The payoff is concrete: `OperationCall.parameters` is uniformly
`{"config": <frozen dataclass>}`, so a run manifest gets a JSON-able tuning record
per operation from `dataclasses.asdict` with no special-casing. @operation enforces
that shape at import - a stray `minimum_length_m=400` is a TypeError, not a
precedent.

NO `scale` FIELD IN ANY CONFIG. If an operation can read the scale it can branch on
it, and "an operation never knows what scale it is running at" stops being enforced
by anything. The scale selects WHICH config; it is never IN the config.

EVERY OPERATION TAKES ITS INTERNAL FILES FROM THE SCRATCHFILEMANAGER. None of them
constructs a path, a name prefix, or a temp workspace. `scratch("dissolved")` lands
in this operation's own workspace; a helper tool gets `scratch.child("label")` and
never learns its own trail, so the same helper is callable from any operation.

Note what appears NOWHERE in this file: ExternalSource, ProductIdentity, Derived,
location, scale, role, context radius, run id, partition index,
arcpy.env.scratchWorkspace.
"""

from __future__ import annotations

from dataclasses import dataclass

from ag.core.types import DataType
from ag.core.operations import INJECTED, In, Out, ScratchScope, operation

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
# Shared helper tools
#
# A helper receives a scope the way an operation does - derive downward. It never
# learns its own trail, which is what makes it reusable from anywhere. Its files land
# in the CALLING OPERATION's workspace, under the label the caller chose.
#
# Helpers are NOT decorated: they are not operations, they never appear in a stage,
# and they take whatever arguments they need.
# ---------------------------------------------------------------------------


def _repair_geometry(
    *, features: In, output: Out, errors: Out, scratch: ScratchScope
) -> None:
    """Fix self-intersections and null geometry, reporting what it touched."""
    checked = scratch("checked")
    repaired = scratch("repaired")
    raise NotImplementedError(
        f"CheckGeometry -> {checked}, RepairGeometry -> {repaired}, "
        f"then split into {output} and {errors}"
    )


def _build_topology(
    *, roads: In, nodes: Out, edges: Out, scratch: ScratchScope
) -> None:
    """Node/edge topology over a line network.

    Called TWICE inside thin_road_network, which is the case that forces
    ScratchScope.child to auto-index: the first call's files render under
    `build_topology__`, the second under `build_topology_reranked__`. Neither
    developer has to know about the other.
    """
    dangles = scratch("dangles")
    junctions = scratch("junctions")
    raise NotImplementedError(
        f"FeatureVerticesToPoints -> {junctions}, dangle detection -> {dangles}, "
        f"then emit {nodes} and {edges}"
    )


def _vertex_deltas(
    *, before: In, after: In, output: Out, scratch: ScratchScope
) -> None:
    """Per-vertex displacement between two versions of the same features."""
    vertices_before = scratch("vertices_before")
    vertices_after = scratch("vertices_after")
    paired = scratch("paired", TABLE)
    raise NotImplementedError(
        f"FeatureVerticesToPoints on both -> {vertices_before} / {vertices_after}, "
        f"join on (fid, vertex_index) -> {paired}, then summarize into {output}"
    )


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
    _repair_geometry(
        features=selected,
        output=output,
        errors=geometry_errors,
        scratch=scratch.child("repair_geometry"),
    )
    raise NotImplementedError(
        f"MultipartToSinglepart({source}) -> {singlepart}, "
        f"Select(class <= {config.minimum_class}) -> {selected}"
    )


@operation
def join_admin_attributes(
    *,
    roads: In,
    areas: In,
    output: Out,
    match_report: Out,
    config: JoinAdminConfig,
    scratch: ScratchScope = INJECTED,
) -> None:
    """Merge municipality and county attributes into the road records.

    THIS IS A GENUINE JOIN - attribute data from `areas` ends up inside the output
    records. That is what makes the resulting object multi-origin, and it is the
    contrast with displacement, where roads influence geometry but contribute no data.

    `match_report` is a TABLE recording which roads got no admin match. It is read by
    the next operation, so an unmatched road is ranked conservatively rather than
    silently.
    """
    normalized = scratch("normalized", TABLE)
    located = scratch("located")
    joined = scratch("joined")
    _normalize_admin_codes(
        areas=areas, output=normalized, scratch=scratch.child("normalize_codes")
    )
    raise NotImplementedError(
        f"Identity({roads}, {normalized}, {config.search_radius_m}) -> {located}, "
        f"JoinField -> {joined}, then {output} and the unmatched summary "
        f"{match_report}"
    )


def _normalize_admin_codes(*, areas: In, output: Out, scratch: ScratchScope) -> None:
    """Zero-pad municipality codes and drop superseded boundaries."""
    padded = scratch("padded", TABLE)
    current = scratch("current", TABLE)
    raise NotImplementedError(
        f"CalculateField pad -> {padded}, filter valid_to IS NULL -> {current}, "
        f"then {output}"
    )


@operation
def calculate_road_hierarchy(
    *,
    roads: In,
    geometry_errors: In,
    match_report: In,
    output: Out,
    rank_table: Out,
    config: HierarchyConfig,
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
    raise NotImplementedError(
        f"AddField/CalculateField on {roads} weighted by {config.weights} -> "
        f"{with_fields}, downgrade rows named in {geometry_errors} and "
        f"{match_report} by {config.repaired_geometry_penalty} -> {penalised}, "
        f"then {output} and the standalone lookup {rank_table}"
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
    scratch: ScratchScope = INJECTED,
) -> None:
    """Collapse dual carriageways into a single centreline.

    `merge_report` names which output centrelines are synthetic. Thinning reads it,
    because a merged centreline must not be judged by the length rule that applies to
    a real one.
    """
    candidates = scratch("candidates")
    paired = scratch("paired", TABLE)
    _pair_carriageways(
        roads=candidates,
        output=paired,
        scratch=scratch.child("pair_carriageways"),
        separation_m=config.max_separation_m,
    )
    raise NotImplementedError(
        f"Select divided candidates -> {candidates}, MergeDividedRoads using "
        f"{paired} -> {output}, provenance -> {merge_report}"
    )


def _pair_carriageways(
    *, roads: In, output: Out, scratch: ScratchScope, separation_m: float
) -> None:
    """Match opposing carriageways within a separation tolerance."""
    buffered = scratch("buffered")
    overlaps = scratch("overlaps", TABLE)
    raise NotImplementedError(
        f"Buffer({roads}, {separation_m}) -> {buffered}, SpatialJoin -> {overlaps}, "
        f"then the pair list {output}"
    )


@operation
def thin_road_network(
    *,
    roads: In,
    ranks: In,
    merge_report: In,
    output: Out,
    dropped: Out,
    config: ThinRoadConfig,
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
    stubs that connectivity alone would discard.
    """
    dissolved = scratch("dissolved")
    nodes = scratch("nodes")
    edges = scratch("edges")
    reranked_nodes = scratch("reranked_nodes")
    reranked_edges = scratch("reranked_edges")

    _build_topology(
        roads=dissolved,
        nodes=nodes,
        edges=edges,
        scratch=scratch.child("build_topology"),
    )
    _build_topology(
        roads=dissolved,
        nodes=reranked_nodes,
        edges=reranked_edges,
        scratch=scratch.child("build_topology", "reranked"),
    )
    raise NotImplementedError(
        f"Dissolve({roads}) -> {dissolved}, ThinRoadNetwork over {edges} weighted by "
        f"{ranks} and {config.weights}, exempting rows in {merge_report} and "
        f"honouring {config.minimum_length_m}m -> {output} and {dropped}"
    )


@operation
def resolve_ramps(
    *,
    roads: In,
    dropped: In,
    output_lines: Out,
    output_points: Out,
    config: RampConfig,
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
    _representative_points(
        features=collapsed,
        output=output_points,
        scratch=scratch.child("representative_points"),
        cluster_radius_m=config.cluster_radius_m,
    )
    raise NotImplementedError(
        f"Select ramps from {roads} -> {ramp_candidates}, re-add stubs from "
        f"{dropped} -> {reinstated}, CollapseDualLines -> {collapsed}, "
        f"then {output_lines}"
    )


def _representative_points(
    *, features: In, output: Out, scratch: ScratchScope, cluster_radius_m: float
) -> None:
    """One point per interchange, at the centroid of its ramp cluster."""
    clusters = scratch("clusters")
    midpoints = scratch("midpoints")
    raise NotImplementedError(
        f"FindPointClusters({features}, {cluster_radius_m}) -> {clusters}, "
        f"FeatureToPoint -> {midpoints}, then {output}"
    )


@operation
def snap_to_source_geometry(
    *,
    roads: In,
    reference: In,
    output: Out,
    displacement: Out,
    config: SnapConfig,
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
    _vertex_deltas(
        before=before_snap,
        after=snapped,
        output=displacement,
        scratch=scratch.child("vertex_deltas"),
    )
    raise NotImplementedError(
        f"CopyFeatures({roads}) -> {before_snap}, "
        f"Snap to {reference} at {config.tolerance_m}m -> {snapped}, then {output}"
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
    scratch: ScratchScope = INJECTED,
) -> None:
    """Displace roads away from railway lines that would collide at this scale.

    `conflicts` records where a displacement was applied and by how much. It is read
    by finalize_road_attributes, which flags the affected features in the published
    schema rather than leaving the edit invisible.
    """
    clearance_zone = scratch("clearance_zone")
    intersecting = scratch("intersecting")
    displaced = scratch("displaced")
    raise NotImplementedError(
        f"Buffer({railway}, {config.min_clearance_m}) -> {clearance_zone}, "
        f"SelectLayerByLocation({roads}) -> {intersecting}, ResolveRoadConflicts -> "
        f"{displaced}, then {output} and {conflicts}"
    )


@operation
def simplify_road_geometry(
    *,
    roads: In,
    output: Out,
    collapsed_points: Out,
    config: SimplifyConfig,
    scratch: ScratchScope = INJECTED,
) -> None:
    """Vertex reduction.

    TWO OUTPUTS BECAUSE THE GP TOOL HAS TWO. arcpy.cartography.SimplifyLine emits a
    point feature class for features that collapse below the tolerance. Declaring it
    rather than discarding it is what lets the finalize step account for every input
    feature.
    """
    densified = scratch("densified")
    simplified = scratch("simplified")
    raise NotImplementedError(
        f"Densify({roads}) -> {densified}, SimplifyLine at {config.tolerance_m}m -> "
        f"{simplified} plus collapse points, then {output} and {collapsed_points}"
    )


@operation
def smooth_road_geometry(
    *,
    roads: In,
    barriers: In,
    output: Out,
    config: SmoothConfig,
    scratch: ScratchScope = INJECTED,
) -> None:
    """Bend smoothing, held off the railway.

    `barriers` is the SAME stage input handle that resolve_road_railway_conflicts
    reads. Reading is unconstrained - check_one_writer_per_handle only restricts
    WRITING - so one downloaded input serves both operations at no extra transfer.
    """
    prepared = scratch("prepared")
    segments = scratch("segments")
    _split_at_barriers(
        roads=prepared,
        barriers=barriers,
        output=segments,
        scratch=scratch.child("split_at_barriers"),
    )
    raise NotImplementedError(
        f"CopyFeatures({roads}) -> {prepared}, SmoothLine over {segments} at "
        f"{config.tolerance_m}m -> {output}"
    )


def _split_at_barriers(
    *, roads: In, barriers: In, output: Out, scratch: ScratchScope
) -> None:
    """Break lines where a barrier crosses, so smoothing cannot pull across one."""
    crossings = scratch("crossings")
    split = scratch("split")
    raise NotImplementedError(
        f"Intersect({roads}, {barriers}) -> {crossings}, SplitLineAtPoint -> "
        f"{split}, then {output}"
    )


@operation
def finalize_road_attributes(
    *,
    roads: In,
    ranks: In,
    conflicts: In,
    collapsed_points: In,
    output: Out,
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
    _apply_product_schema(
        features=flagged, output=output, scratch=scratch.child("apply_product_schema")
    )
    raise NotImplementedError(
        f"JoinField({roads}, {ranks}) -> {joined}, flag rows named in {conflicts} "
        f"and {collapsed_points} -> {flagged}"
    )


def _apply_product_schema(*, features: In, output: Out, scratch: ScratchScope) -> None:
    """Field mapping into the published schema. The last thing before upload."""
    mapped = scratch("mapped")
    typed = scratch("typed")
    raise NotImplementedError(
        f"FieldMapping over {features} -> {mapped}, type coercion -> {typed}, "
        f"then {output}"
    )
