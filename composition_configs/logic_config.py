from dataclasses import dataclass, field
import os
from typing import (
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    TypeAlias,
    Union,
    Any,
    Callable,
    Mapping,
    Sequence,
)
from enum import Enum

from composition_configs import core_config, type_defs, io_types
from file_manager import work_file_manager

RasterPathList: TypeAlias = tuple[type_defs.RasterFilePath, ...]


@dataclass(frozen=True)
class SymbologyLayerSpec:
    unique_name: str
    input_feature: io_types.GdbIOArg
    input_lyrx: str
    grouped_lyrx: bool
    target_layer_name: Optional[str] = None


@dataclass(frozen=True)
class BarrierRule:
    name: str
    gap_meters: int
    use_turn_orientation: bool = False


@dataclass(frozen=True, slots=True)
class BarrierDefault:
    gap_meters: int
    use_turn_orientation: bool = False


@dataclass(frozen=True, slots=True)
class BarrierOverride:
    gap_meters: Optional[int] = None
    use_turn_orientation: Optional[bool] = None


@dataclass(frozen=True)
class RbcPolygonInitKwargs:
    input_data_structure: list[SymbologyLayerSpec]
    output_building_polygons: io_types.GdbIOArg
    output_collapsed_polygon_points: io_types.GdbIOArg
    work_file_manager_config: core_config.WorkFileConfig

    building_unique_name: str
    barrier_default: BarrierDefault
    barrier_overrides: Optional[List[BarrierRule]] = None


@dataclass(frozen=True)
class RbcPointsInitKwargs:
    input_data_structure: List[SymbologyLayerSpec]

    building_points_unique_name: str
    building_polygons_unique_name: str

    building_gap_distance_m: int

    output_points_after_rbc: io_types.GdbIOArg
    output_polygons_after_rbc: io_types.GdbIOArg

    work_file_manager_config: core_config.WorkFileConfig

    building_symbol_dimension: dict[int, tuple]
    barrier_default: BarrierDefault
    barrier_overrides: Optional[List[BarrierRule]] = None
    map_scale: str = "100000"


@dataclass(frozen=True)
class BegrensningskurveLandWaterKwargs:
    input_begrensningskurve: io_types.GdbIOArg
    input_land_cover_features: io_types.GdbIOArg
    output_begrensningskurve: io_types.GdbIOArg
    water_feature_buffer_width: int
    water_barrier_buffer_width: int
    work_file_manager_config: core_config.WorkFileConfig


@dataclass(frozen=True)
class LineToBufferSymbologyKwargs:
    input_line: io_types.GdbIOArg
    output_line: io_types.GdbIOArg

    sql_selection_query: dict

    work_file_manager_config: core_config.WorkFileConfig

    buffer_distance_factor: Union[int, float] = 1
    buffer_distance_addition: Union[int, float] = 0


@dataclass(frozen=True)
class BufferDisplacementKwargs:
    input_road_line: io_types.GdbIOArg
    input_building_points: io_types.GdbIOArg
    input_line_barriers: Dict[str, Any]

    output_building_points: io_types.GdbIOArg

    sql_selection_query: dict
    building_symbol_dimension: Dict[int, Tuple[int, int]]

    displacement_distance_m: int

    work_file_manager_config: core_config.WorkFileConfig


@dataclass(frozen=True)
class ThinRoadNetworkKwargs:
    input_road_line: io_types.GdbIOArg
    output_road_line: io_types.GdbIOArg
    work_file_manager_config: core_config.WorkFileConfig
    minimum_length: int
    invisibility_field_name: str
    hierarchy_field_name: str
    special_selection_sql: str | None = None


@dataclass(frozen=True)
class RemoveRoadTrianglesKwargs:
    input_line_feature: io_types.GdbIOArg
    work_file_manager_config: core_config.WorkFileConfig
    maximum_length: int
    root_file: io_types.GdbIOArg
    output_processed_feature: io_types.GdbIOArg
    hierarchy_field: str = None
    write_to_memory: bool = False
    keep_work_files: bool = False


