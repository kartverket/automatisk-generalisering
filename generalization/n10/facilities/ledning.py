# Libraries

import arcpy

arcpy.env.overwriteOutput = True

from enum import StrEnum

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from env_setup import environment_setup
from file_manager import WorkFileManager
from file_manager.n10.file_manager_facilities import Facility_N10
from data_orchestrator.orchestrator import InputDataOrchestrator
from data_orchestrator.data_names import DataNames as dn

# ========================
# Class
# ========================


class Names(StrEnum):
    power_line = "power_line"
    builtup_area = "builtup_area"
    power_line_points = "power_line_points"


# ========================
# Program
# ========================


MAP_SCALE = "N10"
PIPELINE = "ledning"


@timing_decorator
def main():
    """
    The main program for generalizing power lines for N10 from FKB and N50.
    """
    environment_setup.main()
    print("\nGeneralizes power lines...\n")

    data_orc = InputDataOrchestrator(map_scale=MAP_SCALE, pipeline=PIPELINE)
    area_data = data_orc.get_dataset(dn.area)
    ledning_data = data_orc.get_dataset(dn.fkb)

    # Sets up work file manager and creates temporarily files
    working_fc = Facility_N10.ledning__n10_facility.value
    config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=config)

    files = {
        name: wfm.build_file_path(file_name=name, file_type="gdb") for name in Names
    }

    fetch_data(files=files, area_data=area_data)
    create_power_line_points(files=files, fkb_data=ledning_data)
    remove_power_lines(files=files, fkb_data=ledning_data)
    remove_masts(fkb_data=ledning_data)

    wfm.delete_created_files()

    print("\nGeneralization of power lines completed!\n")


# ========================
# Main functions
# ========================


def fetch_data(files: dict, area_data) -> None:
    """
    Fetches relevant data.

    Args:
        files (dict): Dictionary with all the working files
        area_data: The area dataset
    """
    print("Fetching data from source datasets...")

    builtup_area_lyr = "builtup_area_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=area_data.ArealdekkeFlate_N50, out_layer=builtup_area_lyr
    )
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=builtup_area_lyr,
        selection_type="NEW_SELECTION",
        where_clause="OBJTYPE IN ('BymessigBebyggelse', 'Tettbebyggelse') AND shape_Area > 100000",
    )
    arcpy.management.CopyFeatures(
        in_features=builtup_area_lyr, out_feature_class=files[Names.builtup_area]
    )

    print("Data fetching completed.")


def create_power_line_points(files: dict, fkb_data) -> None:
    """
    Creates a new feature class with center points for each power line.

    Args:
        files (dict): Dictionary with all the working files
        fkb_data: The FKB dataset
    """
    print("Creating power line points...")

    arcpy.management.FeatureToPoint(
        in_features=fkb_data.FKB_Ledning,
        out_feature_class=files[Names.power_line_points],
        point_location="CENTROID",
    )

    print("Power line points created.")


def remove_power_lines(files: dict, fkb_data) -> None:
    """
    Deletes all power lines that have a center point intersecting built-up
    area (with buffer tolerance) and are shorter than the tolerance.

    Args:
        files (dict): Dictionary with all the working files
        fkb_data: The FKB dataset
    """
    print("Removing power lines...")

    tolerance = [1500, 300]  # [m]
    buffer_tolerance = [0, 100]  # [m]
    features = [
        fkb_data.FKB_Ledning,
        files[Names.power_line],
        Facility_N10.ledning_output__n10_facility.value,
    ]

    centroids_lyr = "centroids_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[Names.power_line_points], out_layer=centroids_lyr
    )

    for i in range(2):
        arcpy.management.SelectLayerByLocation(
            in_layer=centroids_lyr,
            overlap_type="INTERSECT",
            select_features=files[Names.builtup_area],
            selection_type="NEW_SELECTION",
            search_distance=f"{buffer_tolerance[i]} Meters",
        )

        delete_ids = [
            row[0] for row in arcpy.da.SearchCursor(centroids_lyr, ["ORIG_FID"])
        ]

        power_lines_lyr = "power_lines_lyr"
        arcpy.management.MakeFeatureLayer(
            in_features=features[i], out_layer=power_lines_lyr
        )

        oid_list = ",".join(map(str, delete_ids))
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=power_lines_lyr,
            selection_type="NEW_SELECTION",
            where_clause=f"OBJECTID IN ({oid_list})",
        )
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=power_lines_lyr,
            selection_type="SUBSET_SELECTION",
            where_clause=f"SHAPE_Length < {tolerance[i]}",
        )
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=power_lines_lyr,
            selection_type="SUBSET_SELECTION",
            where_clause=f"hovedbruk <> 'hogspent'",
        )
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=power_lines_lyr, selection_type="SWITCH_SELECTION"
        )

        arcpy.management.CopyFeatures(
            in_features=power_lines_lyr, out_feature_class=features[i + 1]
        )

    print("Power lines removed.")


def remove_masts(fkb_data) -> None:
    """
    Deletes all masts that are not connected to a power line anymore.

    Args:
        fkb_data: The FKB dataset
    """
    print("Removing masts...")

    mast_lyr = "mast_lyr"
    arcpy.management.MakeFeatureLayer(in_features=fkb_data.FKB_Mast, out_layer=mast_lyr)

    arcpy.management.SelectLayerByLocation(
        in_layer=mast_lyr,
        overlap_type="INTERSECT",
        select_features=Facility_N10.ledning_output__n10_facility.value,
        selection_type="NEW_SELECTION",
        search_distance="5 Meters",
    )

    arcpy.management.CopyFeatures(
        in_features=mast_lyr,
        out_feature_class=Facility_N10.mast_output__n10_facility.value,
    )

    print("Masts removed.")


# ========================

if __name__ == "__main__":
    main()
