import arcpy

arcpy.env.overwriteOutput = True

from enum import StrEnum

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from data_orchestrator.orchestrator import InputDataOrchestrator
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10
from generalization.n10.arealdekke.category_tools.buff_small_polygon_segments import (
    LINE,
)
from generalization.n10.arealdekke.overall_tools.arealdekke_dissolver import (
    normal_call as dissolve_lines,
)

# ========================
# Constants
# ========================


IMPORTANT_FEATURE = ["Samferdsel", "Bane"]
IMPORTANT_SQL = ",".join([f"'{feature}'" for feature in IMPORTANT_FEATURE])
WATER_FEATURES = ["ElvFlate", "Innsjo", "InnsjoRegulert", "Kanal", "Hav"]
WATER_SQL = ",".join([f"'{feature}'" for feature in WATER_FEATURES])


# ========================
# Class
# ========================


class Names(StrEnum):
    target_lines = "target_lines"
    spatial_join = "spatial_join"
    joined_lines = "joined_lines"
    erased = "erased"
    dissolved = "dissolved"


# ========================
# Main function
# ========================


@timing_decorator
def post_process_lines(land_use_fc: str, data_orc: InputDataOrchestrator) -> None:
    """
    For each target feature corresponding to a specific line feature class,
    remove too small polygons and replace them with new lines, snap these
    together with the original lines and fix the lines to the remaining polygons.

    Args:
        land_use_fc (str): The path to the land use feature class
        data_orc (InputDataOrchestrator): The data orchestrator instance
    """
    working_fc = Arealdekke_N10.snap_lines__n10_land_use.value
    config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=config)

    files = file_setup(wfm=wfm)

    remove_short_polygons(land_use_fc=land_use_fc, files=files)
    snap_lines(land_use_fc=land_use_fc, files=files)

    for line_fc in LINE.values():
        dissolve_lines(input_fc=line_fc, output_fc=files[Names.dissolved], data_orc=data_orc)
        arcpy.cartography.SmoothLine(
            in_features=files[Names.dissolved],
            out_feature_class=line_fc,
            algorithm="PAEK",
            endpoint_option="FIXED_CLOSED_ENDPOINT",
            error_option="RESOLVE_ERRORS",
        )

    wfm.delete_created_files()


# ========================
# Helper functions
# ========================


def file_setup(wfm: WorkFileManager) -> dict:
    """
    Creates all the temporary files that are going to
    be used during the process of buffer thin areas.

    Args:
        wfm (WorkFileManager): The WorkFileManager instance that are keeping the files

    Returns:
        dict: A dictionary with all the files as variables
    """
    return {
        name: wfm.build_file_path(file_name=name, file_type="gdb") for name in Names
    }


