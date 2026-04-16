# Libraries

import arcpy

arcpy.env.overwriteOutput = True

from custom_tools.decorators.timing_decorator import timing_decorator
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10

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
        dissolve_field=["arealdekke", "fremkommelighet"],
        multi_part="SINGLE_PART",
    )


@timing_decorator
def postprocess_passability_layer(final_fc: str, passability_fc: str) -> None:
    """
    Post-processes the passability layer by checking for match with geometries in the final feature class.

    Args:
        final_fc (str): Feature class to be created with the post-processed passability layer
        passability_fc (str): Feature class with the passability layer to be post-processed
    """


# ========================
# Helper functions
# ========================


def update_passability_for_buffer(buffered_fc: str, target: str) -> None:
    """
    Removes areas from the passability layer that overlaps with buffered features of a
    specific land use category (target) on the fly during the process_category pipeline.

    Args:
        buffered_fc (str): Feature class with the buffered features of the target category
        target (str): The field name value of the land use / 'arealdekke'
                       that is enlarged and overlaps other areas
    """
    passability_fc = Arealdekke_N10.passability__n10_land_use.value

    temp_file = "in_memory/temp_passability"
    arcpy.management.CopyFeatures(
        in_features=passability_fc, out_feature_class=temp_file
    )

    sql = f"arealdekke <> '{target}'"
    passability_lyr = "passability_lyr"

    arcpy.management.MakeFeatureLayer(in_features=temp_file, out_layer=passability_lyr)

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=passability_lyr,
        selection_type="NEW_SELECTION",
        where_clause=sql,
    )

    arcpy.analysis.Erase(
        in_features=passability_lyr,
        erase_features=buffered_fc,
        out_feature_class=passability_fc,
    )
