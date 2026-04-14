# Libraries

import arcpy

arcpy.env.overwriteOutput = True

from custom_tools.decorators.timing_decorator import timing_decorator
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10

# ========================
# Main function
# ========================


@timing_decorator
def simplify_and_smooth_polygon(input_fc: str, output_fc: str) -> None:
    """
    Simplifies polygons with the WEIGHTED_AREA algorithm before
    they are smoothed with the BEZIER_INTERPOLATION algorithm.

    Args:
        input_fc (str): The feature class with polygon geometries to be simplified and smoothed
        output_fc (str): The feature class where the result should be saved
    """
    arcpy.cartography.SimplifyPolygon(
        in_features=input_fc,
        out_feature_class=Arealdekke_N10.simplified_polygons__n10_land_use.value,
        algorithm="WEIGHTED_AREA",
        tolerance=5,
        error_option="RESOLVE_ERRORS",
        collapsed_point_option="NO_KEEP",
    )

    arcpy.cartography.SmoothPolygon(
        in_features=Arealdekke_N10.simplified_polygons__n10_land_use.value,
        out_feature_class=output_fc,
        algorithm="BEZIER_INTERPOLATION",
        error_option="RESOLVE_ERRORS",
    )
