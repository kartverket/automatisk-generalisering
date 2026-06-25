# Libraries

import arcpy

arcpy.env.overwriteOutput = True

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10

scale_settings = {
    "N10": "10000",
    "N50": "50000",
    "N100": "100000",
    "N250": "200000",
    "N500": "500000",
}

# ========================
# Main function
# ========================


@timing_decorator
def aggregate_category(input_fc: str, output_fc: str, map_scale: str):
    working_fc = Arealdekke_N10.category_aggregator__n10_land_use.value
    config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=config)

    arcpy.env.referenceScale = scale_settings[map_scale]

    files = create_wfm_gdbs(wfm=wfm)

    data_selection(input_fc=input_fc, files=files)
    find_holes_of_target(files=files)

    arcpy.cartography.DelineateBuiltUpAreas(
        in_buildings=files["target"],
        edge_features=files["near_filtered"],
        grouping_distance=20,
        minimum_detail_size=10,
        out_feature_class=files["aggregated"],
        minimum_building_count=1,
    )

    rewrite_attribute_info(files=files)

    arcpy.management.CopyFeatures(
        in_features=files["copy_of_input"],
        out_feature_class=output_fc,
    )

    wfm.delete_created_files()


# ========================
# Helper functions
# ========================


def create_wfm_gdbs(wfm: WorkFileManager) -> dict:
    """
    Creates all the temporary files that are going to
    be used during the process of area aggregation.

    Args:
        wfm (WorkFileManager): The WorkFileManager instance that are keeping the files

    Returns:
        dict: A dictionary with all the files as variables
    """
    return {
        "copy_of_input": wfm.build_file_path(
            file_name="copy_of_input", file_type="gdb"
        ),
        "target": wfm.build_file_path(file_name="target", file_type="gdb"),
        "near": wfm.build_file_path(file_name="near", file_type="gdb"),
        "others": wfm.build_file_path(file_name="others", file_type="gdb"),
        "near_filtered": wfm.build_file_path(
            file_name="near_filtered", file_type="gdb"
        ),
        "aggregated": wfm.build_file_path(file_name="aggregated", file_type="gdb"),
        "spatial_join": wfm.build_file_path(file_name="spatial_join", file_type="gdb"),
    }


def data_selection(input_fc: str, files: dict) -> None:
    """
    Selects and copies relevant data into separate feature classes.

    Args:
        input_fc (str): Feature class with input data
        files (dict): Dictionary with all the working files
    """
    arcpy.management.CopyFeatures(
        in_features=input_fc, out_feature_class=files["copy_of_input"]
    )

    land_use_lyr = "land_use_lyr"
    arcpy.MakeFeatureLayer_management(
        in_features=files["copy_of_input"], out_layer=land_use_lyr
    )

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr,
        selection_type="NEW_SELECTION",
        where_clause="arealdekke = 'Høyblokkbebyggelse'",
    )
    arcpy.management.CopyFeatures(
        in_features=land_use_lyr, out_feature_class=files["target"]
    )

    arcpy.management.SelectLayerByLocation(
        in_layer=land_use_lyr,
        overlap_type="BOUNDARY_TOUCHES",
        select_features=files["target"],
        selection_type="NEW_SELECTION",
    )
    arcpy.analysis.Erase(
        in_features=land_use_lyr,
        erase_features=files["target"],
        out_feature_class=files["near"],
    )

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr, selection_type="SWITCH_SELECTION"
    )
    arcpy.management.CopyFeatures(
        in_features=land_use_lyr, out_feature_class=files["others"]
    )


def find_holes_of_target(files: dict) -> None:
    """
    Filter the near features to contain only built up areas or areas with inner holes that are elements of the target category.

    Args:
        files (dict): Dictionary with all the working files
    """
    land_use_lyr = "land_use_lyr"
    arcpy.MakeFeatureLayer_management(in_features=files["near"], out_layer=land_use_lyr)

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr,
        selection_type="NEW_SELECTION",
        where_clause="arealdekke = 'Bebygd'",
    )
    arcpy.management.CopyFeatures(
        in_features=land_use_lyr, out_feature_class=files["near_filtered"]
    )

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr, selection_type="SWITCH_SELECTION"
    )

    target_geoms = [
        row[0] for row in arcpy.da.SearchCursor(files["target"], ["SHAPE@"])
    ]
    target_union = target_geoms[0]
    for g in target_geoms[1:]:
        target_union = target_union.union(g)

    with arcpy.da.InsertCursor(files["near_filtered"], ["SHAPE@"]) as icur:
        with arcpy.da.SearchCursor(land_use_lyr, ["SHAPE@"]) as cur:
            for row in cur:
                geom = row[0]
                if geom.boundary().partCount > 1:
                    for i in range(1, geom.boundary().partCount):
                        hole = arcpy.Polygon(
                            geom.boundary().getPart(i),
                            spatial_reference=geom.spatialReference,
                        )
                        if hole.intersect(target_union, 4):
                            icur.insertRow([geom])
                            break


def rewrite_attribute_info(files: dict) -> None:
    """
    Changes attribute information of overlapping geometries to fit with new status.

    Args:
        files (dict): Dictionary with all the working files
    """
    target_geoms = [
        row[0] for row in arcpy.da.SearchCursor(files["aggregated"], ["SHAPE@"])
    ]
    target_union = target_geoms[0]
    for g in target_geoms[1:]:
        target_union = target_union.union(g)

    with arcpy.da.UpdateCursor(files["near_filtered"], ["SHAPE@"]) as cur:
        for row in cur:
            geom = row[0]
            overlap = geom.intersect(target_union, 4).area
            if overlap == 0:
                cur.deleteRow()

    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["copy_of_input"], out_layer=land_use_lyr
    )
    arcpy.management.SelectLayerByLocation(
        in_layer=land_use_lyr,
        overlap_type="ARE_IDENTICAL_TO",
        select_features=files["near_filtered"],
        selection_type="NEW_SELECTION",
    )

    with arcpy.da.UpdateCursor(land_use_lyr, ["arealdekke"]) as cur:
        for _ in cur:
            cur.updateRow(["Høyblokkbebyggelse"])
