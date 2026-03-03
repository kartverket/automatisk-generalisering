from dataclasses import dataclass, field
import os
from typing import (
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    Union,
    Any,
    Callable,
    Mapping,
    Sequence,
)
from enum import Enum

from composition_configs import core_config, type_defs, io_types
from file_manager import work_file_manager


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


@dataclass(frozen=True)
class FillLineGapsAdvancedConfig:
    fill_gaps_on_self: bool = True
    line_changes_output: Optional[str] = None

    # Extra meters added ONLY when considering dangle→dangle candidates.
    # Effective dangle→dangle cap = gap_tolerance_meters + extra.
    # Use 0 to disable expanded dangle pairing.
    increased_tolerance_edge_case_distance_meters: int = 0
    # Auto uses snap on dangle pairs and extend for all others
    edit_method: EditMethod = EditMethod.AUTO
    # decide if lines inherit illegal targets of connected lines
    connectivity_scope: ConnectivityScope = ConnectivityScope.DIRECT_CONNECTION
    connectivity_tolerance_meters: float = 0.02
    line_connectivity_mode: LineConnectivityMode = LineConnectivityMode.ENDPOINTS


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
