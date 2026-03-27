from pydantic.dataclasses import dataclass
from typing import (
    Dict,
    List,
    Optional,
    Tuple,
    Union,
    Any,
)


@dataclass(frozen=True)
class EliminateSmallPolygonsParameters:
    min_area: int
    min_iq_area: int
    max_area_b_iq: int
    exclude: list[str]
    dont_eliminate: list[str]
    spike_size: int
    dont_remove_spikes: list[str]
    integrate_tolerance: float


@dataclass(frozen=True)
class GangSykkelDissolverParameters:
    buffer_distance: int
    length_divide: int


@dataclass(frozen=True)
class LandUseParameters:
    elvFlate: dict
