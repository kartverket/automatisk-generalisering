# Libraries

import arcpy

arcpy.env.overwriteOutput = True

import numpy as np
import os

from tqdm import tqdm

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from file_manager import WorkFileManager
from file_manager.n100.file_manager_land_use import Land_Use_N100
from input_data import input_fkb, input_n50

# ========================
# Program
# ========================

@timing_decorator
def main():
    """
    The main program that is generalizing runways from FKB and N50 to N100.
    """
    print("\nGeneralizes runways!\n")

    # Sets up the work file manager and creates temporarily files
    working_fc = Land_Use_N100.rullebane__n100_land_use.value
    config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=config)

    files = create_wfm_gdbs(wfm=wfm)

    find_runways(files=files)
    overlaps = match_runways(files=files)
    create_runway_centerline(files=files, overlaps=overlaps)

    print()

# ========================
# Main functions
# ========================

@timing_decorator
def create_wfm_gdbs(wfm: WorkFileManager) -> dict:
    """
    Creates all the temporarily files that are going to
    be used during the process of generalizing runways.

    Args:
        wfm (WorkFileManager): The WorkFileManager instance that are keeping the files

    Returns:
        dict: A dictionary with all the files as variables
    """
    runway_line = wfm.build_file_path(file_name="runway_line", file_type="gdb")
    runway_poly = wfm.build_file_path(file_name="runway_poly", file_type="gdb")
    runway_n50 = wfm.build_file_path(file_name="runway_n50", file_type="gdb")
    line_join = wfm.build_file_path(file_name="line_join", file_type="gdb")
    poly_join = wfm.build_file_path(file_name="poly_join", file_type="gdb")
    dissolved_runway = wfm.build_file_path(file_name="dissolved_runway", file_type="gdb")
    new_runway_centerline = wfm.build_file_path(file_name="new_runway_centerline", file_type="gdb")

    return {
        "runway_line": runway_line,
        "runway_poly": runway_poly,
        "runway_n50": runway_n50,
        "line_join": line_join,
        "poly_join": poly_join,
        "dissolved_runway": dissolved_runway,
        "new_runway_centerline": new_runway_centerline
    }

@timing_decorator
def find_runways(files: dict) -> None:
    """
    Fetches all the data for runways, both lines and polygons, FKB and N50.

    Args:
        files (dict): Dictionary with all the working files
    """
    airport_line_lyr = "airport_line_lyr"
    airport_poly_lyr = "airport_poly_lyr"
    arcpy.management.MakeFeatureLayer(in_features=input_fkb.fkb_lufthavn_grense, out_layer=airport_line_lyr)
    arcpy.management.MakeFeatureLayer(in_features=input_fkb.fkb_lufthavn_omrade, out_layer=airport_poly_lyr)

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=airport_line_lyr,
        selection_type="NEW_SELECTION",
        where_clause="informasjon = 'FKB50: Kodet om fra Rullebanegrense'"
    )
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=airport_poly_lyr,
        selection_type="NEW_SELECTION",
        where_clause="objtype = 'Rullebane'"
    )

    arcpy.management.Dissolve(
        in_features=airport_line_lyr,
        out_feature_class=files["runway_line"],
        dissolve_field=[],
        multi_part="SINGLE_PART",
        unsplit_lines="UNSPLIT_LINES"
    )

    arcpy.management.CopyFeatures(in_features=airport_poly_lyr, out_feature_class=files["runway_poly"])

    airport_n50_lyr = "airport_n50_lyr"
    arcpy.management.MakeFeatureLayer(in_features=input_n50.ArealdekkeFlate, out_layer=airport_n50_lyr)

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=airport_n50_lyr,
        selection_type="NEW_SELECTION",
        where_clause="OBJTYPE = 'Rullebane'"
    )

    arcpy.management.CopyFeatures(in_features=airport_n50_lyr, out_feature_class=files["runway_n50"])

@timing_decorator
def match_runways(files: dict) -> dict:
    """
    Matches runway polygons from N50 with the FKB data and labels it depending on
    overlap with either polygons or lines, where polygons have the highest priority.

    Args:
        files (dict): Dictionary with all the working files

    Returns:
        dict: {runway_id: {"poly": [poly_ids], "line": [line_ids]}}
    """
    runway_fc = files["runway_n50"]
    line_fc = files["runway_line"]
    poly_fc = files["runway_poly"]
    line_join = files["line_join"]
    poly_join = files["poly_join"]

    # Adds the new field
    fields = [f.name for f in arcpy.ListFields(runway_fc)]
    if "connection" not in fields:
        arcpy.management.AddField(runway_fc, "connection", "TEXT")
    arcpy.management.CalculateField(runway_fc, "connection", "'None'", "PYTHON3")

    overlaps = {
        row[0]: {"poly": [], "line": []}
        for row in arcpy.da.SearchCursor(runway_fc, ["OID@"])
    }
    
    # Finds overlap with polygons
    arcpy.analysis.SpatialJoin(
        target_features=runway_fc,
        join_features=poly_fc,
        out_feature_class=poly_join,
        join_operation="JOIN_ONE_TO_MANY",
        match_option="INTERSECT",
    )
    
    # Finds overlap with lines
    arcpy.analysis.SpatialJoin(
        target_features=runway_fc,
        join_features=line_fc,
        out_feature_class=line_join,
        join_operation="JOIN_ONE_TO_MANY",
        match_option="INTERSECT",
    )
    
    # Fill polygon matches
    with arcpy.da.SearchCursor(poly_join, ["TARGET_FID", "JOIN_FID"]) as cursor:
        for runway_id, poly_id in cursor:
            if poly_id != -1:
                overlaps[runway_id]["poly"].append(poly_id)

    # Fill line matches
    with arcpy.da.SearchCursor(line_join, ["TARGET_FID", "JOIN_FID"]) as cursor:
        for runway_id, line_id in cursor:
            if line_id != -1:
                overlaps[runway_id]["line"].append(line_id)

    return overlaps

