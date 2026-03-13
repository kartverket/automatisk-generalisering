# Libraries

import arcpy

arcpy.env.overwriteOutput = True

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from env_setup import environment_setup
from file_manager import WorkFileManager
from file_manager.n10.file_manager_land_use import Land_use_N10
from input_data import input_test_data

# ========================
# Program
# ========================


@timing_decorator
def adjusting_surrounding_geometries(input: str, changed_area: str) -> None:
    """
    Adjust land use that intersects with 'changed_area'
    that have been enlarged to preserve topology.

    Args:
        input (str): Input feature class with overlapping land use
        changed_area (str): The field name value of the land
                            use 'arealdekke' that is enlarged
                            and overlaps other areas

    Concept:
        0) Input feature class contains a complete land use, where one specific value of 'arealdekke' overlaps other areas
        1) Select all features with 'arealdekke' equal to 'changed_area' and keep these as locked features
        2) Select all features that overlaps with the locked features
        3) Create a dictionary with: key: locked area ID, value: the geometry of the bounding line
        4) For each of the overlapping features:
            a) Use PolygonToLine to get the bounding line geometry
            b) Identify the points on the edge of locked area and those within
            c) Remove the points within
            d) Fetch the line of the locked featyre between the intersecting points
            e) Add these points to the original line geometry
    """
    print(f"\n🚀 Adjusts edges to fit overlapping areas to {changed_area}...\n")

    # Setting up constants
    output_fc = Land_use_N10.area_line_merger_output__n10_land_use.value

    # 1) Sets up work file manager to take care of temporary files
    work_fc = Land_use_N10.area_line_merger__n10_land_use.value
    work_config = core_config.WorkFileConfig(root_file=work_fc)
    work_wfm = WorkFileManager(config=work_config)

    # 2) Creates temporary files
    work_files = create_work_wfm_gdbs(work_wfm)

    # 3) Fetch data with changed area and those overlapping these
    fetch_relevant_data(input_fc=input, files=work_files, attr_val=changed_area)


@timing_decorator
def create_overlapping_land_use(
    complete_fc: str, buffered_fc: str, output_fc: str, attribute: str
) -> None:
    """
    Creates a new feature class that keeps all original features except
    for those matching 'attribute' and adds the buffered features so that
    the complete data contains correct, but overlapping areas.

    Args:
        complete_fc (str): Feature class containing all the original features
        buffered_fc (str): Feature class containing the buffered, small features
        output_fc (str): Feature class to be created with overlapping geometries
        attribute (str): The attribute value of the attribute field to change
    """
    print(f"🎯 Filtering 'arealdekke' on attribute: '{attribute}' …")
    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(complete_fc, land_use_lyr)
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr,
        selection_type="NEW_SELECTION",
        where_clause=f"arealdekke = '{attribute}'",
    )

    print("🔀 Merges buffered features with selected original land use …")
    temp_merge_fc = r"in_memory/temp_merge_fc"
    temp_dissolve_fc = r"in_memory/temp_dissolved_fc"

    arcpy.management.Merge(inputs=[buffered_fc, land_use_lyr], output=temp_merge_fc)

    print("🧩 Runs dissolve …")
    arcpy.management.Dissolve(
        in_features=temp_merge_fc,
        out_feature_class=temp_dissolve_fc,
        dissolve_field="arealdekke",
        multi_part="SINGLE_PART",
    )

    print(f"🧹 Collects all other land use types except for '{attribute}' …")
    arcpy.management.SelectLayerByAttribute(
        land_use_lyr,
        selection_type="NEW_SELECTION",
        where_clause=f"arealdekke NOT IN ('{attribute}')",
    )

    print("🏁 Merges the data together in final output …")
    arcpy.management.Merge(inputs=[temp_dissolve_fc, land_use_lyr], output=output_fc)

    print("Feature class is ready for use 🎉")


# ========================
# Main functions
# ========================


@timing_decorator
def create_work_wfm_gdbs(wfm: WorkFileManager) -> dict:
    """
    Creates all the temporarily files that are going to be used
    during the process of adjusting land use boundaries.

    Args:
        wfm (WorkFileManager): The WorkFileManager instance that are keeping the files

    Returns:
        dict: A dictionary with all the files as variables
    """
    copy_of_input = wfm.build_file_path(file_name="copy_of_input", file_type="gdb")
    locked_features = wfm.build_file_path(file_name="locked_features", file_type="gdb")
    intersecting_features = wfm.build_file_path(
        file_name="intersecting_features", file_type="gdb"
    )

    return {
        "copy_of_input": copy_of_input,
        "locked_features": locked_features,
        "intersecting_features": intersecting_features,
    }


@timing_decorator
def fetch_relevant_data(input_fc: str, files: dict, attr_val: str) -> None:
    """
    Copies the original data to work file manager and creates two feature classes:
        1) All the buffered data (locked)
        2) Data intersecting these buffers

    Args:
        input_fc (str): Feature class with the original input data
        files (dict): Dictionary with all the working files
        attr_val (str): String representing the value of the attribute that must be locked
    """
    orig_fc = files["copy_of_input"]
    locked_fc = files["locked_features"]
    intersecting_fc = files["intersecting_features"]

    # Copy the original data to a fc that will be adjusted
    arcpy.management.CopyFeatures(in_features=input_fc, out_feature_class=orig_fc)

    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(in_features=orig_fc, out_layer=land_use_lyr)

    # Stores locked features in own fc
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr,
        selection_type="NEW_SELECTION",
        where_clause=f"arealdekke = '{attr_val}'",
    )
    arcpy.management.CopyFeatures(in_features=land_use_lyr, out_feature_class=locked_fc)

    # Deletes locked features from original data
    arcpy.management.DeleteFeatures(in_features=land_use_lyr)

    # Stores overlapping features in own fc
    arcpy.management.SelectLayerByLocation(
        in_layer=land_use_lyr,
        overlap_type="INTERSECT",
        select_features=locked_fc,
        selection_type="NEW_SELECTION",
    )
    arcpy.management.CopyFeatures(
        in_features=land_use_lyr, out_feature_class=intersecting_fc
    )

    # Deletes intersecting features from original data
    arcpy.management.DeleteFeatures(in_features=land_use_lyr)


# ========================
# Helper functions
# ========================


# ========================


if __name__ == "__main__":
    environment_setup.main()

    working_fc = Land_use_N10.area_line_merger_start__n10_land_use.value
    input_fc = input_test_data.arealdekke
    elv_fc = input_test_data.elv
    attribute = "Ferskvann_elv_bekk"

    if not arcpy.Exists(working_fc):
        create_overlapping_land_use(
            complete_fc=input_fc,
            buffered_fc=elv_fc,
            output_fc=working_fc,
            attribute=attribute,
        )
    else:
        print(
            "⚡ Sammenslått datasett er allerede på plass – går rett videre i prosessen!"
        )

    adjusting_surrounding_geometries(input=working_fc, changed_area=attribute)
