# Libraries

import arcpy
import numpy as np

arcpy.env.overwriteOutput = True

from collections import defaultdict
from tqdm import tqdm

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from env_setup import environment_setup
from file_manager import WorkFileManager
from file_manager.n10.file_manager_landforms import Landform_N10
from input_data import input_n10, input_n50, input_n100, input_roads

# ========================
# Program
# ========================

"""
DOCUMENTATION:

==========================================
How to use this functionality properly
==========================================

1) Run this code to get the modified point layer (feature class)
2) Open the point feature class in ArcGIS Pro
3) Select the layer, go to 'Labeling' and turn it on
4) In 'Label Class' choose 'Field' to be 'HØYDE'
5) Select font, size and colour in 'Text Symbol'
6) Open the side panel for 'Label Placement' and do the following:
    - In 'Symbol': turn the 'Halo' of
    - In 'Position':
        * Set placement to 'Centered on point' and center on symbol
        * 'Orientation' should be 'Curved'
        * 'Rotation' should be set to rotate according to the 'ROTATION' field, 0 deg, Arithmetic and Straight
        * Turn of 'Keep label upright (may flip)' ## IMPORTANT ##
7) Convert the labels to annotations:
    - Right click on the layer and choose 'Convert Labels' and '... To Annotation'
    - Zoom the map to fit the layer area
    - Set scale to 10.000
    - Extent must be the same as the map (the leftmost choice)
    -> Run
8) Choose the 'Feature Outline Mask (Cartography Tool)' function:
    - Choose input layer to be the annotation layer
    - Set 'Margin' to x m (5 m)
    - 'Mask Kind' must be 'Exact'
    - 'Preserve small-sized features' must be turned on
    -> Run

Then you have annotations with masks in ladders with correct orientation and spacing.
"""


@timing_decorator
def main():
    """
    Main function to process landforms in order to generate contour annotations at N10 scale.
    """
    environment_setup.main()

    print("\nCreates contour annotations for landforms at N10 scale...\n")

    municipalities = ["Hole"]

    # Sets up work file manager and creates temporary files
    working_fc = Landform_N10.hoydetall__n10_landforms.value
    work_config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=work_config)

    files = create_wfm_gdbs(wfm=wfm)

    fetch_data(files=files, area=municipalities)
    fetch_annotations_to_avoid(files=files, area=municipalities)
    collect_out_of_bounds_areas(files=files)
    get_annotation_contours(files=files)
    create_points_along_line(files=files)
    ladders = create_ladders(files=files)
    ladders = remove_multiple_points_for_medium_contours(files=files, ladders=ladders)
    ladders = move_ladders_to_valid_area(files=files, ladders=ladders)
    ladders = remove_dense_points(files=files, ladders=ladders)
    set_tangential_rotation(files=files)

    arcpy.management.CopyFeatures(
        in_features=files["point_2km"],
        out_feature_class=Landform_N10.hoydetall_output__n10_landforms.value,
    )

    # wfm.delete_created_files()

    print("\nContour annotations for landforms at N10 scale created successfully!\n")


# ========================
# Main functions
# ========================


