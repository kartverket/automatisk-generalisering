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
def create_overlapping_land_use(
    input_fc: str,
    buffered_fc: str,
    output_fc: str,
) -> None:
    """
    Creates a new feature class that keeps all original features and adds
    the buffered features so that the complete data contains correct,
    but overlapping areas.

    Args:
        input_fc (str): Feature class containing all the original features
        buffered_fc (str): Feature class containing the buffered, small features
        output_fc (str): Feature class to be created with overlapping geometries
    """
    fc = Arealdekke_N10.overlap_merger__n10_land_use.value
    config = core_config.WorkFileConfig(root_file=fc)
    wfm = WorkFileManager(config=config)

    files = create_wfm_gdbs(wfm=wfm)

    print("🔀 Merges buffered features with selected original land use …")
    arcpy.management.Merge(
        inputs=[buffered_fc, input_fc], output=files["temp_merge_fc"]
    )

    print("🧩 Runs dissolve …")
    arcpy.management.Dissolve(
        in_features=files["temp_merge_fc"],
        out_feature_class=output_fc,
        dissolve_field=[],
        multi_part="SINGLE_PART",
    )

    wfm.delete_created_files()


# ========================
# Helper functions
# ========================


def create_wfm_gdbs(wfm: WorkFileManager) -> dict:
    """
    Creates all the temporarily files that are going to be used
    during the process of adjusting land use boundaries.

    Args:
        wfm (WorkFileManager): The WorkFileManager instance that are keeping the files

    Returns:
        dict: A dictionary with all the files as variables
    """
    return {
        "temp_merge_fc": wfm.build_file_path(
            file_name="temp_merge_fc", file_type="gdb"
        ),
    }
