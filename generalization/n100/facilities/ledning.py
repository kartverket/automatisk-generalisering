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
    create_power_line_points(files=files)
    remove_power_lines(files=files)
    remove_masts(files=files)

    wfm.delete_created_files()

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
    builtup_area = wfm.build_file_path(file_name="builtup_area", file_type="gdb")
    mast = wfm.build_file_path(file_name="mast", file_type="gdb")
    power_line_points = wfm.build_file_path(file_name="power_line_points", file_type="gdb")
    point_in_builtup_area = wfm.build_file_path(file_name="point_in_builtup_area", file_type="gdb")
    delete_layer = wfm.build_file_path(file_name="delete_layer", file_type="gdb")
    
    return {
        "power_line": power_line,
        "builtup_area": builtup_area,
        "mast": mast,
        "power_line_points": power_line_points,
        "point_in_builtup_area": point_in_builtup_area,
        "delete_layer": delete_layer,
    }

@timing_decorator
def fetch_data(files: dict) -> None:
    """
    Fetches relevant data.

    Args:
        files (dict): Dictionary with all the working files
    """
    builtup_area_lyr = "builtup_area_lyr"
    arcpy.management.MakeFeatureLayer(in_features=input_n50.ArealdekkeFlate, out_layer=builtup_area_lyr)

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=builtup_area_lyr,
        selection_type="NEW_SELECTION",
        where_clause="OBJTYPE IN ('BymessigBebyggelse', 'Tettbebyggelse') AND shape_Area > 100000"
    )

    arcpy.management.CopyFeatures(in_features=input_fkb.fkb_ledning, out_feature_class=files["power_line"])
    arcpy.management.CopyFeatures(in_features=builtup_area_lyr, out_feature_class=files["builtup_area"])
    arcpy.management.CopyFeatures(in_features=input_fkb.fkb_mast, out_feature_class=files["mast"])

@timing_decorator
def create_power_line_points(files: dict) -> None:
    """
    Creates a new feature class with center points for each power line.

    Args:
        files (dict): Dictionary with all the working files
    """
    arcpy.management.FeatureToPoint(
        in_features=files["power_line"],
        out_feature_class=files["power_line_points"],
        point_location="CENTROID"
    )

@timing_decorator
def remove_power_lines(files: dict) -> None:
    """
    Deletes all power lines that has a center point intersecting builtup
    area (with buffer tolerance) and are shorter than the tolerance.

    Args:
        files (dict): Dictionary with all the working files
    """
    tolerance = [1500, 300] # [m]
    buffer_tolerance = [0, 100] # [m]

    centroids_lyr = "centroids_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["power_line_points"],
        out_layer=centroids_lyr
    )

    for i in range(2):
        arcpy.management.SelectLayerByLocation(
            in_layer=centroids_lyr,
            overlap_type="INTERSECT",
            select_features=files["builtup_area"],
            selection_type="NEW_SELECTION",
            search_distance=f"{buffer_tolerance[i]} Meters"
        )

        arcpy.management.CopyFeatures(
            in_features=centroids_lyr,
            out_feature_class=files["point_in_builtup_area"]
        )

        delete_ids = [row[0] for row in arcpy.da.SearchCursor(
            files["point_in_builtup_area"], ["ORIG_FID"]
        )]

        power_lines_lyr = "power_lines_lyr"
        arcpy.management.MakeFeatureLayer(
            in_features=files["power_line"],
            out_layer=power_lines_lyr
        )
        
        oid_list = ",".join(map(str, delete_ids))
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=power_lines_lyr,
            selection_type="NEW_SELECTION",
            where_clause=f"OBJECTID IN ({oid_list})"
        )
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=power_lines_lyr,
            selection_type="SUBSET_SELECTION",
            where_clause=f"SHAPE_Length < {tolerance[i]}"
        )

        arcpy.management.DeleteFeatures(in_features=power_lines_lyr)

    output = Facility_N100.ledning_output__n100_facility.value
    arcpy.management.CopyFeatures(in_features=files["power_line"], out_feature_class=output)

@timing_decorator
def remove_masts(files: dict) -> None:
    """
    Deletes all masts that are not connected to a power line anymore.

    Args:
        files (dict): Dictionary with all the working files
    """
    mast_lyr = "mast_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["mast"],
        out_layer=mast_lyr
    )

    arcpy.management.SelectLayerByLocation(
        in_layer=mast_lyr,
        overlap_type="INTERSECT",
        select_features=files["power_line"],
        selection_type="NEW_SELECTION",
        search_distance="5 Meters",
        invert_spatial_relationship="INVERT"
    )

    arcpy.management.DeleteFeatures(in_features=mast_lyr)

    arcpy.management.CopyFeatures(
        in_features=files["mast"],
        out_feature_class=Facility_N100.mast_output__n100_facility.value
    )

# ========================

if __name__ == "__main__":
    main()