@timing_decorator
def create_wfm_gdbs(wfm: WorkFileManager) -> dict:
    """
    Creates all the temporarily files that are going to be used
    during the process of creating contour annotations.

    Args:
        wfm (WorkFileManager): The WorkFileManager instance that are keeping the files

    Returns:
        dict: A dictionary with all the files as variables
    """
    contours = wfm.build_file_path(file_name="contours", file_type="gdb")
    out_of_bounds_polygons = wfm.build_file_path(
        file_name="out_of_bounds_polygons", file_type="gdb"
    )
    out_of_bounds_polylines = wfm.build_file_path(
        file_name="out_of_bounds_polylines", file_type="gdb"
    )
    out_of_bounds_buffers = wfm.build_file_path(
        file_name="out_of_bounds_buffers", file_type="gdb"
    )
    out_of_bounds_annotations = wfm.build_file_path(
        file_name="out_of_bounds_annotations", file_type="gdb"
    )
    out_of_bounds_annotation_polygons = wfm.build_file_path(
        file_name="out_of_bounds_annotation_polygons", file_type="gdb"
    )
    out_of_bounds_areas = wfm.build_file_path(
        file_name="out_of_bounds_areas", file_type="gdb"
    )
    temporary_file = wfm.build_file_path(file_name="temporary_file", file_type="gdb")
    annotation_contours = wfm.build_file_path(
        file_name="contour_annotations", file_type="gdb"
    )
    point_2km = wfm.build_file_path(file_name="point_2km", file_type="gdb")
    dbscan = wfm.build_file_path(file_name="dbscan", file_type="gdb")
    joined_contours = wfm.build_file_path(file_name="joined_contours", file_type="gdb")
    valid_contours = wfm.build_file_path(file_name="valid_contours", file_type="gdb")

    return {
        "contours": contours,
        "out_of_bounds_polygons": out_of_bounds_polygons,
        "out_of_bounds_polylines": out_of_bounds_polylines,
        "out_of_bounds_buffers": out_of_bounds_buffers,
        "out_of_bounds_annotations": out_of_bounds_annotations,
        "out_of_bounds_annotation_polygons": out_of_bounds_annotation_polygons,
        "out_of_bounds_areas": out_of_bounds_areas,
        "temporary_file": temporary_file,
        "annotation_contours": annotation_contours,
        "point_2km": point_2km,
        "dbscan": dbscan,
        "joined_contours": joined_contours,
        "valid_contours": valid_contours,
    }


@timing_decorator
def fetch_data(files: dict, area: list = None) -> None:
    """
    Collects relevant data and clips it to desired area if required.

    Args:
        files (dict): Dictionary with all the working files
        area (list, optional): List of municipality name(s) to clip data to (defaults to None)
    """
    # 1) Defining layers to use
    layers = [
        ("contour_lyr", input_n10.Contours, None, files["contours"], False),
        (
            "building_lyr",
            input_n10.Buildings,
            None,
            files["out_of_bounds_polygons"],
            False,
        ),
        (
            "land_use_lyr",
            input_n50.ArealdekkeFlate,
            "OBJTYPE IN ('BymessigBebyggelse','ElvBekk','FerskvannTørrfall','Havflate','Industriområde','Innsjø','InnsjøRegulert','Tettbebyggelse')",
            files["out_of_bounds_polygons"],
            True,
        ),
        ("train_lyr", input_n50.Bane, None, files["out_of_bounds_polylines"], False),
        (
            "road_lyr",
            input_roads.road_output_1,
            None,
            files["out_of_bounds_polylines"],
            True,
        ),
    ]

    # 2) Creating feature layers
    for name, src, sql, *_ in layers:
        arcpy.management.MakeFeatureLayer(src, name, sql)

    # 3) Defining clip area, if a chosen area exists
    clip_lyr = None
    if area:
        clip_lyr = "area_lyr"
        arcpy.management.MakeFeatureLayer(input_n100.AdminFlate, clip_lyr)
        vals = ",".join(f"'{v}'" for v in area)
        arcpy.management.SelectLayerByAttribute(
            clip_lyr, "NEW_SELECTION", f"NAVN IN ({vals})"
        )

    # 4) Process each layer
    for lyr_name, _, _, out_fc, append in tqdm(
        layers, desc="Fetching data", colour="yellow", leave=False
    ):
        process(files, lyr_name, out_fc, clip=clip_lyr, append=append)


