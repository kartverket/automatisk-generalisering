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

1) Run this code to get the modified point layer (feature class).
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
    - 'Preserve small-sized features must be turned on
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

    municipalities = [
        "Larvik",
        "Sandefjord",
        "Færder",
        "Tønsberg",
        "Horten",
        "Holmestrand",
    ]  # "Lom" # "Ullensvang" # "Klepp" ["Larvik", "Sandefjord", "Færder", "Tønsberg", "Horten", "Holmestrand"]

    # Sets up work file manager and creates temporary files
    working_fc = Landform_N10.hoydetall__n10_landforms.value
    work_config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=work_config)

    files = create_wfm_gdbs(wfm=wfm)

    fetch_data(files=files, area=municipalities)
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

    wfm.delete_created_files()

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
    out_of_bounds_dissolved = wfm.build_file_path(
        file_name="out_of_bounds_dissolved", file_type="gdb"
    )
    temporary_file = wfm.build_file_path(file_name="temporary_file", file_type="gdb")
    annotation_contours = wfm.build_file_path(
        file_name="contour_annotations", file_type="gdb"
    )
    point_2km = wfm.build_file_path(file_name="point_2km", file_type="gdb")
    dbscan = wfm.build_file_path(file_name="dbscan", file_type="gdb")
    join = wfm.build_file_path(file_name="join", file_type="gdb")

    return {
        "contours": contours,
        "out_of_bounds_polygons": out_of_bounds_polygons,
        "out_of_bounds_polylines": out_of_bounds_polylines,
        "out_of_bounds_buffers": out_of_bounds_buffers,
        "out_of_bounds_dissolved": out_of_bounds_dissolved,
        "temporary_file": temporary_file,
        "annotation_contours": annotation_contours,
        "point_2km": point_2km,
        "dbscan": dbscan,
        "join": join,
    }


