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