@timing_decorator
def fetch_annotations_to_avoid(files: dict, area: list = None) -> None:
    """
    Fetches annotations that should be avoided when placing new contour annotations.

    Args:
        files (dict): Dictionary with all the working files
        area (list, optional): List of municipality name(s) to clip data to (defaults to None)
    """
    # 1) Defining layers to use
    annotation_layers = input_n10.annotations  # list of all annotation paths

    layers = []

    for i, anno in enumerate(annotation_layers):
        layers.append(
            (
                f"annotation_lyr_{i}",
                anno,
                files["out_of_bounds_annotations"],
            )
        )

    # 2) Creating feature layers
    for name, src, _ in layers:
        arcpy.management.MakeFeatureLayer(src, name)

    # 3) Defining clip area, if a chosen area exists
    clip_lyr = None
    if area:
        clip_lyr = "area_lyr"
        arcpy.management.MakeFeatureLayer(input_n100.AdminFlate, clip_lyr)
        vals = ",".join(f"'{v}'" for v in area)
        arcpy.management.SelectLayerByAttribute(
            clip_lyr, "NEW_SELECTION", f"NAVN IN ({vals})"
        )

    # 4) Process each layer and add the data in one feature class
    for lyr_name, _, out_fc in tqdm(
        layers, desc="Fetching annotations to avoid", colour="yellow", leave=False
    ):
        tmp = files["temporary_file"]
        arcpy.analysis.Clip(
            in_features=lyr_name, clip_features=clip_lyr, out_feature_class=tmp
        )
        if arcpy.Exists(out_fc):
            arcpy.management.Append(inputs=tmp, target=out_fc, schema_type="NO_TEST")
        else:
            arcpy.management.CopyFeatures(in_features=tmp, out_feature_class=out_fc)

    # 5) Fetch the bounding polygons of the annotations and store them in a separate feature class as polygons
    arcpy.management.FeatureToPolygon(
        in_features=files["out_of_bounds_annotations"],
        out_feature_class=files["out_of_bounds_annotation_polygons"],
    )


@timing_decorator
def collect_out_of_bounds_areas(files: dict) -> None:
    """
    Creates buffer around lines and dissolves all polygons without creating multiparts.

    Args:
        files (dict): Dictionary with all the working files
    """
    arcpy.analysis.Buffer(
        in_features=files["out_of_bounds_polylines"],
        out_feature_class=files["out_of_bounds_buffers"],
        buffer_distance_or_field="20 Meters",
        line_side="FULL",
        line_end_type="ROUND",
    )
    arcpy.management.Append(
        inputs=files["out_of_bounds_buffers"],
        target=files["out_of_bounds_polygons"],
        schema_type="NO_TEST",
    )
    arcpy.management.Append(
        inputs=files["out_of_bounds_annotation_polygons"],
        target=files["out_of_bounds_polygons"],
        schema_type="NO_TEST",
    )
    arcpy.analysis.Buffer(
        in_features=files["out_of_bounds_polygons"],
        out_feature_class=files["out_of_bounds_buffers"],
        buffer_distance_or_field="20 Meters",
        line_side="FULL",
        line_end_type="ROUND",
        dissolve_option="ALL",
    )
    arcpy.management.MultipartToSinglepart(
        in_features=files["out_of_bounds_buffers"],
        out_feature_class=files["out_of_bounds_areas"],
    )


@timing_decorator
def get_annotation_contours(files: dict) -> None:
    """
    Collect index contours with the specific heigth intervall.

    Args:
        files (dict): Dictionary with all the working files
    """
    contours_lyr = "contours_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["contours"],
        out_layer=contours_lyr,
    )

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=contours_lyr,
        selection_type="NEW_SELECTION",
        where_clause="MOD(HØYDE, 25) = 0",
    )

    arcpy.management.MultipartToSinglepart(
        in_features=contours_lyr,
        out_feature_class=files["annotation_contours"],
    )


@timing_decorator
def create_points_along_line(files: dict, threshold: int = 2000) -> None:
    """
    Creates a point every x m defined by the threshold.

    Args:
        files (dict): Dictionary with all the working files
        threshold (int, optionally): Distance (m) between each new point (default: 2000)
    """
    contours_lyr = "contours_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["annotation_contours"],
        out_layer=contours_lyr,
        where_clause="Shape_Length > 3000",
    )

    arcpy.management.GeneratePointsAlongLines(
        Input_Features=contours_lyr,
        Output_Feature_Class=files["point_2km"],
        Point_Placement="DISTANCE",
        Distance=f"{threshold} Meters",
        Include_End_Points="NO_END_POINTS",
        Distance_Method="GEODESIC",
    )

    count = int(arcpy.management.GetCount(files["point_2km"])[0])
    print(f"\nCreated {count} points along contours.\n")


