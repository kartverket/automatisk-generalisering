# Libraries

import arcpy

arcpy.env.overwriteOutput = True

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from file_manager import WorkFileManager
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
    print(
        "\nStarting post-processing of the passability layer by checking for match with geometries in the final feature class."
    )

    # Sets up work file manager to take care of temporary files
    fc = Arealdekke_N10.passability_work_file__n10_land_use.value
    config = core_config.WorkFileConfig(root_file=fc)
    wfm = WorkFileManager(config=config)

    # Fetch original fields to keep in the final passability layer
    field = "arealdekke"

    arealdekke_set = set()

    with arcpy.da.SearchCursor(passability_fc, [field]) as cursor:
        for row in cursor:
            if row[0] is not None:
                arealdekke_set.add(row[0])

    # Performes intersection for each land use category
    intersect_results = []
    num = len(arealdekke_set)

    for i, value in enumerate(arealdekke_set):
        print(f"Processing passability for land use category: {value} ({i+1} / {num})")

        # Creates layers
        pass_lyr = "pass_lyr"
        final_lyr = "final_lyr"

        arcpy.management.MakeFeatureLayer(
            in_features=passability_fc, out_layer=pass_lyr
        )
        arcpy.management.MakeFeatureLayer(in_features=final_fc, out_layer=final_lyr)

        # Selects features with the current 'arealdekke' value in both layers
        sql = f"{field} = '{value}'"
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=pass_lyr, selection_type="NEW_SELECTION", where_clause=sql
        )
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=final_lyr, selection_type="NEW_SELECTION", where_clause=sql
        )

        # Creates temporary file for this category
        out_fc = wfm.build_file_path(
            file_name=f"passability_intersect_{value}", file_type="gdb"
        )

        arcpy.analysis.Intersect(
            in_features=[pass_lyr, final_lyr],
            out_feature_class=out_fc,
            join_attributes="ALL",
        )

        intersect_results.append(out_fc)

    print("Merging intersected features to create the final passability layer.")
    merged = wfm.build_file_path(file_name="merged_passability", file_type="gdb")
    arcpy.management.Merge(inputs=intersect_results, output=merged)

    print(
        "Dissolving merged geometries based on 'fremkommelighet' to create the final passability layer.\n"
    )
    arcpy.management.Dissolve(
        in_features=merged,
        out_feature_class=passability_fc,
        dissolve_field=["fremkommelighet"],
        multi_part="SINGLE_PART",
    )

    wfm.delete_created_files()


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
