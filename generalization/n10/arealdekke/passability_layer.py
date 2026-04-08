# Libraries

import arcpy

arcpy.env.overwriteOutput = True

from custom_tools.decorators.timing_decorator import timing_decorator

# ========================
# Main functions
# ========================


@timing_decorator
def create_passability_layer(input_fc: str, output_fc: str) -> None:
    """
    Creates a separate feature class with the geometries not having 'None' as passability.

    Args:
        input_fc (str): Feature class with original land use data having a column named 'fremkommelighet'
        output_fc (str) Feature class to be created with the geometries having 'fremkommelighet' != 'None'
    """
    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(in_features=input_fc, out_layer=land_use_lyr)

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr,
        selection_type="NEW_SELECTION",
        where_clause="fremkommelighet <> 'None'",
    )

    arcpy.management.Dissolve(
        in_features=land_use_lyr,
        out_feature_class=output_fc,
        dissolve_field="fremkommelighet",
        multi_part="SINGLE_PART",
    )