@timing_decorator
def fetch_data(files: dict, area: list = None) -> None:
    """
    Collects relevant data and clips it to desired area if required.

    Args:
        files (dict): Dictionary with all the working files
        area (list, optional): List of municipality name(s) to clip data to (defaults to None)
    """
    # Fetch relevant data
    contour_lyr = "contour_lyr"
    building_lyr = "building_lyr"
    land_use_lyr = "land_use_lyr"
    train_lyr = "train_lyr"
    road_lyr = "road_lyr"

    arcpy.management.MakeFeatureLayer(
        in_features=input_n10.Contours, out_layer=contour_lyr
    )
    arcpy.management.MakeFeatureLayer(
        in_features=input_n10.Buildings, out_layer=building_lyr
    )
    arcpy.management.MakeFeatureLayer(
        in_features=input_n50.ArealdekkeFlate,
        out_layer=land_use_lyr,
        where_clause="OBJTYPE IN ('BymessigBebyggelse', 'ElvBekk', 'FerskvannTørrfall', 'Havflate', 'Industriområde', 'Innsjø', 'InnsjøRegulert', 'Tettbebyggelse')",
    )
    arcpy.management.MakeFeatureLayer(in_features=input_n50.Bane, out_layer=train_lyr)
    arcpy.management.MakeFeatureLayer(
        in_features=input_roads.road_output_1, out_layer=road_lyr
    )

    def process_layer(
        in_lyr: str,
        out_fc: str,
        clip_boundary: str = None,
        temp_fc: str = None,
        append: bool = False,
    ) -> None:
        """
        Clip and appends, or copies the input layer to the output layer.
        """
        if clip_boundary:
            # Clip til kommune
            arcpy.analysis.PairwiseClip(
                in_features=in_lyr,
                clip_features=clip_boundary,
                out_feature_class=temp_fc if append else out_fc,
            )
            if append:
                arcpy.management.Append(
                    inputs=temp_fc, target=out_fc, schema_type="NO_TEST"
                )
        else:
            # Ingen kommune: bare kopier eller append
            if append:
                arcpy.management.Append(
                    inputs=in_lyr, target=out_fc, schema_type="NO_TEST"
                )
            else:
                arcpy.management.CopyFeatures(
                    in_features=in_lyr, out_feature_class=out_fc
                )

    if area:
        # Fetch municipality boundary
        area_lyr = "area_lyr"
        arcpy.management.MakeFeatureLayer(
            in_features=input_n100.AdminFlate, out_layer=area_lyr
        )
        vals = ",".join([f"'{v}'" for v in area])
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=area_lyr,
            selection_type="NEW_SELECTION",
            where_clause=f"NAVN IN ({vals})",
        )

        # 1) Contours
        process_layer(
            in_lyr=contour_lyr, out_fc=files["contours"], clip_boundary=area_lyr
        )

        # 2) Building + Train
        for lyr, out_fc in zip(
            [building_lyr, train_lyr],
            [files["out_of_bounds_polygons"], files["out_of_bounds_polylines"]],
        ):
            process_layer(in_lyr=lyr, out_fc=out_fc, clip_boundary=area_lyr)
        for lyr, out_fc in zip(
            [land_use_lyr, road_lyr],
            [files["out_of_bounds_polygons"], files["out_of_bounds_polylines"]],
        ):
            process_layer(
                in_lyr=lyr,
                out_fc=out_fc,
                clip_boundary=area_lyr,
                temp_fc=files["temporary_file"],
                append=True,
            )
    else:
        # Save all data to working geodatabases
        process_layer(in_lyr=contour_lyr, out_fc=files["contours"])
        for lyr, out_fc in zip(
            [building_lyr, train_lyr],
            [files["out_of_bounds_polygons"], files["out_of_bounds_polylines"]],
        ):
            process_layer(in_lyr=lyr, out_fc=out_fc)
        for lyr, out_fc in zip(
            [land_use_lyr, road_lyr],
            [files["out_of_bounds_polygons"], files["out_of_bounds_polylines"]],
        ):
            process_layer(in_lyr=lyr, out_fc=out_fc, append=True)


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
    arcpy.analysis.PairwiseDissolve(
        in_features=files["out_of_bounds_polygons"],
        out_feature_class=files["out_of_bounds_dissolved"],
        dissolve_field=[],
        multi_part="MULTI_PART",
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
    join_fc = files["join"]

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
    for cid, cluster in tqdm(
        enumerate(clusters), desc="Create cluster mapping", colour="yellow", leave=False
    ):
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
    for cid, height_dict in tqdm(
        cluster_groups.items(),
        desc="Detect points to delete",
        colour="yellow",
        leave=False,
    ):
        for height, pts in height_dict.items():
            if len(pts) > 1:
                for p in pts[1:]:
                    to_delete.add(p)

    with arcpy.da.UpdateCursor(points_fc, ["OID@"]) as cur:
        for row in cur:
            if row[0] in to_delete:
                cur.deleteRow()

    for cluster, height in tqdm(
        cluster_groups.items(),
        desc="Update cluster groups",
        colour="yellow",
        leave=False,
    ):
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
    for cid, height_dict in tqdm(
        cluster_groups.items(),
        desc="Create ladder mapping",
        colour="yellow",
        leave=False,
    ):
        for oids in height_dict.values():
            for oid in oids:
                result[cid].append(oid)

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
    contour_fc = files["join"]

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

    return ladders


@timing_decorator
def move_ladders_to_valid_area(files: dict, ladders: dict) -> dict:
    """
    Move the ladders into valid positions.

    Approach:
        For each ladder, do the following:
            1) Start by finding the lowest valid point
            2) For each remaining point: find a valid position
                as close to the starting point as possible
            3) If a point do not have a valid position (either
                the starting point or other) within 2000 m, it
                is deleted

    Args:
        files (dict): Dictionary with all the working files
        ladders (dict): Dictionary with all the ladders, {ladder_id: [id1, id2, ...], ...}

    Returns:
        dict: Modified ladder overview
    """
    max_movement = 1000  # [m]

    points_fc = files["point_2km"]
    join_fc = files["join"]
    ob_fc = files["out_of_bounds_dissolved"]

    # 1) Build OB geometry
    geoms = []
    with arcpy.da.SearchCursor(ob_fc, ["SHAPE@"]) as cur:
        for row in cur:
            geoms.append(row[0])
    ob_geom = geoms[0].union(geoms[1:]) if len(geoms) > 1 else geoms[0]

    # 2) Load all the data once
    all_points = {
        oid: (pt, h)
        for oid, pt, h in arcpy.da.SearchCursor(points_fc, ["OID@", "SHAPE@", "HØYDE"])
    }
    all_lines = {
        oid: line_geom
        for oid, line_geom in arcpy.da.SearchCursor(join_fc, ["JOIN_FID", "SHAPE@"])
    }

    # 3) Prepare global updates
    updated_positions = {}
    oids_to_delete = set()

    # 4) Iterate through all ladders
    for ladder_id, oids in tqdm(
        ladders.items(), desc="Move ladders", colour="yellow", leave=False
    ):
        if len(oids) == 0:
            continue

        # Extract points
        pts = {oid: all_points[oid] for oid in oids}
        lines = {oid: all_lines[oid] for oid in oids}

        # Sort
        sorted_pts = sorted(pts.items(), key=lambda x: x[1][1])

        # Find starting point
        starting_point = None
        starting_oid = None

        for oid, (pt, _) in tqdm(
            sorted_pts, desc="Find valid starting point", colour="green", leave=False
        ):
            new_pos = find_valid_position_along_contour(
                point_geom=pt,
                contour_geom=lines[oid],
                ob_geom=ob_geom,
                max_dist=max_movement,
            )
            if new_pos:
                starting_point = new_pos
                starting_oid = oid
                updated_positions[oid] = new_pos
                break
            else:
                oids_to_delete.add(oid)

        if starting_point is None:
            # All points invalid
            oids_to_delete.update(oids)
            continue

        # Move remaining points
        for oid, (pt, _) in tqdm(
            sorted_pts,
            desc="Move remaining points to valid area",
            colour="green",
            leave=False,
        ):
            if oid in oids_to_delete or oid == starting_oid:
                continue
            new_pos = move_towards_starting_point(
                point_geom=pt,
                contour_geom=lines[oid],
                starting_geom=starting_point,
                ob_geom=ob_geom,
                max_dist=max_movement,
            )
            if new_pos:
                updated_positions[oid] = new_pos
            else:
                oids_to_delete.add(oid)

        # Update ladder list
        ladders[ladder_id] = [oid for oid in oids if oid not in oids_to_delete]

    # 5) Update all the points with new geometries
    with arcpy.da.UpdateCursor(points_fc, ["OID@", "SHAPE@"]) as cur:
        for oid, _ in cur:
            if oid in oids_to_delete:
                cur.deleteRow()
            elif oid in updated_positions:
                cur.updateRow([oid, updated_positions[oid]])

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
    contour_fc = files["join"]

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

    for contour_oid, pts in tqdm(
        contour_to_points.items(),
        desc="Detecting points to delete",
        colour="yellow",
        leave=False,
    ):
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
    contour_fc = files["join"]

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

    for oid, (x, y) in tqdm(
        coords.items(), desc="Building grid index", colour="yellow", leave=False
    ):
        cell = cell_for(x, y)
        grid[cell].append(oid)

    # Find neighbors using grid lookup
    neighbors = {oid: [] for oid, _ in points}

    for oid, (x, y) in tqdm(
        coords.items(), desc="Finding neighbors", colour="yellow", leave=False
    ):
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

    for oid, _ in tqdm(points, desc="Building clusters", colour="yellow", leave=False):
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


def find_valid_position_along_contour(
    point_geom: arcpy.Point,
    contour_geom: arcpy.Polyline,
    ob_geom: arcpy.Geometry,
    max_dist: int,
    step: int = 5,
) -> arcpy.Point | arcpy.PointGeometry | None:
    """
    Moves a point along a contour polyline until it finds a valid (non-OB) position.

    Args:
        point_geom (Geometry): The annotation point geometry
        contour_geom (Geometry): The contour polyline geometry
        ob_geom (arcpy.Geometry): Out of bounds geometry
        max_dist (int): Maximum distance to move along the contour
        step (int, optional): Step size in meters for searching (default: 5)

    Returns:
        Geometry or None: A valid point geometry, or None if no valid position exists
    """
    # 1) Find start position
    m0 = contour_geom.measureOnLine(point_geom)
    if m0 is None:
        return None

    # 2) Validate starting position
    if point_geom.disjoint(ob_geom):
        return point_geom

    # 3) Search in both directions
    max_m = contour_geom.length
    steps = int(max_dist // step)

    for i in range(1, steps + 1):
        offset = i * step
        m_plus = m0 + offset
        m_minus = m0 - offset

        if 0 <= m_plus and m_plus <= max_m:
            p = contour_geom.positionAlongLine(m_plus)
            if p.disjoint(ob_geom):
                return p

        if 0 <= m_minus and m_minus <= max_m:
            p = contour_geom.positionAlongLine(m_minus)
            if p.disjoint(ob_geom):
                return p

    # 4) No valid position found
    return None


def move_towards_starting_point(
    point_geom: arcpy.Point,
    contour_geom: arcpy.Polyline,
    starting_geom: arcpy.Point,
    ob_geom: arcpy.Geometry,
    max_dist: int,
    step: int = 5,
) -> arcpy.Point | arcpy.PointGeometry | None:
    """
    Moves a point along its contour towards the anchor point,
    stopping at the closest valid (non-OB) position.

    Args:
        point_geom (arcpy.Point): The point to move
        contour_geom (arcpy.Polyline): The contour to move along
        starting_geom (arcpy.Point): The starting point of the ladder
        ob_geom (arcpy.Geometry): Out-of-bounds geometry
        max_dist (int): Maximum distance to move along the contour
        step (int, optional): Step size in meters for searching (default: 5)

    Returns:
        Geometry or None: A valid point geometry, or None if no valid position exists
    """
    # 1) Find start position
    m_point = contour_geom.measureOnLine(point_geom)
    m_start = contour_geom.measureOnLine(starting_geom)

    if m_point is None or m_start is None:
        return None

    # 2) Determine direction
    direction = 1 if m_start > m_point else -1
    max_m = contour_geom.length

    # 3) If the point is already valid, keep it
    if point_geom.disjoint(ob_geom):
        return point_geom

    # 4) Step along the contour toward the starting point
    steps = int(max_dist // step)
    for i in range(1, steps + 1):
        m_new = m_point + direction * i * step
        if m_new < 0 or m_new > max_m:
            continue
        new_pos = contour_geom.positionAlongLine(m_new)
        if new_pos.disjoint(ob_geom):
            return new_pos

    return None


# ========================

if __name__ == "__main__":
    main()