@dataclass(frozen=True)
class RemoveRoadTrianglesRunParams:
    scale: str


@dataclass(frozen=True)
class CollapseRoadDetailsKwargs:
    input_road_line: io_types.GdbIOArg
    output_road_line: io_types.GdbIOArg
    merge_distnace_m: int
    collapse_field_name: Optional[str] = None


@dataclass(frozen=True)
class RrcInitKwargs:
    input_data_structure: List[SymbologyLayerSpec]
    work_file_manager_config: core_config.WorkFileConfig

    primary_road_unique_name: str

    output_road_feature: io_types.GdbIOArg
    output_displacement_feature: io_types.GdbIOArg

    map_scale: str = "100000"
    hierarchy_field: str = "hierarchy"


@dataclass(frozen=True)
class DissolveInitKwargs:
    """
    Configuration for DissolveWithIntersections.

    input_line_feature: path or InjectIO to the input line feature
    output_processed_feature: path or InjectIO for the final merged intersections (or single)
    work_file_manager_config: WorkFileManager behavior (root_file, in-memory, keep_files)
    dissolve_fields: optional list of fields to dissolve on; if None -> dissolve all (single-part)
    sql_expressions: optional list of SQL where-clauses to split/segment, each produces its own FTL result
    """

    input_line_feature: io_types.GdbIOArg
    output_processed_feature: io_types.GdbIOArg
    work_file_manager_config: core_config.WorkFileConfig

    dissolve_fields: Optional[List[str]] = None
    sql_expressions: Optional[List[str]] = None


@dataclass(frozen=True)
class ConnectRiverLinesKwargs:
    work_file_manager_config: core_config.WorkFileConfig
    output_processed_feature: io_types.GdbIOArg
    basin: str


@dataclass(frozen=True)
class RemoveCyclesKwargs:
    input_line_feature: io_types.GdbIOArg
    work_file_manager_config: core_config.WorkFileConfig
    output_processed_feature: io_types.GdbIOArg


@dataclass(frozen=True)
class RiverStrahlerKwargs:
    input_line_feature: io_types.GdbIOArg
    work_file_manager_config: core_config.WorkFileConfig
    output_processed_feature: io_types.GdbIOArg
    havflate_feature: io_types.GdbIOArg


class EditMethod(str, Enum):
    AUTO = "auto"
    FORCED_SNAP = "forced_snap"
    FORCED_EXTEND = "forced_extend"


class ConnectivityScope(str, Enum):
    NONE = "none"
    DIRECT_CONNECTION = "direct"
    INPUT_LINES = "input_lines"
    ONE_DEGREE = "one_degree"
    TRANSITIVE = "transitive"


class LineConnectivityMode(str, Enum):
    ENDPOINTS = "endpoints"
    INTERSECT = "intersect"


class AngleTargetMode(str, Enum):
    AUTO = "auto"
    FORCE_NON_LINE = "force_non_line"


@dataclass(frozen=True)
class BestFitWeightsConfig:
    """
    Normalized weights for composite best-fit candidate scoring.

    Each weight is a non-negative scalar. The composite score for a candidate is:

        score = distance * norm_dist + angle * norm_angle + z * norm_z

    where norm_* are each normalized to [0, 1] relative to their natural range
    (distance: gap_tolerance_meters; angle: 90 degrees; z: reserved).

    distance: weight applied to normalized distance. Default 1.0.
    angle: weight applied to normalized angle difference. Has no scoring effect unless
        FillLineGapsAngleConfig is active. Default 0.0.
    z: weight applied to normalized Z difference. Has no scoring effect unless
        FillLineGapsZConfig is active. Default 0.0.
    """

    distance: float = 1.0
    angle: float = 0.0
    z: float = 0.0


