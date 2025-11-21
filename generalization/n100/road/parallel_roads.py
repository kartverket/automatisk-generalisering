# Importing packages
import arcpy

from collections import defaultdict
from tqdm import tqdm

arcpy.env.overwriteOutput = True

from composition_configs import core_config
from constants.n100_constants import FieldNames_str
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools.custom_arcpy import OverlapType, SelectionType
from file_manager import WorkFileManager
from file_manager.n100.file_manager_roads import Road_N100

from custom_tools.generalization_tools.road.remove_road_triangles import (
    endpoints_of,
    sort_prioritized_hierarchy,
)

# File overview
input_fc = Road_N100.data_preparation___resolve_road_conflicts___n100_road.value
working_fc = Road_N100.parallel_roads__n100_road.value


@timing_decorator
def generalize_parallel_roads() -> None:
    """
    Generalizes the road data by removing or adjusting parallel roads.
    """
    print("\nGeneralizing of parallel roads started!\n")
    # Create WorkFileManager
    config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=config)

    file_storage = create_wfm_gdbs(wfm=wfm)

    # Prepare the data with dissolve and removal of small instances
    original_geometries, road_data = data_preparation(
        input_fc=input_fc,
        dissolved_fc=file_storage["dissolved_fc"],
        join_fc=file_storage["join_fc"],
    )

    # Create buffer around dissolved roads and identify overlapping roads
    buffered_overlapping_roads(
        dissolved_fc=file_storage["dissolved_fc"],
        buffer_fc=file_storage["buffer_fc"],
        intersect_fc=file_storage["intersect_fc"],
        dissolved_buffer_fc=file_storage["dissolved_buffer_fc"],
        join_fc=file_storage["join_fc"],
        clip_fc=file_storage["clip_fc"],
        single_part_fc=file_storage["single_part_fc"],
        oid_to_data=road_data,
    )

    # Remove small instances from the dataset
    #clean_small_instances(dissolved_fc=file_storage["dissolved_fc"], priority=road_data)

    # wfm.delete_created_files()

    print()


##################
# Help functions
##################


def fetch_original_data(input_fc: str) -> dict:
    """
    Creates a dictionary that contains the original geometries.

    Args:
        input_fc (str): Path to the featureclass containing the original data

    Returns:
        dict: Dictionary where key is oid and value original geometry
    """
    oid_to_geom = {}
    with arcpy.da.SearchCursor(
        input_fc, ["OID@", "SHAPE@", "vegkategori", "vegklasse", "Shape_Length"]
    ) as search_cursor:
        for oid, geom, vegkategori, vegklasse, length in search_cursor:
            if geom is None:
                continue
            oid_to_geom[oid] = [vegkategori, vegklasse, length, geom]
    return oid_to_geom


def dissolve_road_features(input_fc: str, dissolved_fc: str) -> None:
    arcpy.management.Dissolve(
        in_features=input_fc,
        out_feature_class=dissolved_fc,
        dissolve_field=["medium"],
        multi_part="SINGLE_PART",
    )


def fetch_road_data(
    oid_to_geom: dict, input_fc: str, join_fc: str, dissolved_fc: str
) -> dict:
    """ """
    oid_to_data = defaultdict(list)

    arcpy.analysis.SpatialJoin(
        target_features=dissolved_fc,
        join_features=input_fc,
        out_feature_class=join_fc,
        join_operation="JOIN_ONE_TO_MANY",
        join_type="KEEP_ALL",
        match_option="SHARE_A_LINE_SEGMENT_WITH",
    )

    with arcpy.da.SearchCursor(join_fc, ["SHAPE@", "TARGET_FID", "ORIG_FID"]) as search_cursor:
        for geom, dissolved_oid, road_oid in search_cursor:
            if road_oid in oid_to_geom:
                oid_to_data[dissolved_oid].append(oid_to_geom[road_oid] + [geom])

    for oid, data in oid_to_data.items():
        oid_to_data[oid] = sort_prioritized_hierarchy(data)[0]

    return oid_to_data


##################
# Main functions
##################


@timing_decorator
def create_wfm_gdbs(wfm: WorkFileManager) -> dict:
    """ """
    dissolved_fc = wfm.build_file_path(
        file_name="dissolved_roads",
        file_type="gdb",
    )
    join_fc = wfm.build_file_path(
        file_name="spatial_joined_roads",
        file_type="gdb",
    )
    buffer_fc = wfm.build_file_path(
        file_name="buffered_roads",
        file_type="gdb",
    )
    intersect_fc = wfm.build_file_path(
        file_name="intersected_buffers",
        file_type="gdb",
    )
    dissolved_buffer_fc = wfm.build_file_path(
        file_name="dissolved_buffers",
        file_type="gdb",
    )
    clip_fc = wfm.build_file_path(
        file_name="clipped_roads",
        file_type="gdb",
    )
    single_part_fc = wfm.build_file_path(
        file_name="single_part_roads",
        file_type="gdb",
    )

    return {
        "dissolved_fc": dissolved_fc,
        "join_fc": join_fc,
        "buffer_fc": buffer_fc,
        "intersect_fc": intersect_fc,
        "dissolved_buffer_fc": dissolved_buffer_fc,
        "clip_fc": clip_fc,
        "single_part_fc": single_part_fc,
    }


