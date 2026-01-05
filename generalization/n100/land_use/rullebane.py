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
    remove_noisy_runway_lines(files=files)

    output_fc = Land_Use_N100.rullebane_output__n100_land_use.value
    arcpy.management.CopyFeatures(
        in_features=files["new_runway_centerline"], out_feature_class=output_fc
    )

    wfm.delete_created_files()

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
    dissolved_runway = wfm.build_file_path(
        file_name="dissolved_runway", file_type="gdb"
    )
    new_runway_centerline = wfm.build_file_path(
        file_name="new_runway_centerline", file_type="gdb"
    )
    temporarily_layer = wfm.build_file_path(
        file_name="temporarily_layer", file_type="gdb"
    )

    return {
        "runway_line": runway_line,
        "runway_poly": runway_poly,
        "runway_n50": runway_n50,
        "line_join": line_join,
        "poly_join": poly_join,
        "dissolved_runway": dissolved_runway,
        "new_runway_centerline": new_runway_centerline,
        "temporarily_layer": temporarily_layer,
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
    arcpy.management.MakeFeatureLayer(
        in_features=input_fkb.fkb_lufthavn_grense, out_layer=airport_line_lyr
    )
    arcpy.management.MakeFeatureLayer(
        in_features=input_fkb.fkb_lufthavn_omrade, out_layer=airport_poly_lyr
    )

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=airport_line_lyr,
        selection_type="NEW_SELECTION",
        where_clause="informasjon = 'FKB50: Kodet om fra Rullebanegrense'",
    )
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=airport_poly_lyr,
        selection_type="NEW_SELECTION",
        where_clause="objtype = 'Rullebane'",
    )

    arcpy.management.Dissolve(
        in_features=airport_line_lyr,
        out_feature_class=files["runway_line"],
        dissolve_field=[],
        multi_part="SINGLE_PART",
        unsplit_lines="UNSPLIT_LINES",
    )

    arcpy.management.CopyFeatures(
        in_features=airport_poly_lyr, out_feature_class=files["runway_poly"]
    )

    airport_n50_lyr = "airport_n50_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=input_n50.ArealdekkeFlate, out_layer=airport_n50_lyr
    )

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=airport_n50_lyr,
        selection_type="NEW_SELECTION",
        where_clause="OBJTYPE = 'Rullebane'",
    )

    arcpy.management.CopyFeatures(
        in_features=airport_n50_lyr, out_feature_class=files["runway_n50"]
    )


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
        if overlaps[key]["poly"] and overlaps[key]["line"]:
            centerline_poly(key, overlaps[key]["poly"], new_file, files)
            centerline_line(key, overlaps[key]["line"], new_file, files)
        elif overlaps[key]["poly"]:
            centerline_poly(key, overlaps[key]["poly"], new_file, files)
        elif overlaps[key]["line"]:
            centerline_line(key, overlaps[key]["line"], new_file, files)
        else:
            centerline_none(key, new_file, files)


@timing_decorator
def remove_noisy_runway_lines(files: dict) -> None:
    """
    Removes unnecessary runway lines.

    Runways are removed based on the following rules:
    - All runways shorter than 200 m are removed
    After this, for each group of overlapping runways:
    - Keep the longest runway
    runway lines that are shorter than a given length.

    Args:
        files (dict): Dictionary with all the working files
    """
    centerlines_lyr = "centerlines_lyr"
    arcpy.management.MakeFeatureLayer(files["new_runway_centerline"], centerlines_lyr)

    n50_count = int(arcpy.management.GetCount(files["runway_n50"]).getOutput(0))

    with arcpy.da.SearchCursor(files["runway_n50"], ["SHAPE@"]) as search_cursor:
        for row in tqdm(
            search_cursor,
            total=n50_count,
            desc="Removing noisy runway lines",
            colour="yellow",
            leave=False,
        ):
            runway_geom = row[0]

            if runway_geom is None:
                continue

            arcpy.management.CopyFeatures(runway_geom, files["temporarily_layer"])
            arcpy.management.SelectLayerByLocation(
                in_layer=centerlines_lyr,
                overlap_type="INTERSECT",
                select_features=files["temporarily_layer"],
                selection_type="NEW_SELECTION",
            )

            lines = []

            with arcpy.da.SearchCursor(
                centerlines_lyr, ["OID@", "SHAPE@", "Shape_Length"]
            ) as line_cursor:
                for oid, geom, length in line_cursor:
                    if length > 200.0:
                        lines.append(
                            {
                                "oid": oid,
                                "geom": geom,
                                "length": length,
                                "dir": line_direction(geom),
                            }
                        )

            keep = set()

            if lines:
                main_line = max(lines, key=lambda x: x["length"])
                keep.add(main_line["oid"])

                for l in lines:
                    if l["oid"] == main_line["oid"]:
                        continue
                    dist = l["geom"].distanceTo(main_line["geom"])
                    ang = angle_difference(l["dir"], main_line["dir"])

                    # Rule 1: Keep if far enough away and long enough
                    if dist > 500 and l["length"] > 500:
                        keep.add(l["oid"])

                    # Rule 2: Keep if different direction and long enough
                    elif ang > 60:
                        if l["length"] >= 1000:
                            keep.add(l["oid"])
                    elif ang > 30:
                        if l["length"] >= 300:
                            keep.add(l["oid"])

            with arcpy.da.UpdateCursor(centerlines_lyr, ["OID@"]) as update_cursor:
                for row in update_cursor:
                    oid = row[0]
                    if oid not in keep:
                        update_cursor.deleteRow()

            arcpy.management.Delete(files["temporarily_layer"])


