# Libraries

from pathlib import Path

from custom_tools.general_tools.param_utils import initialize_params
from generalization.n10.arealdekke.parameters.parameter_dataclasses import (
    MinArea,
    MinWidth,
)

# ========================
# Constants
# ========================


PARAMS_PATH = Path(__file__).parent.parent / "parameters" / "parameters.yml"
AREA_CLASS = "MinArea"
WIDTH_CLASS = "MinWidth"


# ========================
# Functionality
# ========================


def get_min_width(
    map_scale: str,
    target: str,
) -> int:
    """
    Extracts the minimum width for the target land use from the parameters.yml file in the parameters folder.

    Args:
        map_scale (str): Scale for current map
        target (str): Name of land use type to consider

    Returns:
        int: Minimum width for relevant land use type
    """
    scale_parameters = initialize_params(
        params_path=PARAMS_PATH,
        class_name=WIDTH_CLASS,
        map_scale=map_scale,
        dataclass=MinWidth,
    )

    return scale_parameters.features[target]


def get_min_area(
    map_scale: str,
    target: str,
) -> int:
    """
    Extracts the minimum area for the target land use from the parameters.yml file in the parameters folder.

    Args:
        map_scale (str): Scale for current map
        target (str): Name of land use type to consider

    Returns:
        int: Minimum area for relevant land use type
    """
    scale_parameters = initialize_params(
        params_path=PARAMS_PATH,
        class_name=AREA_CLASS,
        map_scale=map_scale,
        dataclass=MinArea,
    )

    return scale_parameters.features[target]
