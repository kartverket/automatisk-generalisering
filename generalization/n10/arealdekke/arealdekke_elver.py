import arcpy
from enum import Enum
from custom_tools.decorators.timing_decorator import timing_decorator

from composition_configs import core_config
from env_setup import environment_setup
from file_manager import WorkFileManager
from file_manager.n10.file_manager_landuse import Landuse_N10
from input_data import input_arealdekke

from buff_small_polygon_segments import buff_small_polygon_segments

arcpy.env.overwriteOutput = True

# ========================
# Program
# ========================


def main():

    environment_setup.main()

    # Sets up work file manager and creates temporarily files
    working_fc = Landuse_N10.arealdekket_river__n10_landuse.value
    config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=config)

    files = create_wfm_gdbs(wfm=wfm)
    fetch_data(files=files)

    buff_small_polygon_segments(
        in_feature_class=files[fc.rivers_fc],
        out_feature_class=files[fc.rivers_fixed],
        min_width=3,
    )


# ========================
# Dictionary creation and
# Data fetching
# ========================


class fc(Enum):
    rivers_fc = "rivers_fc"
    rivers_fixed = "rivers_fixed"


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

    # Fetch data
    rivers_fc = wfm.build_file_path(file_name="rivers_fc", file_type="gdb")
    rivers_fixed = wfm.build_file_path(file_name="rivers_fixed", file_type="gdb")

    return {
        # Fetch data
        fc.rivers_fc: rivers_fc,
        fc.rivers_fixed: rivers_fixed,
    }


@timing_decorator
def fetch_data(files: dict) -> None:
    """
    Fetches relevant data.

    Args:
        files (dict): Dictionary with all the working files
    """

    # Get data from gdb
    arealdekke_lyr = "arealdekke_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=input_arealdekke.arealdekke,
        out_layer=arealdekke_lyr,
        where_clause="arealdekke='Ferskvann_elv_bekk'",
    )

    # Repair data to remove self intersections
    arcpy.management.RepairGeometry(
        in_features=arealdekke_lyr, delete_null="DELETE_NULL"
    )
    arcpy.management.EliminatePolygonPart(
        in_features=arealdekke_lyr, out_feature_class=files[fc.rivers_fc]
    )


if __name__ == "__main__":
    main()