@timing_decorator
def create_ladders(files: dict) -> dict:
    """
    Cluster the points using DBSCAN to sort the points into ladders.

    Args:
        files (dict): Dictionary with all the working files

    Returns:
        dict: A dictionary containing all the ladders, {cluster_id: [oid1, oid2, ...], ...}
    """
    points_fc = files["point_2km"]
    contours_fc = files["annotation_contours"]
    join_fc = files["joined_contours"]

    cluster_field = "CLUSTER_ID"
    height_field = "HØYDE"
    eps_distance = 500  # [m]

    # 1) Performe DBSCAN
    arcpy.management.AddField(
        in_table=points_fc, field_name=cluster_field, field_type="LONG"
    )
    points = [
        (oid, pt) for oid, pt in arcpy.da.SearchCursor(points_fc, ["OID@", "SHAPE@"])
    ]
    clusters = cluster_points(points=points, eps=eps_distance)

    # 2) Write cluster ID back to point
    cluster_id_map = {}
    for cid, cluster in enumerate(clusters):
        for oid in cluster:
            cluster_id_map[oid] = cid

    with arcpy.da.UpdateCursor(points_fc, ["OID@", cluster_field]) as cur:
        for oid, _ in cur:
            cur.updateRow([oid, cluster_id_map[oid]])

    # 3) Find points of same height in same cluster and delete these
    cluster_groups = defaultdict(lambda: defaultdict(list))
    with arcpy.da.SearchCursor(points_fc, ["OID@", cluster_field, height_field]) as cur:
        for oid, cid, height in cur:
            cluster_groups[cid][height].append(oid)

    to_delete = set()
    for cid, height_dict in cluster_groups.items():
        for height, pts in height_dict.items():
            if len(pts) > 1:
                for p in pts[1:]:
                    to_delete.add(p)

    with arcpy.da.UpdateCursor(points_fc, ["OID@"]) as cur:
        for row in cur:
            if row[0] in to_delete:
                cur.deleteRow()

    for cluster, height in cluster_groups.items():
        for oids in height.values():
            k = 0
            while k < len(oids):
                if oids[k] in to_delete:
                    oids.pop(k)
                else:
                    k += 1

    # 4) Performe spatial join to connect points with contours
    arcpy.analysis.SpatialJoin(
        target_features=contours_fc,
        join_features=points_fc,
        out_feature_class=join_fc,
        join_operation="JOIN_ONE_TO_MANY",
        match_option="INTERSECT",
    )

    # 5) Return the ladders
    result = defaultdict(list)
    for cid, height_dict in cluster_groups.items():
        for oids in height_dict.values():
            for oid in oids:
                result[cid].append(oid)

    print(f"\nCreated {len(result)} ladders and deleted {len(to_delete)} points.\n")

    return result