# ========================
# Helper functions
# ========================


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
            spatial_reference=spatial_ref,
        )

        fields = [("runway_id", "LONG")]

        if fields:
            for field_name, field_type in fields:
                arcpy.management.AddField(file_name, field_name, field_type)


def centerline_poly(
    runway_id: int, poly_ids: list, file_name: str, files: dict
) -> None:
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
        multi_part="SINGLE_PART",
    )

    create_centerlines(featureClass=dissolved, runway_id=runway_id, file_name=file_name)


def centerline_line(
    runway_id: int, line_ids: list, file_name: str, files: dict
) -> None:
    """
    Creates centerlines for runways based on FKB lines.

    Args:
        runway_id (int): The runway ID from N50
        line_ids (list): List of line IDs from FKB that matches the runway
        file_name (str): The path and name of the new feature class
        files (dict): Dictionary with all the working files
    """
    # Fetch lines
    oid_field = arcpy.Describe(files["runway_line"]).OIDFieldName
    sql = f"{oid_field} IN ({', '.join(map(str, line_ids))})"
    runway_line_layer = "runway_line_layer"
    arcpy.management.MakeFeatureLayer(files["runway_line"], runway_line_layer, sql)

    # Dissolve the features
    dissolved = arcpy.management.Dissolve(
        in_features=runway_line_layer,
        out_feature_class=files["dissolved_runway"],
        dissolve_field=[],
        multi_part="MULTI_PART",
    )

    create_centerlines(
        featureClass=dissolved, runway_id=runway_id, file_name=file_name, polygons=False
    )


def centerline_none(runway_id: int, file_name: str, files: dict) -> None:
    """
    Creates centerlines for runways based on N50 polygons.

    Args:
        runway_id (int): The runway ID from N50
        file_name (str): The path and name of the new feature class
        files (dict): Dictionary with all the working files
    """
    # Fetch original N50 feature
    runway_original_layer = "runway_original_layer"
    oid_field = arcpy.Describe(files["runway_n50"]).OIDFieldName
    arcpy.management.MakeFeatureLayer(
        files["runway_n50"], runway_original_layer, f"{oid_field} = {runway_id}"
    )

    create_centerlines(
        featureClass=runway_original_layer, runway_id=runway_id, file_name=file_name
    )


def create_centerlines(
    featureClass: str, runway_id: int, file_name: str, polygons: bool = True
) -> None:
    """
    The part that creates the actual centerlines based on either polygons or lines.

    Args:
        featureClass (str): The feature class to create centerlines from
        runway_id (int): The runway ID from N50
        file_name (str): The path and name of the new feature class
        polygons (bool, optional): Whether the feature class is polygons or lines, defaults to True
    """
    for row in arcpy.da.SearchCursor(featureClass, ["SHAPE@"]):
        geom = row[0]

        if geom is None:
            continue

        # Generalize
        if polygons:
            tolerance = max(0.2, geom.extent.width * 0.02)
            simplified = geom.generalize(tolerance)
            boundary = simplified.boundary()
        else:
            boundary = geom

        # Fetch all points
        pts = []
        for i in range(boundary.partCount):
            part = boundary.getPart(i)
            for p in part:
                if p:
                    pts.append((p.X, p.Y))

        if polygons:
            # Cluster
            eps = min(max(geom.extent.width, geom.extent.height) * 0.1, 200)
            clusters = cluster_points(pts, eps=eps, min_pts=1)

            # Calculate center points
            centers = [cluster_center(c) for c in clusters]
        else:
            centers = pts

        # Creates new runway centerlines
        if len(centers) >= 2:
            pairs = all_furthest_pairs(centers) if polygons else furthest_pair(centers)
            for p1, p2 in pairs:
                line = points_to_polyline([p1, p2], geom.spatialReference)
                with arcpy.da.InsertCursor(file_name, ["SHAPE@", "runway_id"]) as ic:
                    ic.insertRow([line, runway_id])


def euclid(p1: list, p2: list) -> float:
    """
    Calculates the Euclidean distance between two points.

    Args:
        p1 (list): The first point as (x, y)
        p2 (list): The second point as (x, y)

    Returns:
        float: The Euclidean distance between the two points
    """
    return np.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


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


def furthest_pair(points: list) -> tuple:
    """
    Estimates the pair of points that are the furthest apart.

    Args:
        points (list): List of points as (x, y)

    Returns:
        tuple: A pair of points (p1, p2) (p1 = (x, y))
    """
    best_pair = None
    best_distance = -1

    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            d = euclid(points[i], points[j])
            if d > best_distance:
                best_distance = d
                best_pair = [(points[i], points[j])]

    return best_pair


def all_furthest_pairs(points: list) -> list:
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
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)

    # Nærmeste punkt på linjen
    nx = ax + t * dx
    ny = ay + t * dy

    return euclid(p, (nx, ny))


def line_direction(geom: arcpy.Polyline) -> float:
    """
    Calculates the direction (angle) of a line in degrees.

    Args:
        geom (arcpy.Polyline): The polyline geometry

    Returns:
        float: The direction of the line in degrees
    """
    first = geom.firstPoint
    last = geom.lastPoint

    dx = last.X - first.X
    dy = last.Y - first.Y

    angle = np.degrees(np.arctan2(dy, dx))

    return angle % 180


def angle_difference(angle1: float, angle2: float) -> float:
    """
    Calculates the smallest difference between two angles in degrees.

    Args:
        angle1 (float): The first angle in degrees
        angle2 (float): The second angle in degrees

    Returns:
        float: The smallest difference between the two angles in degrees
    """
    d = abs(angle1 - angle2)
    return min(d, 180 - d)


# ========================

if __name__ == "__main__":
    main()
