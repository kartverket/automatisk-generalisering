from pydantic.dataclasses import dataclass


@dataclass(frozen=True)
class MinArea:
    features: dict[str, int]


@dataclass(frozen=True)
class MinWidth:
    features: dict[str, int]


@dataclass(frozen=True)
class EliminateSmallPolygonsParameters:
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
