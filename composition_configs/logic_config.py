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


@dataclass(frozen=True)
class in_symbology_layer:
    unique_name: str
    input_feature: Union[type_defs.GdbFilePath, core_config.InjectIO]
    input_lyrx: str
    grouped_lyrx: bool
    target_layer_name: Optional[str] = None


@dataclass(frozen=True)
class RbcInitKwargs:
    input_data_structure: list[dict[str, Any]]
    output_building_polygons: Union[type_defs.GdbFilePath, core_config.InjectIO]
    work_file_manager_config: core_config.WorkFileConfig