@timing_decorator
def create_runway_centerline(files: dict, overlaps: dict) -> None:
    """
    Adds new runway lines to a specific file. This, or these lines are the center line of the runway.

    Args:
        files (dict): Dictionary with all the working files
        dict: {runway_id: {"poly": [poly_ids], "line": [line_ids]}} - overview of the runways to generalize
    """
    new_file = files["new_runway_centerline"]
    create_centerline_layer(new_file, files["runway_n50"])

    for key in tqdm(overlaps, desc="Adding runway lines", colour="yellow", leave=False):
        if overlaps[key]["poly"]:
            centerline_poly(key, overlaps[key]["poly"], new_file, files)
        elif overlaps[key]["line"]:
            centerline_line(key, overlaps[key]["line"], new_file, files)
        else:
            centerline_none(key, new_file, files)

# ========================
# Helper functions
# ========================

def create_dissolved_buffer(in_layer: str, buffer_layer: str, dissolved_layer: str, buffer_dist: int=20) -> None:
    """
    Create dissolved buffers.

    Args:
        in_layer (str): The layer with features to make buffers around
        buffer_layer (str): The layer to store buffers
        dissolved_layer (str): The layr to store dissolved buffers
        buffer_dist (optional, int): Distance for the buffer, default = 20 m
    """
    arcpy.analysis.Buffer(
        in_features=in_layer,
        out_feature_class=buffer_layer,
        buffer_distance_or_field=buffer_dist,
        line_side="FULL",
        line_end_type="ROUND",
        dissolve_field=[]
    )
    
    arcpy.management.Dissolve(
        in_features=buffer_layer,
        out_feature_class=dissolved_layer,
        dissolve_field=[],
        multi_part="SINGLE_PART"
    )

def create_centerline_layer(file_name: str, ref_file_name: str) -> None:
    """
    Creates the new feature class for storing the centerlines.

    Args:
        file_name (str): The path and name of the new feature class
        ref_file_name (str): The reference file for spatial reference
    """
    spatial_ref = arcpy.Describe(ref_file_name).spatialReference

    if spatial_ref:
        arcpy.management.CreateFeatureclass(
            out_path=os.path.dirname(file_name),
            out_name=os.path.basename(file_name),
            geometry_type="POLYLINE",
            spatial_reference=spatial_ref
        )

        fields = [
            ("runway_id", "LONG")
        ]

        if fields:
            for field_name, field_type in fields:
                arcpy.management.AddField(file_name, field_name, field_type)

def centerline_poly(runway_id: int, poly_ids: list, file_name: str, files: dict) -> None:
    """
    Creates centerlines for runways based on FKB polygons.

    Args:
        runway_id (int): The runway ID from N50
        poly_ids (list): List of polygon IDs from FKB that matches the runway
        file_name (str): The path and name of the new feature class
        files (dict): Dictionary with all the working files
    """
    # Fetch polygons
    oid_field = arcpy.Describe(files["runway_poly"]).OIDFieldName
    sql = f"{oid_field} IN ({', '.join(map(str, poly_ids))})"
    runway_poly_layer = "runway_poly_layer"
    arcpy.management.MakeFeatureLayer(files["runway_poly"], runway_poly_layer, sql)

    # Dissolve the features
    dissolved = arcpy.management.Dissolve(
        in_features=runway_poly_layer,
        out_feature_class=files["dissolved_runway"],
        dissolve_field=[],
        multi_part="SINGLE_PART"
    )

    for row in arcpy.da.SearchCursor(dissolved, ["SHAPE@"]):
        geom = row[0]

        # Generalize
        tolerance = max(0.2, geom.extent.width * 0.02)
        simplified = geom.generalize(tolerance)
        boundary = simplified.boundary()

        # Fetch all points
        pts = []
        for part in boundary:
            for p in part:
                if p:
                    pts.append((p.X, p.Y))
        
        # Cluster
        eps = min(max(geom.extent.width, geom.extent.height) * 0.2, 200)
        clusters = cluster_points(pts, eps=eps, min_pts=1)
        
        # Calculate center points
        centers = [cluster_center(c) for c in clusters]
        
        # Creates new runway centerlines
        if len(centers) >= 2:
            pairs = all_furthest_pair(centers)
            for p1, p2 in pairs:
                line = points_to_polyline([p1, p2], geom.spatialReference)
                with arcpy.da.InsertCursor(file_name, ["SHAPE@", "runway_id"]) as ic:
                    ic.insertRow([line, runway_id])