@timing_decorator
def data_preparation(
    input_fc: str, dissolved_fc: str, join_fc: str
) -> tuple[dict, dict]:
    """ """
    # Collect the original geometries for final match when storing the data
    original_geometries = fetch_original_data(input_fc=input_fc)

    dissolve_road_features(input_fc=input_fc, dissolved_fc=dissolved_fc)

    # Fetch road data for hierarchy sorting
    if arcpy.Exists(join_fc):
        arcpy.management.Delete(join_fc)
    road_data = fetch_road_data(
        oid_to_geom=original_geometries,
        input_fc=input_fc,
        join_fc=join_fc,
        dissolved_fc=dissolved_fc,
    )

    return original_geometries, road_data


@timing_decorator
def buffered_overlapping_roads(
    dissolved_fc: str, buffer_fc: str, intersect_fc: str, dissolved_buffer_fc: str, join_fc: str, clip_fc: str, single_part_fc: str, oid_to_data: dict
) -> defaultdict[list]:
    """ """
    arcpy.analysis.Buffer(
        in_features=dissolved_fc,
        out_feature_class=buffer_fc,
        buffer_distance_or_field="30 Meters",
        line_side="FULL",
        line_end_type="FLAT",
        dissolve_option="NONE",
        method="PLANAR",
    )

    arcpy.analysis.Intersect(
        in_features=[buffer_fc],
        out_feature_class=intersect_fc,
        join_attributes="ALL",
        cluster_tolerance=None,
        output_type="INPUT",
    )

    arcpy.management.Dissolve(
        in_features=intersect_fc,
        out_feature_class=dissolved_buffer_fc,
        dissolve_field=[],
        multi_part="SINGLE_PART",
    )

    arcpy.analysis.Clip(
        in_features=dissolved_fc,
        clip_features=dissolved_buffer_fc,
        out_feature_class=clip_fc,
    )

    arcpy.management.MultipartToSinglepart(
        in_features=clip_fc,
        out_feature_class=single_part_fc,
    )

    if arcpy.Exists(join_fc):
        arcpy.management.Delete(join_fc)
    arcpy.analysis.SpatialJoin(
        target_features=single_part_fc,
        join_features=dissolved_buffer_fc,
        out_feature_class=join_fc,
        join_operation="JOIN_ONE_TO_MANY",
        join_type="KEEP_ALL",
        match_option="INTERSECT",
    )

    grouped = defaultdict(list)
    fields = ["JOIN_FID", "SHAPE@", "Shape_Length"]
    with arcpy.da.SearchCursor(join_fc, fields) as search_cursor:
        for buf_id, geom, length in search_cursor:
            if geom is not None:
                if length > 100:
                    grouped[buf_id].append(geom)
    
    for key in tqdm(grouped.keys(), desc="Collects complete geometry of overlapping roads", colour="yellow", leave=False):
        for i in range(len(grouped[key])):
            for idx in oid_to_data:
                if oid_to_data[idx][-1].overlaps(grouped[key][i]):
                    grouped[key][i] = oid_to_data[idx][-1]


@timing_decorator
def clean_small_instances(dissolved_fc: str, priority: dict) -> None:
    """ """
    # Create feature layer for selection
    short_roads = r"short_roads_lyr"
    arcpy.management.MakeFeatureLayer(dissolved_fc, short_roads, "Shape_Length < 100")
    relevant_roads = r"relevant_roads_lyr"
    arcpy.management.MakeFeatureLayer(dissolved_fc, relevant_roads)
    arcpy.management.SelectLayerByLocation(
        in_layer=relevant_roads,
        overlap_type="INTERSECT",
        select_features=short_roads,
        selection_type="NEW_SELECTION",
    )

    # Finds all short roads connected to junctions in every end
    endpoint_collection = defaultdict(list)
    with arcpy.da.SearchCursor(relevant_roads, ["OID@", "SHAPE@"]) as search_cursor:
        for oid, geom in search_cursor:
            s, e = endpoints_of(geom)
            for pnt in [s, e]:
                endpoint_collection[pnt].append(oid)

    for key in endpoint_collection:
        endpoint_collection[key].append(len(endpoint_collection[key]))

    remove_pnts = {}
    with arcpy.da.UpdateCursor(short_roads, ["OID@", "SHAPE@"]) as update_cursor:
        for oid, geom in update_cursor:
            s, e = endpoints_of(geom)
            control = 0
            for pnt in [s, e]:
                if pnt in endpoint_collection:
                    if endpoint_collection[pnt][-1] > 2:
                        control += 1
            if control == 2:
                remove_pnts[oid] = [s, e]
                update_cursor.deleteRow()

    print(len(remove_pnts))

    road_to_move = {}
    for oid, pnts in remove_pnts.items():
        roads = set()
        for pnt in pnts:
            for road_oid in endpoint_collection[pnt][:-1]:
                roads.add(road_oid)
        road_to_move[oid] = roads


##################
# Run program
##################

if __name__ == "__main__":
    generalize_parallel_roads()