@timing_decorator
def remove_multiple_points_for_medium_contours(files: dict, ladders: dict) -> dict:
    """
    For contours shorter than 10 km, only the annotation
    in the longest ladder should be kept.

    Args:
        files (dict): Dictionary with all the working files
        ladders (dict): Dictionary with all the ladders, {ladder_id: [id1, id2, ...], ...}

    Returns:
        dict: Modified ladder overview
    """
    points_fc = files["point_2km"]
    contour_fc = files["joined_contours"]

    # 1) Find contours shorter than 10 km
    contour_to_points = defaultdict(list)

    with arcpy.da.SearchCursor(
        contour_fc,
        ["TARGET_FID", "JOIN_FID", "CLUSTER_ID"],
        where_clause="Shape_Length < 10000",
    ) as cur:
        for target, join, cluster in cur:
            contour_to_points[target].append((join, cluster))

    # 2) Find points to delete
    oids_to_delete = set()

    for info in contour_to_points.values():
        if len(info) == 1:
            continue
        longest = max(info, key=lambda x: len(ladders[x[1]]))
        keep_join = longest[0]
        for join_oid, cluster_id in info:
            if join_oid != keep_join:
                oids_to_delete.add(join_oid)
                ladders[cluster_id] = [
                    oid for oid in ladders[cluster_id] if oid != join_oid
                ]

    # 3) Delete points in the point layer
    if oids_to_delete:
        sql = f"OBJECTID IN ({','.join(map(str, oids_to_delete))})"
        with arcpy.da.UpdateCursor(points_fc, ["OID@"], sql) as cur:
            for _ in cur:
                cur.deleteRow()

    print(f"\nDeleted {len(oids_to_delete)} points from medium contours.\n")

    return ladders


@timing_decorator
def move_ladders_to_valid_area(files: dict, ladders: dict) -> dict:
    """
    Moves ladder points to valid positions along their associated contour lines.

    Workflow:
        1) Remove contour segments that fall inside out-of-bounds areas
        2) For each point, find the nearest valid location on its own contour,
           limited by a maximum allowed movement distance
        3) Keep points that can be moved; delete points that cannot

    Args:
        files (dict): Paths to all working feature classes
        ladders (dict): Mapping of ladder IDs to lists of point OIDs,
                        e.g. {ladder_id: [oid1, oid2, ...]}

    Returns:
        dict: Updated ladder mapping with invalid points removed
    """

    max_movement = 2000  # [m]

    points_fc = files["point_2km"]
    contour_fc = files["joined_contours"]
    ob_fc = files["out_of_bounds_areas"]
    valid_fc = files["valid_contours"]

    # 1) Erase OB areas from the contours
    arcpy.analysis.Erase(
        in_features=contour_fc, erase_features=ob_fc, out_feature_class=valid_fc
    )

    # 2) Collect point information
    point_info = {
        oid: {"near_geom": None, "geom": geom, "height": h}
        for oid, geom, h in arcpy.da.SearchCursor(
            points_fc, ["OID@", "SHAPE@", "HØYDE"]
        )
    }

    contours = {
        join_fid: geom
        for join_fid, geom in arcpy.da.SearchCursor(valid_fc, ["JOIN_FID", "SHAPE@"])
    }

    points_to_delete = set()

    for oids in ladders.values():
        oids.sort(key=lambda oid: point_info[oid]["height"])
        accumulated = []
        for _, oid in enumerate(oids):
            contour = contours.get(oid)
            if contour is None:
                points_to_delete.add(oid)
                continue

            pt_geom = point_info[oid]["geom"]

            """prev_pt = oid if i == 0 else oids[i-1]
            while prev_pt in points_to_delete and i > 0:
                i -= 1
                prev_pt = oids[i-1] if i > 0 else oid
            
            prev_geom = point_info[prev_pt]["near_geom"] if point_info[prev_pt]["near_geom"] is not None else point_info[prev_pt]["geom"]"""

            prev_geom = (
                get_accumulated_movement(accumulated)
                if len(accumulated) > 0
                else pt_geom
            )

            nearest_point, *_ = contour.queryPointAndDistance(prev_geom)
            dist_to_orig = pt_geom.distanceTo(nearest_point)

            if dist_to_orig > max_movement:
                points_to_delete.add(oid)
                continue

            point_info[oid]["near_geom"] = nearest_point
            accumulated.append(nearest_point.centroid)

    # 6) Update point geometries
    with arcpy.da.UpdateCursor(points_fc, ["OID@", "SHAPE@"]) as cur:
        for oid, _ in cur:
            if oid in points_to_delete:
                cur.deleteRow()
            else:
                if point_info[oid]["near_geom"] is None:
                    continue

                cur.updateRow([oid, point_info[oid]["near_geom"]])

    for ladder_id, oids in ladders.items():
        ladders[ladder_id] = [oid for oid in oids if oid not in points_to_delete]

    print(
        f"\nRemoved {len(points_to_delete)} points that could not be moved to valid area.\n"
    )

    return ladders


