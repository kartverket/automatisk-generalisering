# Libraries

import arcpy

arcpy.env.overwriteOutput = True

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10
from generalization.n10.arealdekke.overall_tools.arealdekke_dissolver import (
    ArealdekkeDissolver,
)
from generalization.n10.arealdekke.overall_tools.passability_layer import (
    update_passability_for_buffer,
)

fetch_orig_data = ArealdekkeDissolver.restore_data_polygon_without_feature_to_point


# ========================
# Main function
# ========================


@timing_decorator
def remove_overlaps(
    input_fc: str, buffered_fc: str, locked_fc: str, output_fc: str, changed_area: str
) -> None:
    """
    Adjusts land use that intersects with 'changed_area'
    that have been enlarged to preserve topology.

    Args:
        input_fc (str): Input feature class with original, complete land use
        buffered_fc (str): Feature class with the enlarged land use that
                           overlaps other areas
        locked_fc (str): Feature class with the locked features
        output_fc (str): Feature class to store output
        changed_area (str): The field name value of the land use / 'arealdekke'
                            that is enlarged and overlaps other areas
    """
    # 1) Sets up work file manager to take care of temporary files
    fc = Arealdekke_N10.overlap_remover__n10_land_use.value
    config = core_config.WorkFileConfig(root_file=fc)
    wfm = WorkFileManager(config=config)

    # 2) Creates temporary files
    files = create_wfm_gdbs(wfm)

    # 3) Remove locked features from buffers to avoid overlap in these areas
    data_cleaning(files=files, input_fc=input_fc, buffered_fc=buffered_fc, locked_fc=locked_fc)

    # Extra: Fix geometries in the passability layer after buffering
    update_passability_for_buffer(
        buffered_fc=files["singlepart_buffers"], target=changed_area
    )

    # 4) Fetch correct attributes for the buffered features
    # (those that are going to be merged with original data)
    change_target_features(input_fc=input_fc, files=files, target=changed_area)

    # 5) Fetch data with changed area and those overlapping these
    fetch_relevant_data(
        files=files,
        attr_val=changed_area,
    )

    # 6) Delete overlapping areas from features
    erase_overlap(files=files)

    # 7) Collect the data and store the result
    collect_and_finish(files=files, output_fc=output_fc)

    wfm.delete_created_files()


# ========================
# Helper functions
# ========================


def create_wfm_gdbs(wfm: WorkFileManager) -> dict:
    """
    Creates all the temporarily files that are going to be used
    during the process of removing overlap in the land use data.

    Args:
        wfm (WorkFileManager): The WorkFileManager instance that are keeping the files

    Returns:
        dict: A dictionary with all the files as variables
    """
    return {
        "erased_buffers": wfm.build_file_path(
            file_name="erased_buffers", file_type="gdb"
        ),
        "singlepart_buffers": wfm.build_file_path(
            file_name="singlepart_buffers", file_type="gdb"
        ),
        "copy_of_input": wfm.build_file_path(
            file_name="copy_of_input", file_type="gdb"
        ),
        "locked_features": wfm.build_file_path(
            file_name="locked_features", file_type="gdb"
        ),
        "intersecting_features": wfm.build_file_path(
            file_name="intersecting_features", file_type="gdb"
        ),
        "erased_intersection": wfm.build_file_path(
            file_name="erased_intersection", file_type="gdb"
        ),
    }


def data_cleaning(files: dict, input_fc: str, buffered_fc: str, locked_fc: str) -> None:
    """
    Removes locked areas from the buffered features to avoid overlap in these areas,
    and creates a singlepart feature class so that areas not overlapping the original
    features anymore can be deleted.

    Args:
        files (dict): Dictionary with all the working files
        input_fc (str): Input feature class with original, complete land use
        buffered_fc (str): Feature class with the enlarged land use that
                           overlaps other areas
        locked_fc (str): Feature class with the locked features
    """
    if locked_fc:
        arcpy.analysis.PairwiseErase(
            in_features=buffered_fc,
            erase_features=locked_fc,
            out_feature_class=files["erased_buffers"],
        )
    else:
        arcpy.management.CopyFeatures(
            in_features=buffered_fc, out_feature_class=files["erased_buffers"]
        )
    
    arcpy.management.MultipartToSinglepart(
        in_features=files["erased_buffers"],
        out_feature_class=files["singlepart_buffers"]
    )

    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["singlepart_buffers"], out_layer=land_use_lyr
    )

    arcpy.management.SelectLayerByLocation(
        in_layer=land_use_lyr,
        overlap_type="INTERSECT",
        select_features=input_fc,
        selection_type="NEW_SELECTION",
        invert_spatial_relationship="INVERT",
    )

    arcpy.management.DeleteFeatures(in_features=land_use_lyr)


def change_target_features(input_fc: str, files: dict, target: str) -> None:
    """
    Changes the original geometry to fit with the edited features and preserves attribute information.

    Args:
        input_fc (str): Input feature class with original, complete land use
        files (dict): Dictionary with all the working files
        target (str): The field name value of the land use / 'arealdekke'
                      that is enlarged and overlaps other areas
    """
    # Update attribute information of buffered features with 'arealdekke' == target to original data
    arcpy.management.AddField(
        in_table=files["singlepart_buffers"], field_name="arealdekke", field_type="TEXT"
    )
    arcpy.management.CalculateField(
        in_table=files["singlepart_buffers"],
        field="arealdekke",
        expression=f"'{target}'",
        expression_type="PYTHON3",
    )
    fetch_orig_data(
        without_data=files["singlepart_buffers"],
        original=input_fc,
        column="arealdekke",
        index="arealdekke",
    )

    # Delete old features with 'arealdekke' == target
    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(in_features=input_fc, out_layer=land_use_lyr)
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr,
        selection_type="NEW_SELECTION",
        where_clause=f"arealdekke = '{target}'",
    )
    arcpy.management.DeleteFeatures(in_features=land_use_lyr)

    # Insert the buffered features with correct attribute information
    arcpy.management.Merge(
        inputs=[input_fc, files["singlepart_buffers"]],
        output=files["copy_of_input"],
    )


def fetch_relevant_data(files: dict, attr_val: str) -> None:
    """
    Copies the original data to work file manager and creates two feature classes:
        1) All the buffered data (locked)
        2) Data intersecting these buffers

    Args:
        files (dict): Dictionary with all the working files
        attr_val (str): String representing the value of the attribute that must be locked
    """
    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["copy_of_input"], out_layer=land_use_lyr
    )

    # Stores locked features in own fc
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr,
        selection_type="NEW_SELECTION",
        where_clause=f"arealdekke = '{attr_val}'",
    )
    arcpy.management.CopyFeatures(
        in_features=land_use_lyr, out_feature_class=files["locked_features"]
    )

    # Deletes locked features from original data
    arcpy.management.DeleteFeatures(in_features=land_use_lyr)

    # Stores overlapping features in own fc
    arcpy.management.SelectLayerByLocation(
        in_layer=land_use_lyr,
        overlap_type="INTERSECT",
        select_features=files["locked_features"],
        selection_type="NEW_SELECTION",
    )
    arcpy.management.CopyFeatures(
        in_features=land_use_lyr, out_feature_class=files["intersecting_features"]
    )

    # Deletes intersecting features from original data
    arcpy.management.DeleteFeatures(in_features=land_use_lyr)


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