@dataclass(frozen=True)
class FillLineGapsOutputConfig:
    """
    Optional diagnostic and metadata outputs produced alongside the main result.

    line_changes_output: path to write a feature class recording each connector added.
        Each row carries gap_dist_m and gap_source fields. None disables this output.
    write_output_metadata: when True, appends a metadata summary record to the output
        feature class after the run completes.
    candidate_connections_output: path to write the full candidate diagnostics feature
        class (one POLYLINE row per evaluated dangle/target pair, with scoring detail).
        None disables candidate collection entirely, skipping all diagnostic assembly.
    """

    line_changes_output: Optional[str] = None
    write_output_metadata: bool = False
    candidate_connections_output: Optional[str] = None


@dataclass(frozen=True)
class FillLineGapsAngleConfig:
    """
    Angle-based candidate filtering, scoring, and directional behaviour.

    angle_block_threshold_degrees: candidates whose connector-to-source angle exceeds
        this threshold are rejected at Step 1b as illegal. None disables the angle gate.
    angle_extra_dangle_threshold_degrees: relaxed angle threshold applied to dangle-pair
        candidates that qualify for the edge-case distance bonus. None falls back to
        angle_block_threshold_degrees.
    angle_local_half_window_m: half-window in metres passed to local_line_angle_at_xy
        when computing the source angle at a dangle endpoint.
    connect_to_features_angle_mode: optional per-dataset override controlling how angles
        are measured for external target features. Keys are the original
        connect_to_features path or its dataset_key. Values are AngleTargetMode members.
    lines_are_directed: when True the caller guarantees all input lines are pre-oriented
        (flow runs start to end). Angle comparisons use directional difference (0 to 180
        degrees) and src_target_diff as the primary metric for line-to-line pairs.
        Requires best_fit_weights.angle > 0 on FillLineGapsConfig (enforced at init).
    dangle_pair_apply_connector_diff: when True and lines_are_directed is also True,
        the angle metric for a valid end-to-start dangle pair uses
        max(src_target_diff, src_connector_diff) instead of src_target_diff alone.
        This penalises candidates whose connector direction is poor even when target
        alignment is good. Has no effect when lines_are_directed is False.
    """

    angle_block_threshold_degrees: Optional[float] = None
    angle_extra_dangle_threshold_degrees: Optional[float] = None
    angle_local_half_window_m: float = 2.0
    connect_to_features_angle_mode: Optional[dict[str, AngleTargetMode]] = None
    lines_are_directed: bool = False
    dangle_pair_apply_connector_diff: bool = False


@dataclass(frozen=True)
class FillLineGapsZConfig:
    """
    Z/elevation-based candidate filtering and scoring.

    raster_paths: ordered tuple of pre-scoped raster tile paths (e.g. from
        find_rasters_for_vector_extent). FillLineGaps builds RasterHandle objects from
        these at run() start. None disables all Z-based logic including z_drop_threshold.
    z_drop_threshold: legality gate on Z drop along a candidate connector. A candidate is
        rejected when (end_z - start_z) > z_drop_threshold. None disables the gate.
        Set to 0 to reject any uphill candidate; set to -10 to require a drop of at
        least 10 m.
    """

    raster_paths: Optional[RasterPathList] = None
    z_drop_threshold: Optional[float] = None


@dataclass(frozen=True)
class FillLineGapsCrossingConfig:
    """
    Connector crossing rejection and impassable barrier layer settings.

    reject_crossing_connectors: when True, candidates whose connector geometry crosses
        an existing feature (self-lines or connect_to_features) are rejected at Step 1a.
        Accepted connectors are also checked against each other during Kruskal selection,
        and resnap captures are re-checked after their final geometry is resolved.
        Requires crossing_check_spatial_reference.
    crossing_check_spatial_reference: spatial reference used to construct temporary
        connector geometries for crossing checks. Accepts an integer WKID or a .prj
        file path (passed directly to arcpy.SpatialReference()). Required when
        reject_crossing_connectors is True or barrier_layers is set.
    barrier_layers: feature layers that act as impassable barriers. Any candidate whose
        trimmed connector crosses one of these layers is rejected at Step 1a regardless
        of the reject_crossing_connectors setting. These layers are never used as snap
        targets. Requires crossing_check_spatial_reference.
    """

    reject_crossing_connectors: bool = False
    crossing_check_spatial_reference: "int | str | None" = None
    barrier_layers: "list[str] | None" = None

    def __post_init__(self) -> None:
        if (
            self.reject_crossing_connectors or self.barrier_layers is not None
        ) and self.crossing_check_spatial_reference is None:
            raise ValueError(
                "crossing_check_spatial_reference is required when "
                "reject_crossing_connectors is True or barrier_layers is set"
            )