@timing_decorator
def remove_dense_points(files: dict, ladders: dict) -> dict:
    """
    Remove points that are too close to each other along the same contour.

    Args:
        files (dict): Dictionary with all the working files
        ladders (dict): Dictionary with all the ladders, {ladder_id: [id1, id2, ...], ...}

    Returns:
        dict: Updated ladder list
    """
    points_fc = files["point_2km"]
    contour_fc = files["joined_contours"]

    points = {
        oid: geom for oid, geom in arcpy.da.SearchCursor(points_fc, ["OID@", "SHAPE@"])
    }

    # 1) Build contour mapping
    contour_to_points = defaultdict(list)
    contours = {}
    with arcpy.da.SearchCursor(
        contour_fc, ["SHAPE@", "TARGET_FID", "JOIN_FID", "CLUSTER_ID"]
    ) as cur:
        for geom, target, join, cluster in cur:
            if target not in contours:
                contours[target] = geom
                ladder_size = len(ladders[cluster])
            if join in points:
                contour_to_points[target].append(
                    {"oid": join, "geom": points[join], "ladder_size": ladder_size}
                )

    # 2) Detect the points that should be deleted
    tolerance = 2000  # [m]
    oids_to_delete = set()

    for contour_oid, pts in contour_to_points.items():
        contour_geom = contours[contour_oid]

        # Estimate distance along contour
        for p in pts:
            p["dist"] = contour_geom.measureOnLine(p["geom"])

        # Sort on distance
        pts.sort(key=lambda x: x["dist"])

        # Iterate through the points along the contour
        current = pts[0]
        for p in pts[1:]:
            dist_diff = p["dist"] - current["dist"]
            large_current = current["ladder_size"] >= 4
            large_new = p["ladder_size"] >= 4

            # Rules
            # 1: Both are large = keep both
            if large_current and large_new:
                current = p
            # 2: New is large, but old is short = delete old, keep new
            elif large_new and not large_current:
                oids_to_delete.add(current["oid"])
                current = p
            # 3: Both are small or new is small = use 2km rule
            elif dist_diff < tolerance:
                oids_to_delete.add(p["oid"])
            else:
                current = p

    # 3) Delete the points
    if oids_to_delete:
        sql = f"OBJECTID IN ({','.join(map(str, oids_to_delete))})"
        with arcpy.da.UpdateCursor(points_fc, ["OID@"], where_clause=sql) as cur:
            for _ in cur:
                cur.deleteRow()

    for ladder_id, oids in ladders.items():
        ladders[ladder_id] = [oid for oid in oids if oid not in oids_to_delete]

    print(f"\nDeleted {len(oids_to_delete)} dense points along contours.\n")

    return ladders


@timing_decorator
def set_tangential_rotation(files: dict) -> None:
    """
    Set ROTATION for each point so the label aligns with
    the contour line's tangent at that location.

    Approach:
        For each point:
            1) Find the contour line it belongs to (JOIN_FID)
            2) Measure the point's position along the line
            3) Extract a small segment around that position
            4) Compute tangent direction using atan2(dy, dx)
            5) Store the angle in ROTATION (ArcGIS format)

    Args:
        files (dict): Dictionary with all the working files.
    """

    points_fc = files["point_2km"]
    contour_fc = files["joined_contours"]

    # 1) Ensure ROTATION field exists
    if "ROTATION" not in [f.name for f in arcpy.ListFields(points_fc)]:
        arcpy.management.AddField(points_fc, "ROTATION", "DOUBLE")

    # 2) Build mapping: JOIN_FID -> contour geometry
    contour_by_join = {}
    with arcpy.da.SearchCursor(contour_fc, ["JOIN_FID", "SHAPE@"]) as cur:
        for join, geom in cur:
            contour_by_join[join] = geom

    # 3) Update tangent rotation for each point
    with arcpy.da.UpdateCursor(points_fc, ["OID@", "SHAPE@", "ROTATION"]) as cur:
        for oid, pt, _ in cur:

            if oid not in contour_by_join:
                continue

            line = contour_by_join[oid]

            # 3.1) Position along line
            m = line.measureOnLine(pt)
            if m is None:
                continue

            # 3.2) Small segment around the point (±10 m)
            m1 = max(0, m - 10)
            m2 = min(line.length, m + 10)
            seg = line.segmentAlongLine(m1, m2)

            # 3.3) Compute tangent direction
            start = seg.firstPoint
            end = seg.lastPoint
            dx = end.X - start.X
            dy = end.Y - start.Y

            tangent = np.degrees(np.arctan2(dy, dx)) % 360

            # 3.4) Store rotation
            cur.updateRow([oid, pt, tangent])


