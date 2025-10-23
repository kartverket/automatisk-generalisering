# Importing packages
from collections import defaultdict
from itertools import combinations
from tqdm import tqdm

import arcpy
import numpy as np
import math
import os

arcpy.env.overwriteOutput = True

# Importing custom input files modules
from input_data import input_n100

# Importing custom modules
from file_manager.n100.file_manager_roads import Road_N100
from env_setup import environment_setup
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools import custom_arcpy

from generalization.n100.road.dam import get_endpoints

data_files = {
    # Stores all the relevant file paths to the geodata used in this Python file
    "input": Road_N100.data_preparation___smooth_road___n100_road.value,
    "junction_point": Road_N100.road_triangles__junction_point__n100_road.value,
    "working_file": Road_N100.road_triangles__working_file__n100_road.value,
    "dissolved": Road_N100.road_triangles__dissolved__n100_road.value,
    "splitted": Road_N100.road_triangles__splitted__n100_road.value,
    "selection": Road_N100.road_triangles__road_selection__n100_road.value,
    "candidates": Road_N100.road_triangles__triangle_candidates__n100_road.value,
}

files_to_delete = [
    # Stores all the keys from 'data_files' that should be deleted in the end
]


@timing_decorator
def main():
    """ """
    print()
    road_dissolving()
    road_selection()
    find_road_triangles()
    # Deletes all the intermediate files created during the process
    delete_intermediate_files()
    print()


##################
# Help functions
##################


def create_junction_points(road_fc: str, junction_fc: str, tolerance: int = 2) -> None:
    """
    Creates junction points at road intersections and stores them in a feature class.

    Args:
        road_fc (str): Path to the input road feature class
        junction_fc (str): Path to the output junction points feature class
        tolerance (int, optional): Minimum number of roads that must meet at a junction to be considered valid (default: 2)
    """
    end_points = defaultdict(set)

    with arcpy.da.SearchCursor(road_fc, ["OID@", "SHAPE@"]) as cursor:
        for oid, geom in cursor:
            start, end = get_endpoints(geom)
            start, end = start.firstPoint, end.firstPoint
            start, end = (round(start.X, 3), round(start.Y, 3)), (
                round(end.X, 3),
                round(end.Y, 3),
            )
            end_points[start].add(oid)
            end_points[end].add(oid)

    junctions = {point for point, oids in end_points.items() if len(oids) > tolerance}

    if junctions:
        spatial_ref = arcpy.Describe(road_fc).spatialReference
        if arcpy.Exists(junction_fc):
            arcpy.management.Delete(junction_fc)
        arcpy.management.CreateFeatureclass(
            out_path=os.path.dirname(junction_fc),
            out_name=os.path.basename(junction_fc),
            geometry_type="POINT",
            spatial_reference=spatial_ref,
        )
        arcpy.management.AddField(junction_fc, "road_count", "LONG")
        arcpy.management.AddField(junction_fc, "road_oids", "text", field_length=255)
        with arcpy.da.InsertCursor(
            junction_fc, ["SHAPE@", "road_count", "road_oids"]
        ) as insert_cursor:
            for point in tqdm(junctions, desc="Creating junction points", colour="yellow", leave=False):
                point_geom = arcpy.PointGeometry(
                    arcpy.Point(point[0], point[1]), spatial_ref
                )
                road_oids = list(end_points[point])
                insert_cursor.insertRow(
                    [point_geom, len(road_oids), ",".join(map(str, road_oids))]
                )
        # Sletter duplikate punkt, men da må en være sikker på 100% topologisk korrekthet
        #arcpy.management.DeleteIdentical(junction_fc, ["Shape"], xy_tolerance="5 Meters")


##################
# Main functions
##################


@timing_decorator
def road_dissolving() -> None:
    """
    Dissolves road features based on their 'objtype' and 'medium' attributes.
    """

    road_fc = data_files["input"]
    working_fc = data_files["working_file"]
    junctions_fc = data_files["junction_point"]
    dissolved_fc = data_files["dissolved"]
    splitted_fc = data_files["splitted"]

    arcpy.management.CopyFeatures(road_fc, working_fc)

    create_junction_points(road_fc=working_fc, junction_fc=junctions_fc)

    arcpy.management.Dissolve(
        in_features=working_fc,
        out_feature_class=dissolved_fc,
        dissolve_field=["objtype", "medium"],
        multi_part="SINGLE_PART",
        unsplit_lines="DISSOLVE_LINES",
    )
    arcpy.management.SplitLineAtPoint(
        in_features=dissolved_fc,
        out_feature_class=splitted_fc,
        point_features=junctions_fc,
        search_radius="0 Meters",
    )