@dataclass(frozen=True)
class FillLineGapsConnectivityConfig:
    """
    Controls how the tool detects existing connections between line endpoints.

    An existing connection between two endpoints means they should not receive a new
    connector, even if their distance is within gap_tolerance_meters.

    connectivity_scope: determines how far the tool traverses the endpoint graph when
        deciding whether two endpoints are already connected. NONE skips the check;
        DIRECT_CONNECTION considers only the immediate pair; INPUT_LINES, ONE_DEGREE,
        and TRANSITIVE widen the traversal progressively.
    connectivity_tolerance_meters: snapping tolerance used when building the endpoint
        connectivity graph.
    line_connectivity_mode: controls which part of each line participates in connectivity
        detection. ENDPOINTS checks only start/end vertices; INTERSECT includes any
        geometric intersection along the line.
    """

    connectivity_scope: ConnectivityScope = ConnectivityScope.DIRECT_CONNECTION
    connectivity_tolerance_meters: float = 0.02
    line_connectivity_mode: LineConnectivityMode = LineConnectivityMode.ENDPOINTS


@dataclass(frozen=True)
class FillLineGapsAdvancedConfig:
    """
    Residual tuning parameters that do not belong to a specific themed sub-config.

    edit_method: controls how connectors are applied to input lines. AUTO selects snap
        or extend based on geometry; FORCED_SNAP always snaps; FORCED_EXTEND always
        extends.
    increased_tolerance_edge_case_distance_meters: additional distance added to
        gap_tolerance_meters when searching for dangle-pair candidates that qualify for
        the edge-case bonus. Zero disables the expanded search radius.
    require_mutual_dangle_preference_for_bonus: when True the edge-case distance bonus
        is only applied when both source and target dangles mutually prefer each other's
        parent line. When False (default) the angle gate
        (angle_extra_dangle_threshold_degrees) is the sole guard.
    """

    edit_method: EditMethod = EditMethod.AUTO
    increased_tolerance_edge_case_distance_meters: int = 0
    require_mutual_dangle_preference_for_bonus: bool = False


@dataclass(frozen=True)
class FillLineGapsConfig:
    """
    Top-level configuration for FillLineGaps.

    input_lines: path to the input line feature class.
    output_lines: path where the edited gap-filled line feature class will be written.
    work_file_manager_config: controls scratch/work file behaviour (root_file,
        write_to_memory, keep_files).
    gap_tolerance_meters: maximum connector length in metres; candidates beyond this
        distance are never considered.
    connect_to_features: optional list of external feature class paths that act as
        additional snap targets. When provided, dangles on input_lines may connect to
        these features as well as to other input_lines dangles.
    fill_gaps_on_self: when True (default) dangles on input_lines are allowed to connect
        to other dangles on input_lines. Set to False only when connect_to_features
        provides all intended targets.
    best_fit_weights: composite scoring weights controlling how distance, angle, and Z
        contribute to candidate ranking. The default (distance=1.0, angle=0.0, z=0.0)
        ranks purely by nearest distance. Angle and Z weights have no scoring effect
        unless the corresponding sub-configs are also provided.
    output_config: optional diagnostic and metadata output settings.
    angle_config: optional angle filtering, scoring, and directional behaviour.
    z_config: optional Z/elevation filtering and scoring.
    crossing_config: optional connector crossing rejection and barrier layer settings.
    connectivity_config: optional connectivity detection settings.
    advanced_config: residual tuning parameters (edit method and edge-case bonus).
    """

    input_lines: str
    output_lines: str
    work_file_manager_config: core_config.WorkFileConfig
    gap_tolerance_meters: int
    connect_to_features: Optional[list[str]] = None
    fill_gaps_on_self: bool = True
    best_fit_weights: BestFitWeightsConfig = field(default_factory=BestFitWeightsConfig)
    output_config: FillLineGapsOutputConfig = field(
        default_factory=FillLineGapsOutputConfig
    )
    angle_config: FillLineGapsAngleConfig = field(
        default_factory=FillLineGapsAngleConfig
    )
    z_config: FillLineGapsZConfig = field(default_factory=FillLineGapsZConfig)
    crossing_config: FillLineGapsCrossingConfig = field(
        default_factory=FillLineGapsCrossingConfig
    )
    connectivity_config: FillLineGapsConnectivityConfig = field(
        default_factory=FillLineGapsConnectivityConfig
    )
    advanced_config: FillLineGapsAdvancedConfig = field(
        default_factory=FillLineGapsAdvancedConfig
    )


