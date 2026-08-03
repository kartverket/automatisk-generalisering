# Libraries

import arcpy

arcpy.env.overwriteOutput = True

from enum import StrEnum

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10
from generalization.n10.arealdekke.overall_tools.fill_holes import (
    match_holes_with_surrounding_features,
)

# ========================
# Class
# ========================


class Names(StrEnum):
    split_result = "split_result"
    other_features = "other_features"
    surrounding_features = "surrounding_features"
    surrounding_lines = "surrounding_lines"
    intersecting_lines = "intersecting_lines"
    join_land_use = "join_land_use"


# ========================
# Main function
# ========================


@timing_decorator
def replace_uncategorized_features(input_fc: str) -> None:
    """
    Recategorizes the features that are uncategorized (empty) in the input feature class.

    Args:
        input_fc (str): The feature class that is going to be processed.
                        It should be the output of the generalization process
    """
    # Set up WorkFileManager
    fc = Arealdekke_N10.replace_uncategorized__n10_land_use.value
    config = core_config.WorkFileConfig(root_file=fc)
    wfm = WorkFileManager(config=config)

    files = file_setup(wfm=wfm)

    fetch_empty_features(input_fc=input_fc, files=files)
    match_holes_with_surrounding_features(files=files, input_fc=input_fc, strict=False)
    create_final_output(files=files, output_fc=input_fc)

    wfm.delete_created_files()


# ========================
# Helper functions
# ========================


def file_setup(wfm: WorkFileManager) -> dict:
    """
    Creates all the temporary files that are going to be used
    during the process of replacing uncategorized features.

    Args:
        wfm (WorkFileManager): The WorkFileManager instance that are keeping the files

    Returns:
        dict: A dictionary with all the files as variables
    """
    return {
        name: wfm.build_file_path(file_name=name, file_type="gdb") for name in Names
    }


def fetch_empty_features(input_fc: str, files: dict) -> None:
    """
    Fetches all the features that are uncategorized (empty)
    from the input feature class.

    Args:
        input_fc (str): The input feature class
        files (dict): A dictionary with all the temporary files
    """
    land_use_lyr = "land_use_lyr"
    arcpy.MakeFeatureLayer_management(input_fc, land_use_lyr)

    arcpy.management.SelectLayerByAttribute(
        land_use_lyr, "NEW_SELECTION", f"arealdekke = ''"
    )

    arcpy.management.CopyFeatures(
        in_features=land_use_lyr, out_feature_class=files[Names.split_result]
    )

    arcpy.analysis.Erase(
        in_features=input_fc,
        erase_features=files[Names.split_result],
        out_feature_class=files[Names.other_features],
    )

    arcpy.management.MakeFeatureLayer(
        in_features=files[Names.split_result], out_layer=land_use_lyr
    )
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr,
        selection_type="NEW_SELECTION",
        where_clause="Shape_Area < 5",
    )
    arcpy.management.DeleteFeatures(in_features=land_use_lyr)


def create_final_output(files: dict, output_fc: str) -> None:
    """
    Creates the final output feature class by merging the split result
    and the surrounding features.

    Args:
        files (dict): A dictionary with all the temporary files
        output_fc (str): The output feature class
    """
    arcpy.management.Merge(
        inputs=[files[Names.split_result], files[Names.other_features]],
        output=output_fc,
    )
    arcpy.management.Integrate(in_features=output_fc, cluster_tolerance="0.001 Meters")
