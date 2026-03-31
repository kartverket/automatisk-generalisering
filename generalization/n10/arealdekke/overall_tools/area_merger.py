# Libraries

import arcpy

arcpy.env.overwriteOutput = True

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10

# ========================
# Main function
# ========================


@timing_decorator
def area_merger(
    input_fc: str, buffered_fc: str, work_fc: str, output_fc: str, changed_area: str
) -> None:
    """
    The main function that dissolves buffered geometries into the
    data set, removes overlapping areas and preserves topology.

    Args:
        input_fc (str): Input feature class with original land use
        buffered_fc (str): Feature class with the buffer zones for thin polygons
        work_fc (str): Feature class to store half-processed results
        output_fc (str): Feature class to store output
        changed_area (str): The field name value of the land use 'arealdekke'
                            that is enlarged and overlaps other areas
    """
    create_overlapping_land_use(
        input_fc=input_fc,
        buffered_fc=buffered_fc,
        output_fc=work_fc,
        changed_area=changed_area,
    )

    adjusting_surrounding_geometries(
        input_fc=work_fc,
        buffered_fc=buffered_fc,
        output_fc=output_fc,
        changed_area=changed_area,
    )


# ========================
# Helper functions
# ========================


@timing_decorator
def create_overlapping_land_use(
    input_fc: str, buffered_fc: str, output_fc: str, changed_area: str
) -> None:
    """
    Creates a new feature class that keeps all original features except
    for those matching 'changed_area' and adds the buffered features so that
    the complete data contains correct, but overlapping areas.

    Args:
        input_fc (str): Feature class containing all the original features
        buffered_fc (str): Feature class containing the buffered, small features
        output_fc (str): Feature class to be created with overlapping geometries
        changed_area (str): The attribute value of the attribute field to change
    """
    print(f"🎯 Filtering 'arealdekke' on attribute: '{changed_area}' …")
    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(input_fc, land_use_lyr)
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr,
        selection_type="NEW_SELECTION",
        where_clause=f"arealdekke = '{changed_area}'",
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

    print(f"🧹 Collects all other land use types except for '{changed_area}' …")
    arcpy.management.SelectLayerByAttribute(
        land_use_lyr,
        selection_type="NEW_SELECTION",
        where_clause=f"arealdekke NOT IN ('{changed_area}')",
    )

    print("🏁 Merges the data together in final output …")
    arcpy.management.Merge(inputs=[temp_dissolve_fc, land_use_lyr], output=output_fc)

    print("Feature class is ready for use 🎉")


@timing_decorator
def adjusting_surrounding_geometries(
    input_fc: str, buffered_fc: str, output_fc: str, changed_area: str
) -> None:
    """
    Adjusts land use that intersects with 'changed_area'
    that have been enlarged to preserve topology.

    Args:
        input_fc (str): Input feature class with overlapping land use
        buffered_fc (str): Feature class with the buffer zones for thin polygons
        output_fc (str): Feature class to store output
        changed_area (str): The field name value of the land use 'arealdekke'
                            that is enlarged and overlaps other areas
    """
    print(f"\n🚀 Adjusts edges to fit overlapping areas to {changed_area}...\n")

    # 1) Sets up work file manager to take care of temporary files
    fc = Arealdekke_N10.area_line_merger__n10_land_use.value
    config = core_config.WorkFileConfig(root_file=fc)
    wfm = WorkFileManager(config=config)

    # 2) Creates temporary files
    files = create_wfm_gdbs(wfm)

    # 3) Fetch data with changed area and those overlapping these
    fetch_relevant_data(
        input_fc=input_fc,
        buffered_fc=buffered_fc,
        files=files,
        attr_val=changed_area,
    )

    # 4) Delete overlapping areas from features
    erase_overlap(files=files)

    # 5) Collect the data and store the result
    collect_and_finish(files=files, output_fc=output_fc)

    wfm.delete_created_files()


@timing_decorator
def create_wfm_gdbs(wfm: WorkFileManager) -> dict:
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
    erased_intersection = wfm.build_file_path(
        file_name="erased_intersection", file_type="gdb"
    )

    return {
        "copy_of_input": copy_of_input,
        "locked_features": locked_features,
        "intersecting_features": intersecting_features,
        "erased_intersection": erased_intersection,
    }


@timing_decorator
def fetch_relevant_data(
    input_fc: str, buffered_fc: str, files: dict, attr_val: str
) -> None:
    """
    Copies the original data to work file manager and creates two feature classes:
        1) All the buffered data (locked)
        2) Data intersecting these buffers

    Args:
        input_fc (str): Feature class with the original input data
        buffered_fc (str): Feature class with the buffers
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
        select_features=buffered_fc,
        selection_type="NEW_SELECTION",
    )
    arcpy.management.CopyFeatures(
        in_features=land_use_lyr, out_feature_class=intersecting_fc
    )

    # Deletes intersecting features from original data
    arcpy.management.DeleteFeatures(in_features=land_use_lyr)


@timing_decorator
def erase_overlap(files: dict) -> None:
    """
    Erase line parts of intersecting features that overlaps locked features (avoiding overlap).

    Args:
        files (dict): Dictionary with all the working files
    """
    arcpy.analysis.Erase(
        in_features=files["intersecting_features"],
        erase_features=files["locked_features"],
        out_feature_class=files["erased_intersection"],
    )


@timing_decorator
def collect_and_finish(files: dict, output_fc: str) -> None:
    """
    Collects original data and modified data in one
    feature class, and copies the result to output.

    Args:
        files (dict): Dictionary with all the working files
        output_fc (str): Feature class to store the final result
    """
    data = [
        files["copy_of_input"],
        files["locked_features"],
        files["erased_intersection"],
    ]

    arcpy.management.Merge(inputs=data, output=output_fc)
