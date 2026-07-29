# Libraries

import arcpy

arcpy.env.overwriteOutput = True

from enum import StrEnum

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10

# ========================
# Class
# ========================


class Names(StrEnum):
    empty = "empty"
    adjacent = "adjacent"


# ========================
# Main function
# ========================


@timing_decorator
def replace_uncategorized_features(input_fc: str, output_fc: str) -> None:
    """
    ...
    """
    # Set up WorkFileManager
    fc = Arealdekke_N10.replace_uncategorized__n10_land_use.value
    config = core_config.WorkFileConfig(root_file=fc)
    wfm = WorkFileManager(config=config)

    files = file_setup(wfm=wfm)

    fetch_empty_features(input_fc=input_fc, files=files)


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
        in_features=land_use_lyr, out_feature_class=files[Names.empty]
    )

    arcpy.management.SelectLayerByLocation(
        in_layer=land_use_lyr,
        overlap_type="INTERSECT",
        select_features=input_fc,
        selection_type="NEW_SELECTION",
    )

    arcpy.analysis.Erase(
        in_features=land_use_lyr,
        erase_features=files[Names.empty],
        out_feature_class=files[Names.adjacent],
    )


def categorize_uncategorized_features(files: dict) -> None:
    """
    Categorizes all the features that are uncategorized (empty)
    from the input feature class.

    Args:
        files (dict): A dictionary with all the temporary files
    """
    return


# ========================
