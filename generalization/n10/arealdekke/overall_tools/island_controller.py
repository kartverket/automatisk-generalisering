import arcpy

arcpy.env.overwriteOutput = True

from collections import defaultdict

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10

# ========================
# Program
# ========================


@timing_decorator
def island_controller(input_fc: str, output_fc: str) -> None:
    """
    Main function dissolving small areas (also under minimum)
    on islands too small for multiple feature classes.

    Args:
        input_fc (str): The input feature class with complete land use data
        output_fc (str): The feature class to store final output in
    """
    stat_field = "arealdekke"

    # 1) Setting up work file manager
    fc = Arealdekke_N10.island_merger__n10_land_use.value
    config = core_config.WorkFileConfig(root_file=fc)
    wfm = WorkFileManager(config=config)

    # 2) Create temporary files
    files = create_wfm_gdbs(wfm=wfm)

    # 3) Performe main program
    copy_features_and_identifies_inner_holes(input_fc=input_fc, files=files)
    find_hole_geometries(files=files)
    find_holes_with_multiple_features(files=files, stat_field=stat_field)

    if arcpy.Exists(files["relevant_holes"]):
        features_to_keep, features_to_remove = find_largest_feature_on_island(
            files=files, stat_field=stat_field
        )

        update_island_attributes(files=files, area_ids=features_to_keep)
        update_relevant_islands(
            files=files, feature_ids=features_to_remove, output_fc=output_fc
        )
    else:
        print("\nNo small polygons with multiple land use features inside.\n")
        print("Copies original data to output.")

        arcpy.management.CopyFeatures(in_features=input_fc, out_feature_class=output_fc)

    wfm.delete_created_files()


# ========================
# Main functions
# ========================


@timing_decorator
def create_wfm_gdbs(wfm: WorkFileManager) -> dict:
    """
    Creates all the temporarily files that are going to be used
    during the process of combining land use on islands.

    Args:
        wfm (WorkFileManager): The WorkFileManager instance that are keeping the files

    Returns:
        dict: A dictionary with all the files as variables
    """
    copy_of_input = wfm.build_file_path(file_name="copy_of_input", file_type="gdb")
    inner_holes = wfm.build_file_path(file_name="inner_holes", file_type="gdb")
    hole_polygons = wfm.build_file_path(file_name="hole_polygons", file_type="gdb")
    spatial_join = wfm.build_file_path(file_name="spatial_join", file_type="gdb")
    hole_statistics = wfm.build_file_path(file_name="hole_statistics", file_type="gdb")
    relevant_holes = wfm.build_file_path(file_name="relevant_holes", file_type="gdb")
    correct_attributes = wfm.build_file_path(
        file_name="correct_attributes", file_type="gdb"
    )

    return {
        "copy_of_input": copy_of_input,
        "inner_holes": inner_holes,
        "hole_polygons": hole_polygons,
        "spatial_join": spatial_join,
        "hole_statistics": hole_statistics,
        "relevant_holes": relevant_holes,
        "correct_attributes": correct_attributes,
    }


@timing_decorator
def copy_features_and_identifies_inner_holes(input_fc: str, files: dict) -> None:
    """
    Copy the original data into a separate feature class,
    add a new field on the water features where:
        - 1: polygon has inner hole
        - 0: polygon does not have inner hole
    ... and store those with in an own feature class.

    Args:
        input_fc (str): Feature class with the original land use data
        files (dict): Dictionary with all the working files
    """
    arcpy.management.CopyFeatures(
        in_features=input_fc, out_feature_class=files["copy_of_input"]
    )

    new_field = "has_hole"
    relevant_features = [
        "Ferskvann_elv_bekk",
        "Ferskvann_innsjo_tjern",
        "Ferskvann_innsjo_tjern_regulert",
        "Ferskvann_kanal",
        "Hav",
    ]

    arcpy.management.AddField(files["copy_of_input"], new_field, "SHORT")

    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["copy_of_input"], out_layer=land_use_lyr
    )

    sel_str = ",".join([f"'{x}'" for x in relevant_features])
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr,
        selection_type="NEW_SELECTION",
        where_clause=f"arealdekke IN ({sel_str})",
    )

    arcpy.management.CalculateField(
        in_table=land_use_lyr,
        field=new_field,
        expression="1 if !SHAPE!.boundary().partCount > !SHAPE!.partCount else 0",
        expression_type="PYTHON3",
    )

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr,
        selection_type="SUBSET_SELECTION",
        where_clause=f"{new_field} = 1",
    )

    arcpy.management.CopyFeatures(
        in_features=land_use_lyr, out_feature_class=files["inner_holes"]
    )


