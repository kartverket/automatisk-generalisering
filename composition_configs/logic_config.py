from dataclasses import dataclass, field
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


@dataclass(frozen=True)
class RbcInitKwargs:
    input_data_structure: list[SymbologyLayerSpec]
    barrier_rules: list[BarrierRule]
    building_unique_name: str
    output_building_polygons: Union[type_defs.GdbFilePath, core_config.InjectIO]
    work_file_manager_config: core_config.WorkFileConfig