class LineAngleMode(str, Enum):
    WHOLE_LINE = "whole_line"
    START_SEGMENT = "start_segment"
    END_SEGMENT = "end_segment"
    BOTH_ENDPOINT_SEGMENTS = "both_endpoint_segments"
    START_TO_MIDPOINT = "start_to_midpoint"
    END_TO_MIDPOINT = "end_to_midpoint"
    BOTH_ENDPOINT_TO_MIDPOINT = "both_endpoint_to_midpoint"
    ALL_ANGLES = "all_angles"


@dataclass(frozen=True)
class AngleToolConfig:
    input_lines: str
    angle_modes: tuple[LineAngleMode, ...]
    output_lines: Optional[str] = None
    field_name_by_mode: Optional[dict[LineAngleMode, str]] = None
    return_results: bool = True
    write_fields: bool = False


class LineEndpointMode(str, Enum):
    START_POINT = "start_point"
    END_POINT = "end_point"
    BOTH_ENDPOINTS = "both_endpoints"


@dataclass(frozen=True)
class LineEndpointFieldNameConfig:
    start_x: str = "start_x"
    start_y: str = "start_y"
    end_x: str = "end_x"
    end_y: str = "end_y"


@dataclass(frozen=True)
class LineEndpointToolConfig:
    input_lines: str
    endpoint_modes: tuple[LineEndpointMode, ...]
    output_lines: Optional[str] = None
    field_names: LineEndpointFieldNameConfig = field(
        default_factory=LineEndpointFieldNameConfig
    )
    return_results: bool = True
    write_fields: bool = False


class LineZValueMode(str, Enum):
    START_POINT = "start_point"
    END_POINT = "end_point"
    BOTH_ENDPOINTS = "both_endpoints"


class LineZOrientMode(str, Enum):
    INDIVIDUAL = "individual"
    NETWORK = "network"


@dataclass(frozen=True)
class LineZValueFieldNameConfig:
    start_z: str = "start_z"
    end_z: str = "end_z"


@dataclass(frozen=True)
class LineZValueToolConfig:
    input_lines: str
    input_rasters: tuple[str, ...]
    endpoint_modes: tuple[LineZValueMode, ...]
    output_lines: Optional[str] = None
    field_names_per_raster: Optional[tuple[LineZValueFieldNameConfig, ...]] = None
    # If None and one raster: defaults ("start_z", "end_z").
    # If None and multiple rasters: auto "start_z_1", "end_z_1", "start_z_2", "end_z_2" …
    return_results: bool = True
    write_fields: bool = False


@dataclass(frozen=True)
class LineZOrientConfig:
    input_lines: str
    raster_paths: RasterPathList
    orientation_mode: LineZOrientMode = LineZOrientMode.INDIVIDUAL
    min_anchor_z_drop_meters: float = 0.5
    min_confident_flip_meters: Optional[float] = None
    connectivity_tolerance_meters: float = 0.02
