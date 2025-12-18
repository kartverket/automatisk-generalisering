# Libraries

import arcpy

arcpy.env.overwriteOutput = True

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from file_manager import WorkFileManager
from file_manager.n100.file_manager_facilities import Facility_N100
from input_data import input_fkb, input_n50

# ========================
# Program
# ========================

@timing_decorator
def main():
    """
    The main program for generalizing power lines for N10 from FKB and N50.
    """
    print("\nGeneralizes power lines...\n")

    # Sets up work file manager and creates temporarily files
    working_fc = Facility_N100.ledning__n100_facility.value
    config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=config)

    files = create_wfm_gdbs(wfm=wfm)

    fetch_data(files=files)
    remove_power_lines(files=files)

    print("\nGeneralization of power lines completed!\n")

# ========================
# Main functions
# ========================

@timing_decorator
def create_wfm_gdbs(wfm: WorkFileManager) -> dict:
    """
    Creates all the temporarily files that are going to
    be used during the process of generalizing power lines.

    Args:
        wfm (WorkFileManager): The WorkFileManager instance that are keeping the files

    Returns:
        dict: A dictionary with all the files as variables
    """
    power_line = wfm.build_file_path(file_name="power_line", file_type="gdb")
    build_up_area = wfm.build_file_path(file_name="build_up_area", file_type="gdb")
    
    return {
        "power_line": power_line,
        "build_up_area": build_up_area
    }

@timing_decorator
def fetch_data(files: dict) -> None:
    """
    Fetches relevant data.

    Args:
        files (dict): Dictionary with all the working files
    """
    byggoganlegg_lyr = "byggoganlegg_lyr"
    build_up_area_lyr = "build_up_area_lyr"
    arcpy.management.MakeFeatureLayer(in_features=input_fkb.fkb_byggoganlegg_senterlinje, out_layer=byggoganlegg_lyr)
    arcpy.management.MakeFeatureLayer(in_features=input_n50.ArealdekkeFlate, out_layer=build_up_area_lyr)

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=byggoganlegg_lyr,
        selection_type="NEW_SELECTION",
        where_clause="objtype = 'ledning'"
    )
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=build_up_area_lyr,
        selection_type="NEW_SELECTION",
        where_clause="OBJTYPE IN ('BymessigBebyggelse', 'Tettbebyggelse') AND shape_Area > 100000"
    )

    arcpy.management.CopyFeatures(in_features=byggoganlegg_lyr, out_feature_class=files["power_line"])
    arcpy.management.CopyFeatures(in_features=build_up_area_lyr, out_feature_class=files["build_up_area"])

@timing_decorator
def remove_power_lines(files: dict) -> None:
    """
    Deletes all power lines that intersect with build up area.

    Args:
        files (dict): Dictionary with all the working files
    """
    output = Facility_N100.ledning_output__n100_facility.value
    arcpy.management.CopyFeatures(in_features=files["power_line"], out_feature_class=output)

    power_line_lyr = "power_line_lyr"
    arcpy.management.MakeFeatureLayer(in_features=output, out_layer=power_line_lyr)

    arcpy.management.SelectLayerByLocation(
        in_layer=power_line_lyr,
        overlap_type="INTERSECT",
        select_features=files["build_up_area"],
        selection_type="NEW_SELECTION"
    )

    arcpy.management.DeleteFeatures(in_features=power_line_lyr)

# ========================
# Helper functions
# ========================

# ...

# ========================

if __name__ == "__main__":
    main()
