# Libraries

from pathlib import Path

from custom_tools.general_tools.param_utils import initialize_params
from generalization.n10.arealdekke.parameters.parameter_dataclasses import (
    EliminateSmallPolygonsParameters,
    GangSykkelDissolverParameters,
    MinArea,
    MinWidth,
)

# ========================
# Constants
# ========================


PARAMS_PATH = Path(__file__).parent.parent / "parameters" / "parameters.yml"
AREA_CLASS = "MinArea"
WIDTH_CLASS = "MinWidth"

MAPPING = {
    "EliminateSmallPolygons": EliminateSmallPolygonsParameters,
    "GangSykkelDissolver": GangSykkelDissolverParameters,
}

PARAMETERTYPE = EliminateSmallPolygonsParameters | GangSykkelDissolverParameters


# ========================
# Functionality
# ========================


def get_min_width(
    map_scale: str,
    target: str = None,
) -> int | MinWidth:
    """
    Extracts the minimum width for the target land use from the parameters.yml file in the parameters folder.

    Args:
        map_scale (str): Scale for current map
        target (str, optional): Name of land use type to consider. Defaults to None

    Returns:
        int | MinWidth: Minimum width for relevant land use type
    """
    scale_parameters = initialize_params(
        params_path=PARAMS_PATH,
        class_name=WIDTH_CLASS,
        map_scale=map_scale,
        dataclass=MinWidth,
    )
    if target:
        return scale_parameters.features[target]
    return scale_parameters


def get_min_area(
    map_scale: str,
    target: str = None,
) -> int | MinArea:
    """
    Extracts the minimum area for the target land use from the parameters.yml file in the parameters folder.

    Args:
        map_scale (str): Scale for current map
        target (str, optional): Name of land use type to consider. Defaults to None

    Returns:
        int | MinArea: Minimum area for relevant land use type
    """
    scale_parameters = initialize_params(
        params_path=PARAMS_PATH,
        class_name=AREA_CLASS,
        map_scale=map_scale,
        dataclass=MinArea,
    )
    if target:
        return scale_parameters.features[target]
    return scale_parameters


def initialize_parameters(map_scale: str, class_name: str) -> PARAMETERTYPE:
    """
    Initializes parameter objects from the parameters.yml file.

    Args:
        map_scale (str): Scale for the current map
        class_name (str): Name of the parameter class to initialize

    Returns:
        Parameter dataclass instance:
            Initialized parameter object for the specified class and map scale
    """
    scale_parameters = initialize_params(
        params_path=PARAMS_PATH,
        class_name=class_name,
        map_scale=map_scale,
        dataclass=MAPPING[class_name],
    )
    return scale_parameters