def remove_short_polygons(land_use_fc: str, files: dict) -> None:
    """
    Removes all polygons that are shorter than the threshold distance.

    Args:
        land_use_fc (str): The path to the land use feature class
        files (dict): A dictionary with all the files as variables
    """
    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(in_features=land_use_fc, out_layer=land_use_lyr)

    for target, line_fc in LINE.items():
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=land_use_lyr,
            selection_type="NEW_SELECTION",
            where_clause=f"arealdekke='{target}'",
        )
        arcpy.management.SelectLayerByLocation(
            in_layer=land_use_lyr,
            overlap_type="INTERSECT",
            select_features=line_fc,
            selection_type="SUBSET_SELECTION",
        )

        if int(arcpy.management.GetCount(land_use_lyr)[0]) == 0:
            continue

        arcpy.cartography.CollapseHydroPolygon(
            in_features=land_use_lyr,
            out_line_feature_class=files[Names.target_lines],
        )

        arcpy.analysis.SpatialJoin(
            target_features=land_use_lyr,
            join_features=files[Names.target_lines],
            out_feature_class=files[Names.spatial_join],
            join_operation="JOIN_ONE_TO_ONE",
            match_option="INTERSECT",
        )

        join_lyr = "join_lyr"
        arcpy.management.MakeFeatureLayer(
            in_features=files[Names.spatial_join], out_layer=join_lyr
        )
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=join_lyr,
            selection_type="NEW_SELECTION",
            where_clause="Join_Count = 1",
        )

        if int(arcpy.management.GetCount(join_lyr)[0]) == 0:
            continue

        line_lyr = "line_lyr"
        arcpy.management.MakeFeatureLayer(
            in_features=files[Names.target_lines], out_layer=line_lyr
        )
        arcpy.management.SelectLayerByLocation(
            in_layer=line_lyr,
            overlap_type="INTERSECT",
            select_features=join_lyr,
            selection_type="NEW_SELECTION",
        )
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=line_lyr,
            selection_type="SUBSET_SELECTION",
            where_clause="Shape_Length < 50",
        )

        if int(arcpy.management.GetCount(line_lyr)[0]) == 0:
            continue

        arcpy.management.SelectLayerByLocation(
            in_layer=join_lyr,
            overlap_type="INTERSECT",
            select_features=line_lyr,
            selection_type="SUBSET_SELECTION",
        )

        if int(arcpy.management.GetCount(join_lyr)[0]) == 0:
            continue

        # Fetch original attributes for the new lines
        arcpy.analysis.SpatialJoin(
            target_features=line_lyr,
            join_features=land_use_lyr,
            out_feature_class=files[Names.joined_lines],
            join_operation="JOIN_ONE_TO_MANY",
            match_option="CLOSEST",
        )

        existing_fields = [f.name for f in arcpy.ListFields(line_lyr)]
        new_fields = [
            f.name
            for f in arcpy.ListFields(land_use_lyr)
            if f.name not in existing_fields
        ]

        arcpy.management.JoinField(
            in_data=line_lyr,
            in_field="OBJECTID",
            join_table=files[Names.joined_lines],
            join_field="TARGET_FID",
            fields=new_fields,
        )

        arcpy.management.Append(
            inputs=line_lyr,
            target=line_fc,
            schema_type="NO_TEST",
        )
        arcpy.edit.Snap(
            in_features=line_fc,
            snap_environment=[
                [line_fc, "END", "15 Meters"],
                [line_fc, "EDGE", "10 Meters"],
            ],
        )

        arcpy.management.SelectLayerByLocation(
            in_layer=land_use_lyr,
            overlap_type="ARE_IDENTICAL_TO",
            select_features=join_lyr,
            selection_type="NEW_SELECTION",
        )
        arcpy.management.DeleteFeatures(in_features=land_use_lyr)


def snap_lines(land_use_fc: str, files: dict) -> None:
    """
    Snaps lines in the different line feature classes to corresponding land use
    polygons and erases the lines that are inside the land use polygons.

    Args:
        land_use_fc (str): The path to the land use feature class
        files (dict): A dictionary with all the files as variables
    """
    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=land_use_fc,
        out_layer=land_use_lyr,
    )

    for line_fc in LINE.values():
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=land_use_lyr,
            selection_type="NEW_SELECTION",
            where_clause=f"arealdekke IN ({WATER_SQL})",
        )
        arcpy.edit.Snap(
            in_features=line_fc,
            snap_environment=[[land_use_lyr, "EDGE", "10 Meters"]],
        )
        arcpy.analysis.Erase(
            in_features=line_fc,
            erase_features=land_use_lyr,
            out_feature_class=files[Names.erased],
        )
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=land_use_lyr,
            selection_type="NEW_SELECTION",
            where_clause=f"arealdekke IN ({IMPORTANT_SQL})",
        )
        arcpy.analysis.Erase(
            in_features=files[Names.erased],
            erase_features=land_use_lyr,
            out_feature_class=line_fc,
        )

        line_lyr = "line_lyr"
        arcpy.management.MakeFeatureLayer(
            in_features=line_fc,
            out_layer=line_lyr,
        )
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=line_lyr,
            selection_type="NEW_SELECTION",
            where_clause="Shape_Length < 5",
        )
        arcpy.management.DeleteFeatures(in_features=line_lyr)


# =======================

if __name__ == "__main__":
    # Example usage
    land_use_fc = Arealdekke_N10.arealdekke_class_final__n10_land_use.value
    data_orc = InputDataOrchestrator(map_scale="N10", pipeline="land_use")
    post_process_lines(land_use_fc=land_use_fc, data_orc=data_orc)
