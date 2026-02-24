import arcpy

from enum import Enum

arcpy.env.overwriteOutput = True

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from env_setup import environment_setup
from file_manager import WorkFileManager
from file_manager.n10.file_manager_facilities import Facility_N10
from input_data import input_innsjohoyde

# ========================
# Program
# ========================

def main():

    environment_setup.main()

    # Sets up work file manager and creates temporarily files
    working_fc = Facility_N10.ledning__n10_facility.value
    config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=config)

    files = create_wfm_gdbs(wfm=wfm)
    fetch_data(files=files)

# ========================
# Data fetching
# ========================

#Enum class for easier use of files dictionary
class name(Enum):
    innsjo_below_5000="innsjo_below_5000"
    innsjo_above_5000="innsjo_above_5000"

@timing_decorator
def create_wfm_gdbs(wfm: WorkFileManager) -> dict:
    """
    Creates all the temporarily files that are going to
    be used during the process of placing the lake heights.

    Args:
        wfm (WorkFileManager): The WorkFileManager instance that are keeping the files

    Returns:
        dict: A dictionary with all the files as variables
    """
    innsjo_below_5000=wfm.build_file_path(file_name="innsjo_below_5000", file_type="gdb")
    innsjo_above_5000=wfm.build_file_path(file_name="innsjo_above_5000", file_type="gdb")

    return {
        name.innsjo_below_5000: innsjo_below_5000,
        name.innsjo_above_5000:innsjo_above_5000,
        
    }

@timing_decorator
def fetch_data(files: dict) -> None:
    """
    Fetches relevant data.

    Args:
        files (dict): Dictionary with all the working files
    """
    builtup_area_lyr = "builtup_area_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=input_n50.ArealdekkeFlate, out_layer=builtup_area_lyr
    )

    innsjo_original_lyr="innsjo_original_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=input_innsjohoyde.innsjo, out_layer=innsjo_original_lyr
    )

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=innsjo_original_lyr, selection_type='NEW_SELECTION', where_clause="SHAPE_AREA>=5000 OR arealdekke='Ferskvann_innsjo_tjern_regulert'"
    )

    arcpy.management.CopyFeatures(
        in_features=innsjo_original_lyr, out_feature_class=files[name.innsjo_above_5000]
    )

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=innsjo_original_lyr, selection_type='NEW_SELECTION', where_clause="SHAPE_AREA>=5000 OR arealdekke='Ferskvann_innsjo_tjern_regulert'", invert_where_clause='INVERT'
    )

    arcpy.management.CopyFeatures(
        in_features=innsjo_original_lyr, out_feature_class=files[name.innsjo_below_5000]
    )

    


if __name__ == "__main__":
    main()