@timing_decorator
def find_hole_geometries(files: dict) -> None:
    """
    Extract hole boundaries and create own geometries of these that are of relevant size.

    Args:
        files (dict): Dictionary with all the working files
    """
    SMALLEST_MINIMUM = 150  # [m^2]
    SMALLEST_LIM = 500  # [m^2]
    RATIO_LIM = 5  # []

    arcpy.management.FeatureToPolygon(
        in_features=files["inner_holes"], out_feature_class=files["hole_polygons"]
    )

    ratio_field = "SHAPE_Ratio"
    arcpy.management.AddField(
        in_table=files["hole_polygons"], field_name=ratio_field, field_type="DOUBLE"
    )

    arcpy.management.CalculateField(
        in_table=files["hole_polygons"],
        field=ratio_field,
        expression="!shape.length! / np.sqrt(!shape.area!)",
        expression_type="PYTHON3",
        code_block="import numpy as np",
    )

    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["hole_polygons"], out_layer=land_use_lyr
    )

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr,
        selection_type="NEW_SELECTION",
        where_clause=f"SHAPE_Area < {SMALLEST_MINIMUM} OR SHAPE_Area > {SMALLEST_LIM}",
    )

    arcpy.management.DeleteFeatures(in_features=land_use_lyr)

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr,
        selection_type="NEW_SELECTION",
        where_clause=f"{ratio_field} > {RATIO_LIM}",
    )

    arcpy.management.DeleteFeatures(in_features=land_use_lyr)


@timing_decorator
def find_holes_with_multiple_features(files: dict, stat_field: str) -> None:
    """
    Detects which of the hole polygons that contains multiple land use categories.

    Args:
        files (dict): Dictionary with all the working files
        stat_field (str): Field name in statistic table
    """
    # 1) Join one to many to find every unique match between hole and land use
    arcpy.analysis.SpatialJoin(
        target_features=files["hole_polygons"],
        join_features=files["copy_of_input"],
        out_feature_class=files["spatial_join"],
        join_operation="JOIN_ONE_TO_MANY",
        match_option="CONTAINS",
    )

    # 2) Count number of features per hole
    target_field = "TARGET_FID"
    arcpy.analysis.Statistics(
        in_table=files["spatial_join"],
        out_table=files["hole_statistics"],
        statistics_fields=[[stat_field, "COUNT"]],
        case_field=target_field,
    )

    # 3) Select those with > 1 features
    stats_lyr = "stats_lyr"
    arcpy.management.MakeTableView(
        in_table=files["hole_statistics"], out_view=stats_lyr
    )

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=stats_lyr,
        selection_type="NEW_SELECTION",
        where_clause=f"COUNT_{stat_field} > 1",
    )

    # 4) Store the relevant holes in an own feature class
    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["hole_polygons"], out_layer=land_use_lyr
    )

    fids = [row[0] for row in arcpy.da.SearchCursor(stats_lyr, [target_field])]

    if len(fids) > 0:
        fids_str = ",".join(f"{str(x)}" for x in fids)

        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=land_use_lyr,
            selection_type="NEW_SELECTION",
            where_clause=f"OBJECTID IN ({fids_str})",
        )

        arcpy.management.CopyFeatures(
            in_features=land_use_lyr, out_feature_class=files["relevant_holes"]
        )


