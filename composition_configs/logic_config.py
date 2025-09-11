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

from composition_configs import core_config, type_defs
from generalization.n100 import building


@dataclass(frozen=True)
class SymbologyLayerSpec:
    unique_name: str
    input_feature: Union[type_defs.GdbFilePath, core_config.InjectIO]
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
    output_building_polygons: Union[type_defs.GdbFilePath, core_config.InjectIO]
    output_collapsed_polygon_points: Union[type_defs.GdbFilePath, core_config.InjectIO]
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

    output_points_after_rbc: Union[type_defs.GdbFilePath, core_config.InjectIO]
    output_polygons_after_rbc: Union[type_defs.GdbFilePath, core_config.InjectIO]

    work_file_manager_config: core_config.WorkFileConfig

    building_symbol_dimension: dict[int, tuple]
    barrier_default: BarrierDefault
    barrier_overrides: Optional[List[BarrierRule]] = None
    map_scale: str = "100000"