@timing_decorator
def road_selection() -> None:
    """
    Selects the road features that meet the following criterias:
    - Object type is 'VegSenterlinje' (road centerline)
    - Road length is less than 500 meters
    """
    road_fc = data_files["splitted"]
    selection_fc = data_files["selection"]

    tolerance = 200 # [m]

    arcpy.management.MakeFeatureLayer(road_fc, "road_lyr")
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view="road_lyr",
        selection_type="NEW_SELECTION",
        where_clause=f"objtype = 'VegSenterlinje' AND Shape_Length < {tolerance}",
    )
    arcpy.management.CopyFeatures("road_lyr", selection_fc)
    arcpy.management.Delete("road_lyr")


@timing_decorator
def find_road_triangles() -> None:
    """
    Finds road triangles where three small road segments form a triangle.
    """
    road_fc = data_files["selection"]
    junctions_fc = data_files["junction_point"]
    candidates_fc = data_files["candidates"]

    create_junction_points(road_fc, junctions_fc, tolerance=0)

    junctions = {oid: oids.split(',') for oid, count, oids in arcpy.da.SearchCursor(junctions_fc, ["OID@", "road_count", "road_oids"]) if count > 1}

    road_to_junc = defaultdict(set)
    for junc_oid, road_oids in tqdm(junctions.items(), desc="Mapping roads to junctions", colour="yellow", leave=False):
        for road_oid in road_oids:
            road_to_junc[road_oid].add(junc_oid)

    roads = list(road_to_junc.keys())
    triangles = set()

    for a, b, c in tqdm(combinations(roads, 3), desc="Finding road triangles", colour="yellow", leave=False):
        # Finds all junctions shared between the three roads
        # Each pair of roads must share a junction to form a triangle
        ab = road_to_junc[a] & road_to_junc[b]
        bc = road_to_junc[b] & road_to_junc[c]
        ca = road_to_junc[c] & road_to_junc[a]
        
        if not (ab and bc and ca):
            continue
        
        # Check if the junctions are distinct
        found_distinct = False
        for j_ab in tqdm(ab, desc="Checking junctions for distinctness", colour="green", leave=False):
            for j_bc in bc:
                for j_ca in ca:
                    if len({j_ab, j_bc, j_ca}) == 3:
                        found_distinct = True
                        break
                if found_distinct:
                    break
            if found_distinct:
                break
        
        if found_distinct:
            triangles.add(tuple(sorted([a, b, c])))
    
    if not triangles:
        print("No road triangles found.")
        return

    roads_in_triangles = set()
    for tri in tqdm(triangles, desc="Collecting roads in triangles", colour="yellow", leave=False):
        roads_in_triangles.update(tri)

    road_shapes = {}
    with arcpy.da.SearchCursor(road_fc, ["OID@", "SHAPE@"]) as cursor:
        for oid, geom in cursor:
            if str(oid) in roads_in_triangles:
                road_shapes[str(oid)] = geom
    
    spatial_ref = arcpy.Describe(road_fc).spatialReference
    if arcpy.Exists(candidates_fc):
        arcpy.management.Delete(candidates_fc)
    
    arcpy.management.CreateFeatureclass(
        out_path=os.path.dirname(candidates_fc),
        out_name=os.path.basename(candidates_fc),
        geometry_type="POLYLINE",
        spatial_reference=spatial_ref,
    )

    with arcpy.da.InsertCursor(candidates_fc, ["SHAPE@"]) as insert_cursor:
        for road in tqdm(roads_in_triangles, desc="Inserting road triangle candidates", colour="yellow", leave=False):
            insert_cursor.insertRow([road_shapes[road]])

@timing_decorator
def prioritize_road_segments_in_triangles() -> None:
    """
    Prioritizes road segments that are part of road triangles and removes the least important segment from the network.
    """
    candidates_fc = data_files["candidates"]
    working_fc = data_files["working_file"]
    return

@timing_decorator
def delete_intermediate_files() -> None:
    """
    Deletes the intermediate files used during the process.
    """
    for file in files_to_delete:
        arcpy.management.Delete(data_files[file])


if __name__ == "__main__":
    main()
