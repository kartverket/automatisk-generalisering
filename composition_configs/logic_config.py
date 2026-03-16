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

# Ordered collection of pre-scoped raster tile paths.
# Produced by find_rasters_for_vector_extent; consumed by FillLineGapsAdvancedConfig
# and LineZValueToolConfig.
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

    Default (distance=1.0, angle=0.0, z=0.0) produces pure nearest-distance ranking,
    identical to the behavior before angle weighting was introduced.
    """

    distance: float = 1.0
    angle: float = 0.0
    z: float = 0.0


@dataclass(frozen=True)
class FillLineGapsAdvancedConfig:
    fill_gaps_on_self: bool = True
    line_changes_output: Optional[str] = None
    write_output_metadata: bool = False
    candidate_connections_output: Optional[str] = None

    increased_tolerance_edge_case_distance_meters: int = 0
    edit_method: EditMethod = EditMethod.AUTO
    connectivity_scope: ConnectivityScope = ConnectivityScope.DIRECT_CONNECTION
    connectivity_tolerance_meters: float = 0.02
    line_connectivity_mode: LineConnectivityMode = LineConnectivityMode.ENDPOINTS

    # ----------------------------
    # Angle layer
    # ----------------------------
    angle_block_threshold_degrees: Optional[float] = None
    angle_extra_dangle_threshold_degrees: Optional[float] = None

    # 0..1, prefer line alignment a bit more than connector transition
    line_alignment_weight: float = 0.6

    best_fit_weights: BestFitWeightsConfig = field(
        default_factory=BestFitWeightsConfig
    )

    # Passed to local_line_angle_at_xy(desired_half_window_m=...)
    angle_local_half_window_m: float = 2.0

    # Optional overrides per external target (connect_to_features)
    # Keying recommendation:
    # - support keys by original connect_to_features path OR by dataset_key(path)
    connect_to_features_angle_mode: Optional[dict[str, AngleTargetMode]] = None

    # ----------------------------
    # Z / elevation layer
    # ----------------------------

    # Pre-scoped raster tile paths (e.g. from find_rasters_for_vector_extent).
    # FillLineGaps builds RasterHandle objects from these at run() start.
    # None disables all Z-based logic.
    raster_paths: Optional[RasterPathList] = None

    # Legality gate on Z drop along a candidate connector.
    # A candidate is illegal when (end_z - start_z) > z_drop_threshold.
    # None disables the gate.
    #   0   → candidate must run downhill or flat
    #  -10  → candidate must drop more than 10 m
    z_drop_threshold: Optional[float] = None


@dataclass(frozen=True)
class FillLineGapsConfig:
    input_lines: str
    output_lines: str
    work_file_manager_config: core_config.WorkFileConfig
    gap_tolerance_meters: int
    connect_to_features: Optional[list[str]] = None
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
