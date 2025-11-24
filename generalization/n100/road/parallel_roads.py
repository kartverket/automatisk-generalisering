# Importing packages
import arcpy
import hashlib
import os

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
    grouped_roads = buffered_overlapping_roads(
        dissolved_fc=file_storage["dissolved_fc"],
        buffer_fc=file_storage["buffer_fc"],
        intersect_fc=file_storage["intersect_fc"],
        dissolved_buffer_fc=file_storage["dissolved_buffer_fc"],
        join_fc=file_storage["join_fc"],
        clip_fc=file_storage["clip_fc"],
        single_part_fc=file_storage["single_part_fc"],
        nearby_roads_fc=file_storage["nearby_roads_fc"],
        oid_to_data=road_data,
    )

    """
    simplify_road_geometry(
        dissolved_fc=file_storage["dissolved_fc"],
        grouped_roads=grouped_roads,
        oid_to_data=road_data,
        dissolved_buffer_fc=file_storage["dissolved_buffer_fc"],
    )
    """
    wfm.delete_created_files()

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
        input_fc,
        ["OID@", "SHAPE@", "vegkategori", "vegklasse", "medium", "Shape_Length"],
    ) as search_cursor:
        for oid, geom, vegkategori, vegklasse, medium, length in search_cursor:
            if geom is None:
                continue
            oid_to_geom[oid] = [vegkategori, vegklasse, length, medium, geom]
    return oid_to_geom


def fetch_road_data(
    oid_to_geom: dict, input_fc: str, join_fc: str, dissolved_fc: str
) -> dict:
    """ """
    oid_to_data = defaultdict(list)

    if arcpy.Exists(join_fc):
        arcpy.management.Delete(join_fc)
    arcpy.analysis.SpatialJoin(
        target_features=dissolved_fc,
        join_features=input_fc,
        out_feature_class=join_fc,
        join_operation="JOIN_ONE_TO_MANY",
        join_type="KEEP_ALL",
        match_option="SHARE_A_LINE_SEGMENT_WITH",
    )

    with arcpy.da.SearchCursor(
        join_fc, ["SHAPE@", "TARGET_FID", "ORIG_FID"]
    ) as search_cursor:
        for geom, dissolved_oid, road_oid in search_cursor:
            if road_oid in oid_to_geom:
                oid_to_data[dissolved_oid].append(oid_to_geom[road_oid] + [geom])

    for oid, data in tqdm(
        oid_to_data.items(),
        desc="Finding least important road",
        colour="yellow",
        leave=False,
    ):
        oid_to_data[oid] = sort_prioritized_hierarchy(data)[-1]

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
    nearby_roads_fc = wfm.build_file_path(
        file_name="nearby_roads",
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
        "nearby_roads_fc": nearby_roads_fc,
    }


@timing_decorator
def data_preparation(
    input_fc: str, dissolved_fc: str, join_fc: str
) -> tuple[dict, dict]:
    """ """
    # Collect the original geometries for final match when storing the data
    original_geometries = fetch_original_data(input_fc=input_fc)

    arcpy.management.Dissolve(
        in_features=input_fc,
        out_feature_class=dissolved_fc,
        dissolve_field=["medium"],
        multi_part="SINGLE_PART",
    )

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
    dissolved_fc: str,
    buffer_fc: str,
    intersect_fc: str,
    dissolved_buffer_fc: str,
    join_fc: str,
    clip_fc: str,
    single_part_fc: str,
    nearby_roads_fc: str,
    oid_to_data: dict,
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

    for key in tqdm(
        grouped.keys(),
        desc="Collects complete geometry of overlapping roads",
        colour="yellow",
        leave=False,
    ):
        for i in range(len(grouped[key])):
            for k in oid_to_data:
                if grouped[key][i].within(oid_to_data[k][-1]):
                    grouped[key][i] = oid_to_data[k][-1]

    if arcpy.Exists(nearby_roads_fc):
        arcpy.management.Delete(nearby_roads_fc)
    arcpy.management.CreateFeatureclass(
        out_path=os.path.dirname(nearby_roads_fc),
        out_name=os.path.basename(nearby_roads_fc),
        geometry_type="POLYLINE",
        spatial_reference=arcpy.Describe(dissolved_fc).spatialReference,
    )

    with arcpy.da.InsertCursor(nearby_roads_fc, ["SHAPE@"]) as insert_cursor:
        for key in tqdm(
            grouped.keys(), desc="Stores nearby roads", colour="yellow", leave=False
        ):
            for geom in grouped[key]:
                insert_cursor.insertRow([geom])

    arcpy.management.DeleteIdentical(nearby_roads_fc, ["Shape"])

    return grouped


@timing_decorator
def simplify_road_geometry(
    dissolved_fc: str,
    grouped_roads: defaultdict[list],
    oid_to_data: dict,
    dissolved_buffer_fc: str,
) -> None:
    """ """
    buffers = "dissolved_buffers_lyr"
    arcpy.management.MakeFeatureLayer(dissolved_buffer_fc, buffers)

    seen_geometries = set()

    for buf_oid, group in tqdm(
        grouped_roads.items(),
        desc="Simplifies road geometries",
        colour="yellow",
        leave=False,
    ):
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=buffers,
            selection_type="NEW_SELECTION",
            where_clause=f"OBJECTID = {buf_oid}",
        )
        with arcpy.da.SearchCursor(buffers, ["SHAPE@"]) as search_cursor:
            for row in search_cursor:
                buffer_geom = row[0]
                break
        if buffer_geom == None:
            continue

        working_group = []
        for geom in group:
            hashed_geom = hashlib.md5(geom.WKB).hexdigest()
            if hashed_geom not in seen_geometries:
                working_group.append(geom)
                seen_geometries.add(hashed_geom)

        if len(working_group) < 1:
            continue

        elif len(working_group) == 1:
            # Do someting
            continue

        else:
            # Assummes that there are two geometries to simplify
            s1, e1 = endpoints_of(working_group[0], num=None)
            s2, e2 = endpoints_of(working_group[1], num=None)
            all_outside = all(not pnt.within(buffer_geom) for pnt in [s1, e1, s2, e2])
            connection = False
            for pnt1 in [s1, e2]:
                for pnt2 in [s2, e2]:
                    if pnt1 == pnt2:
                        connection = True
                        break
                if connection:
                    break

            if not all_outside and connection:
                continue
            else:
                continue


##################
# Run program
##################

if __name__ == "__main__":
    generalize_parallel_roads()