@timing_decorator
def find_largest_feature_on_island(files: dict, stat_field: str) -> tuple:
    """
    For each of the detected relevant island, find the features with largest area.

    Args:
        files (dict): Dictionary with all the working files
        stat_field (str): Field name in statistic table

    Returns:
        tuple:
            - dict: Dictionary with island oid as key and feature oid with largest area inside as value
            - set: A set with object ID for all features inside relevant islands
    """
    relevant_oids = set(
        oid
        for oid, stat in arcpy.da.SearchCursor(
            files["hole_statistics"], ["TARGET_FID", f"COUNT_{stat_field}"]
        )
        if stat > 1
    )

    island_features = defaultdict(list)
    feature_collection = set()
    feature_areas = dict()

    with arcpy.da.SearchCursor(
        files["spatial_join"], ["TARGET_FID", "JOIN_FID"]
    ) as search:
        for target, join in search:
            if target not in relevant_oids:
                continue
            island_features[target].append(join)
            feature_collection.add(join)

    with arcpy.da.SearchCursor(
        files["copy_of_input"], ["OID@", "SHAPE_Area"]
    ) as search:
        for oid, area in search:
            if oid not in feature_collection:
                continue
            feature_areas[oid] = area

    to_keep = dict()
    for island, features in island_features.items():
        areas = [[oid, feature_areas[oid]] for oid in features]
        areas = sorted(areas, key=lambda x: x[1])
        areas.sort(key=lambda x: x[1], reverse=True)
        to_keep[island] = areas[0][0]

    return to_keep, feature_collection


@timing_decorator
def update_island_attributes(files: dict, area_ids: dict) -> None:
    """
    Sets the attributes of the island equal the largest inner polygon.

    Args:
        files (dict): Dictionary with all the working files
        area_ids (dict): Connection between islands and inner polygons
    """
    fields = [f.name for f in arcpy.ListFields(files["copy_of_input"])]
    fields = fields[2:-3]

    unique_islands = set(oid for oid in area_ids.keys())
    unique_ids = set(oid for oid in area_ids.values())

    info = dict()
    with arcpy.da.SearchCursor(files["copy_of_input"], ["OID@"] + fields) as search:
        for row in search:
            if row[0] not in unique_ids:
                continue
            info[row[0]] = row[1:]

    with arcpy.da.UpdateCursor(files["hole_polygons"], ["OID@"] + fields) as update:
        for row in update:
            if row[0] not in unique_islands:
                continue
            feature_id = area_ids[row[0]]
            data_to_update = [row[0]] + list(info[feature_id])
            update.updateRow(data_to_update)

    sel_str = ",".join(map(str, unique_islands))

    islands_lyr = "islands_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["hole_polygons"], out_layer=islands_lyr
    )

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=islands_lyr,
        selection_type="NEW_SELECTION",
        where_clause=f"OBJECTID IN ({sel_str})",
    )

    arcpy.management.CopyFeatures(
        in_features=islands_lyr, out_feature_class=files["correct_attributes"]
    )


@timing_decorator
def update_relevant_islands(files: dict, feature_ids: set, output_fc: str):
    """
    Erases the relevant island geometries from the input data and replaces these holes with the updated island polygons.

    Args:
        files (dict): Dictionary with all the working files
        feature_ids (set): Set of object IDS that should be removed
        output_fc (str): The feature class to store the final data
    """
    islands_lyr = "islands_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["copy_of_input"], out_layer=islands_lyr
    )

    sel_str = ",".join(map(str, feature_ids))

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=islands_lyr,
        selection_type="NEW_SELECTION",
        where_clause=f"OBJECTID IN ({sel_str})",
    )

    arcpy.management.DeleteFeatures(in_features=islands_lyr)

    arcpy.management.Merge(
        inputs=[files["copy_of_input"], files["correct_attributes"]], output=output_fc
    )