def centerline_line(runway_id: str, line_ids: list, file_name: str, files: dict) -> None:
    """
    ...
    """
    return

def centerline_none(runway_id: str, file_name: str, files: dict) -> None:
    """
    ...
    """
    return

def euclid(p1: list, p2: list) -> float:
    """
    Calculates the Euclidean distance between two points.

    Args:
        p1 (list): The first point as (x, y)
        p2 (list): The second point as (x, y)

    Returns:
        float: The Euclidean distance between the two points
    """
    return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def cluster_points(points, eps, min_pts) -> list:
    """
    Clusters a list of points using DBSCAN algorithm.

    Args:
        points (list): List of points as (x, y)
        eps (float): The maximum distance between two points to be considered neighbors
        min_pts (int): The minimum number of points required to form a cluster

    Returns:
        list: A list of clusters, where each cluster is a list of points
    """
    clusters = []
    visited = set()
    assigned = set()
    
    def region_query(p):
        return [q for q in points if euclid(p, q) <= eps]
    
    for p in points:
        if p in visited:
            continue

        neighbors = region_query(p)

        if len(neighbors) < min_pts:
            visited.add(p)
            continue
        
        cluster = []
        clusters.append(cluster)

        cluster.append(p)
        visited.add(p)
        assigned.add(p)

        while neighbors:
            n = neighbors.pop()
            if n not in visited:
                visited.add(n)
                n_neighbors = region_query(n)
                if len(n_neighbors) >= min_pts:
                    neighbors.extend(n_neighbors)
            if n not in assigned:
                cluster.append(n)
                assigned.add(n)
    
    clusters = [c for c in clusters if len(c) >= min_pts]

    return clusters

def cluster_center(points) -> tuple:
    """
    Calculates the center of a cluster of points.

    Args:
        points (list): List of points as (x, y)

    Returns:
        tuple: The center point as (x, y)
    """
    cx = sum(p[0] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)
    return (cx, cy)

def all_furthest_pair(points: list) -> list:
    """
    Estimates multiple pairs of points that are the furthest apart and
    at the same time following the original structure of the geometry.

    Strategy:
    1. Find the two points that are the furthest apart, weighing in support
       from other points that are close to the line between the two points.
    2. Remove these two points from the list of points.
    3. Repeat until there are less than two points left.

    Args:
        points (list): List of points as (x, y)

    Returns:
        list: A list of point pairs [(p1, p2), ...] (p1 = (x, y))
    """
    if len(points) < 2:
        return None
    
    pairs = []

    while len(points) >= 2:
        best_pair = None
        best_score = -1
        best_indices = None

        for i in range(len(points)):
            for j in range(i + 1, len(points)):
                p1, p2 = points[i], points[j]
                d = euclid(points[i], points[j])
                support = 0
                for k, p in enumerate(points):
                    if k in (i, j):
                        continue
                    if point_line_distance(p, p1, p2) < 50:
                        support += 1
                score = d * (1 + support)
                if score > best_score:
                    best_score = score
                    best_pair = (p1, p2)
                    best_indices = (i, j)

        pairs.append(best_pair)

        i, j = best_indices
        for idx in sorted([i, j], reverse=True):
            points.pop(idx)

    return pairs

def points_to_polyline(points: list, spatial_ref: object) -> arcpy.Polyline:
    """
    Creates a Polyline from a list of points.

    Args:
        points (list): List of points as (x, y)
        spatial_ref (object): Spatial reference for the polyline

    Returns:
        arcpy.Polyline: The created polyline
    """
    arr = arcpy.Array([arcpy.Point(x, y) for x, y in points])
    return arcpy.Polyline(arr, spatial_ref)

def point_line_distance(p: tuple, a: tuple, b: tuple) -> float:
    """
    Calculates the shortest distance from point p to the line defined by points a and b.
    
    Args:
        p (tuple): The point as (x, y)
        a (tuple): The first point of the line as (x, y)
        b (tuple): The second point of the line as (x, y)

    Returns:
        float: The shortest distance from point p to the line ab
    """
    # p, a, b er (x, y)
    px, py = p
    ax, ay = a
    bx, by = b

    # Linjevektor
    dx = bx - ax
    dy = by - ay

    # Hvis a og b er samme punkt
    if dx == 0 and dy == 0:
        return euclid(p, a)

    # Parameter t for projeksjon
    t = ((px - ax) * dx + (py - ay) * dy) / (dx*dx + dy*dy)

    # Nærmeste punkt på linjen
    nx = ax + t * dx
    ny = ay + t * dy

    return euclid(p, (nx, ny))

# ========================

if __name__ == "__main__":
    main()