# ========================
# Helper functions
# ========================


def process(
    files: dict, in_lyr: str, out_fc: str, clip: str = None, append: bool = False
) -> None:
    """
    Pre-processing function to clip or append data to a feature class.

    Args:
        files (dict): Dictionary with all the working files
        in_lyr (str): Input layer to process
        out_fc (str): Output feature class
        clip (str, optional): Feature class to use for clipping (defaults to None)
        append (bool, optional): Whether to append to existing feature class (defaults to False)
    """
    if clip:
        tmp = files["temporary_file"] if append else out_fc
        arcpy.analysis.Clip(in_lyr, clip, tmp)
        if append:
            arcpy.management.Append(tmp, out_fc, "NO_TEST")
    else:
        if append:
            arcpy.management.Append(in_lyr, out_fc, "NO_TEST")
        else:
            arcpy.management.CopyFeatures(in_lyr, out_fc)


def cluster_points(points: list, eps: int) -> list:
    """
    Proper DBSCAN-like clustering.

    Args:
        points (list): [(oid, arcpy.Point), ...]
        eps (float): distance threshold

    Returns:
        list: list of clusters, each cluster is a list of OIDs
    """
    # Precompute coordinates
    coords = {oid: (pt.centroid.X, pt.centroid.Y) for oid, pt in points}

    # Build grid index
    cell_size = eps
    grid = defaultdict(list)

    def cell_for(x, y):
        return (int(x // cell_size), int(y // cell_size))

    for oid, (x, y) in coords.items():
        cell = cell_for(x, y)
        grid[cell].append(oid)

    # Find neighbors using grid lookup
    neighbors = {oid: [] for oid, _ in points}

    for oid, (x, y) in coords.items():
        cx, cy = cell_for(x, y)

        # Check this + all 8-neighbors
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                cell = (cx + dx, cy + dy)
                if cell not in grid:
                    continue
                for other in grid[cell]:
                    if other == oid:
                        continue
                    ox, oy = coords[other]
                    if (x - ox) ** 2 + (y - oy) ** 2 <= eps**2:
                        neighbors[oid].append(other)

    # Build clusters (BFS / DFS)
    visited = set()
    clusters = []

    for oid, _ in points:
        if oid in visited:
            continue

        cluster = []
        stack = [oid]

        while stack:
            current = stack.pop()
            if current in visited:
                continue

            visited.add(current)
            cluster.append(current)

            for n in neighbors[current]:
                if n not in visited:
                    stack.append(n)

        clusters.append(cluster)

    return clusters


def get_accumulated_movement(accumulated: list) -> arcpy.PointGeometry:
    """
    Returns the average point from a list of points.

    Args:
        accumulated (list): List of arcpy.PointGeometry

    Returns:
        arcpy.PointGeometry: The average point
    """
    avg_x = sum(p.X for p in accumulated) / len(accumulated)
    avg_y = sum(p.Y for p in accumulated) / len(accumulated)
    ref_point = arcpy.PointGeometry(arcpy.Point(avg_x, avg_y))
    return ref_point


# ========================

if __name__ == "__main__":
    main()
