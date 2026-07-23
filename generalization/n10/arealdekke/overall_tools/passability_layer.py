# Libraries

import arcpy

arcpy.env.overwriteOutput = True

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools.validation import check_valid_feature_class
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

    if not check_valid_feature_class(passability_fc, level=2):
        print("Passability feature class does not contain any data.")
        return

    # Sets up work file manager to take care of temporary files
    fc = Arealdekke_N10.passability_work_file__n10_land_use.value
    config = core_config.WorkFileConfig(root_file=fc)
    wfm = WorkFileManager(config=config)

    # Fetch original fields to keep in the final passability layer
    field = "arealdekke"

    arealdekke_set = {
        row[0]
        for row in arcpy.da.SearchCursor(passability_fc, [field])
        if row[0] is not None
    }

    # Performes intersection for each land use category
    results = []
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
        intersect_fc = wfm.build_file_path(
            file_name=f"passability_intersect_{value}", file_type="gdb"
        )
        aggregate_fc = wfm.build_file_path(
            file_name=f"passability_aggregate_{value}", file_type="gdb"
        )

        arcpy.analysis.Intersect(
            in_features=[pass_lyr, final_lyr],
            out_feature_class=intersect_fc,
            join_attributes="ALL",
        )
        arcpy.cartography.AggregatePolygons(
            in_features=intersect_fc,
            out_feature_class=aggregate_fc,
            aggregation_distance="5 Meters",
            orthogonality_option="ORTHOGONAL",
        )

        arcpy.management.CalculateField(
            in_table=aggregate_fc,
            field="fremkommelighet",
            expression=f"'{value}'",
            expression_type="PYTHON3",
        )

        results.append(aggregate_fc)

    print("Merging intersected features to create the final passability layer.")
    merged = wfm.build_file_path(file_name="merged_passability", file_type="gdb")
    arcpy.management.Merge(inputs=results, output=merged)

    print(
        "Dissolving merged geometries based on 'fremkommelighet' to create the final passability layer.\n"
    )

    if arcpy.Exists(passability_fc):
        arcpy.management.Delete(passability_fc)

    arcpy.management.Dissolve(
        in_features=merged,
        out_feature_class=passability_fc,
        dissolve_field=["fremkommelighet"],
        multi_part="SINGLE_PART",
    )

    wfm.delete_created_files()
