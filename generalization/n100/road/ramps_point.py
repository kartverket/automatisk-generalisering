# Import packages
import os
import arcpy
from collections import defaultdict
from tqdm import tqdm
import numpy as np
import math

arcpy.env.overwriteOutput = True

# Importing custom input files modules
from input_data import input_n100
from input_data import input_roads

# Importing custom modules
from file_manager.n100.file_manager_roads import Road_N100
from custom_tools.decorators.timing_decorator import timing_decorator

from dam import get_endpoints, calculate_angle, reverse_geometry

data_files = {
    # Stores all the relevant file paths to the geodata used in this Python file
    "input": Road_N100.data_preparation___road_single_part_2___n100_road.value,
    "ramps": Road_N100.ramps__ramps__n100_road.value,
    "roundabouts_1": Road_N100.ramps__collapsed_roundabouts__n100_road.value,
    "roundabouts_2": Road_N100.ramps__small_roundabouts__n100_road.value,
    "cleaned_roads": Road_N100.ramps__roads_with_cleaned_roundabouts__n100_road.value,
    "buffered_ramps": Road_N100.ramps__buffered_ramps__n100_road.value,
    "buffered_ramps_100": Road_N100.ramps__buffered_ramps_100__n100_road.value,
    "roads_near_ramps": Road_N100.ramps__roads_near_ramp__n100_road.value,
    "endpoints": Road_N100.ramps__endpoints__n100_road.value,
    "dissolved_ramps": Road_N100.ramps__dissolved_ramps__n100_road.value,
    "intermediate_ramps": Road_N100.ramps__intermediate_ramps__n100_road.value,
    "merged_ramps": Road_N100.ramps__merged_ramps__n100_road.value,
    "closest_points": Road_N100.ramps__closest_points__n100_road.value,
    "dissolved_group": Road_N100.ramps__dissolved_group__n100_road.value,
    "splitted_group": Road_N100.ramps__splitted_group__n100_road.value,
    "ramp_points": Road_N100.ramps__ramp_points__n100_road.value,
    "ramp_points_moved": Road_N100.ramps__ramp_points_moved__n100_road.value,
    "generalized_ramps": Road_N100.ramps__generalized_ramps__n100_road.value,
    "test": Road_N100.ramps__test__n100_road.value,
}

files_to_delete = [
    # Stores all the keys from 'data_files' that should be deleted in the end
    "roundabouts_1",
    "roundabouts_2",
    "roads_near_ramps",
    "endpoints",
    "dissolved_ramps",
    "intermediate_ramps",
    "dissolved_group",
    "splitted_group",
    "split_points",
]


@timing_decorator
def main():
    """
    Simplification of ramps
    """
    # add_ramps()
    fetch_roundabouts()
    clean_ramps_near_roundabouts()
    merge_ramps()
    """
    Generalization of ramps
    """
    make_ramp_points()
    """
    Deletes all the intermediate files created during the process
    """
    # delete_intermediate_files()


##################
# Help functions
##################


def get_center_point(geoms: list[arcpy.Geometry]) -> arcpy.PointGeometry:
    """
    Returns the center point of the geometries given as input.

    Args:
        geoms (list[arcpy.Geometries]): List of geometries to use in the calculation

    Returns:
        arcpy.PointGeometry: The center point of all points in the input geometries
    """
    all_points = []
    for _, geom in geoms:
        for part in geom:
            for pnt in part:
                if pnt:
                    all_points.append(pnt)
    if not all_points:
        raise ValueError("Ingen gyldige punkt i geometrien!")

    avg_x = sum(pnt.X for pnt in all_points) / len(all_points)
    avg_y = sum(pnt.Y for pnt in all_points) / len(all_points)

    return arcpy.PointGeometry(arcpy.Point(avg_x, avg_y))


def points_equal(p1: arcpy.Point, p2: arcpy.Point, tolerance: float = 1e-6) -> bool:
    """
    Checks if two points are spatially equal within a given tolerance.

    Args:
        p1 (arcpy.Point): The first point to compare
        p2 (arcpy.Point): The second point to compare
        tolerance (float, optional): The maximum allowed difference
        in X and Y coordinates for the points to be considered equal.
        Defaults to 1e-6

    Returns:
        bool: True if the X and Y coordinates of both points are
        within the specified tolerance, otherwise False.
    """
    return abs(p1.X - p2.X) < tolerance and abs(p1.Y - p2.Y) < tolerance


def change_geom_in_roundabouts(roads: list[tuple]) -> dict:
    """
    Reorganizes the geometries to remove all roundabouts connected to
    ramps, and moves the end points for all connected roads into a single point.
    If a road has both ends connected to this point, the geometry is deleted.

    Args:
        roads (list[tuple]): a list of tuples containing information for
        relevant roads connected to a roundabout.
        Each tuple contains:
            geom for the complete roundabout
            oid for the road instance
            geom for the road instance
            str with roadtype for the road instance

    Returns:
        new_roads (dict): A dictionary where key is the road oid and
        value is the new geometry for this road, None if the road should
        be deleted
    """
    roundabout_geom = roads[0][0]
    roundabouts = [[oid, geom] for _, oid, geom, t in roads if t == "rundkjøring"]
    other = [[oid, geom] for _, oid, geom, t in roads if t != "rundkjøring"]
    centroid = get_center_point(roundabouts)

    for i in range(len(other)):
        geom = other[i][1]
        points = list(geom.getPart(0))
        start, end = get_endpoints(geom)
        if roundabout_geom.distanceTo(start) <= 0.5:
            points[0] = centroid.firstPoint
        if roundabout_geom.distanceTo(end) <= 0.5:
            points[-1] = centroid.firstPoint
        new_geom = arcpy.Polyline(arcpy.Array(points), geom.spatialReference)
        if points_equal(points[0], points[-1]):
            other[i][1] = None
        else:
            other[i][1] = new_geom

    new_roads = {oid: None for oid, _ in roundabouts}
    for oid, geom in other:
        new_roads[oid] = geom

    return new_roads


def create_buffer(
    input: arcpy.Geometry | str,
    buffer_distance: str,
    buffer_type: str,
    output: arcpy.Geometry | str,
) -> None:
    """
    Createas a buffer around the features in the input,
    and dissolves those that overlaps each other.

    Args:
        input (arcpy.Geometry | str): The input layer with features
        buffer_distance (str): String describing the size of the buffer, format: "X Meters"
        buffer_type (str): String describing if it should be FLAT or ROUND ends
        output (arcpy.Geometry | str): The output layer to save the results
    """
    intermediate_fc = r"in_memory\intermediate"
    arcpy.analysis.Buffer(
        in_features=input,
        out_feature_class=intermediate_fc,
        buffer_distance_or_field=buffer_distance,
        line_end_type=buffer_type,
        dissolve_option="NONE",
        method="PLANAR",
    )
    arcpy.management.Dissolve(
        in_features=intermediate_fc,
        out_feature_class=output,
        dissolve_field=[],
        multi_part="SINGLE_PART",
    )


def split_polyline_at_index(
    polyline: arcpy.Polyline, angle_tolerance: int = 40
) -> arcpy.Polyline | None:
    """
    Splits the input polyline into two if there are an angle sharper than 40 degrees.

    Args:
        polyline (arcpy.Polyline): Polyline object to be analysed
        angle_tolerance (int, optional): Tolerance of what is categorized as a sharp angle, default 40 degrees

    Returns:
        arcpy.Polyline: Two new polylines, one starting in the point with a sharp angle,
        and one that ends in the same point
        If no sharp angle: returns None
    """
    points = polyline.getPart(0)
    sharp_index = None
    for i in tqdm(
        range(1, len(points) - 1), desc="Analysing points", colour="yellow", leave=False
    ):
        a, b, c = points[i - 1 : i + 2]
        angle = calculate_angle(a, b, c)
        if angle < angle_tolerance or angle > 360 - angle_tolerance:
            sharp_index = i
            break
    if sharp_index:
        first = arcpy.Polyline(
            arcpy.Array(points[: sharp_index + 1]), polyline.spatialReference
        )
        second = arcpy.Polyline(
            arcpy.Array(points[sharp_index:]), polyline.spatialReference
        )
        return first, second
    return None, None

def get_line_endpoints(line_geom):
        """
        Accepts an arcpy Polyline geometry and returns two arcpy PointGeometry objects:
        (start_point_geom, end_point_geom).
        """
        # Get first and last coordinate from first part (works for simple and multipart; 
        # for multipart this uses the first and last vertex of the entire geometry).
        first_part = line_geom.getPart(0)
        start_pt = first_part[0]
        # find last non-None vertex in geometry
        last_pt = None
        for part in line_geom:
            for v in part:
                if v is not None:
                    last_pt = v
        if last_pt is None:
            raise ValueError("Line geometry has no vertices")
        sr = line_geom.spatialReference
        start_pg = arcpy.PointGeometry(arcpy.Point(start_pt.X, start_pt.Y), sr)
        end_pg = arcpy.PointGeometry(arcpy.Point(last_pt.X, last_pt.Y), sr)
        return start_pg, end_pg

def merge_lines_by_endpoint_fast(input_fc, output_fc, tolerance=2.0):
    """
    Fast merging of lines whose endpoints are within 'tolerance' distance using a grid spatial index.
    Only geometry is preserved.
    """

    # Collect all lines and their endpoints
    lines = []
    with arcpy.da.SearchCursor(input_fc, ["OID@", "SHAPE@"]) as cursor:
        for oid, geom in cursor:
            if geom is None:
                continue
            start = geom.firstPoint
            end = geom.lastPoint
            lines.append({"oid": oid, "geom": geom, "start": start, "end": end, "used": False})

    # Build a grid spatial index for endpoints
    grid = defaultdict(list)
    grid_size = tolerance
    def grid_key(pt):
        return (int(pt.X // grid_size), int(pt.Y // grid_size))

    for i, line in enumerate(lines):
        grid[grid_key(line["start"])].append(i)
        grid[grid_key(line["end"])].append(i)

    # Merge lines by endpoint proximity using the grid
    merged_geoms = []
    for i, line in enumerate(lines):
        if line["used"]:
            continue
        group = [line]
        line["used"] = True
        queue = [line]
        while queue:
            current = queue.pop()
            for pt in [current["start"], current["end"]]:
                # Check neighboring grid cells
                gx, gy = grid_key(pt)
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        cell = (gx + dx, gy + dy)
                        for idx in grid.get(cell, []):
                            other = lines[idx]
                            if other["used"]:
                                continue
                            for opt in [other["start"], other["end"]]:
                                if math.hypot(pt.X - opt.X, pt.Y - opt.Y) <= tolerance:
                                    group.append(other)
                                    other["used"] = True
                                    queue.append(other)
                                    break
        # Merge all geometries in group
        arr = arcpy.Array()
        for g in group:
            for part in g["geom"]:
                for p in part:
                    arr.add(p)
        merged_geoms.append(arcpy.Polyline(arr, line["geom"].spatialReference))

    # Write merged lines to output
    if arcpy.Exists(output_fc):
        arcpy.management.Delete(output_fc)
    arcpy.management.CreateFeatureclass(
        os.path.dirname(output_fc), os.path.basename(output_fc), "POLYLINE",
        spatial_reference=arcpy.Describe(input_fc).spatialReference
    )
    with arcpy.da.InsertCursor(output_fc, ["SHAPE@"]) as cursor:
        for geom in merged_geoms:
            cursor.insertRow([geom])

def remove_endpoints_points(endpoints_layer, fc):
    """
    Removes points in fc that intersect with endpoints in endpoints_layer
    """
    endpoints_fc = "in_memory\\collected_endpoints"

    sr = arcpy.Describe(endpoints_layer).spatialReference
    arcpy.CreateFeatureclass_management("in_memory", "collected_endpoints", "POINT", spatial_reference=sr)


    with arcpy.da.SearchCursor(endpoints_layer, ["OID@",  "SHAPE@"]) as road_cur, \
        arcpy.da.InsertCursor(endpoints_fc, ["SHAPE@"]) as ins_cur:
        for oid, geom in road_cur:
            #if oid in intersecting_oids:
            start_pg, end_pg = get_line_endpoints(geom)
            ins_cur.insertRow([start_pg])
            ins_cur.insertRow([end_pg])
    
    points_lyr = arcpy.management.MakeFeatureLayer(fc, "points_lyr").getOutput(0)
    arcpy.management.SelectLayerByLocation(points_lyr, "INTERSECT", endpoints_fc, selection_type="NEW_SELECTION")

    selected_count = int(arcpy.GetCount_management(points_lyr).getOutput(0))
    if selected_count > 0:
        arcpy.DeleteRows_management(points_lyr)
    
    arcpy.management.Delete(endpoints_fc)

def combine_intersecting_buffers(buffer_fc, out_fc):
    """
    Combine intersecting buffer polygons into single features.
    buffer_fc     Path to input buffer feature class (must be polygons).
    out_fc        Path to output feature class to create.
    temp_sr       Optional spatial reference object or WKID. If None uses buffer_fc's SR.
    """
    # determine spatial reference
    
    desc = arcpy.Describe(buffer_fc)
    sr = desc.spatialReference

    # load OID field name and geometries
    oid_field = arcpy.Describe(buffer_fc).OIDFieldName
    geoms = []
    oids = []
    with arcpy.da.SearchCursor(buffer_fc, [oid_field, "SHAPE@"]) as cursor:
        for oid, geom in cursor:
            if geom is None:
                continue
            oids.append(oid)
            geoms.append(geom)

    n = len(oids)

    # build adjacency list by geometry intersection
    adj = {i: set() for i in range(n)}
    for i in range(n):
        gi = geoms[i]
        for j in range(i + 1, n):
            gj = geoms[j]
            if not gi.disjoint(gj):
                adj[i].add(j)
                adj[j].add(i)

    # find connected components (DFS)
    visited = [False] * n
    components = []
    for i in range(n):
        if visited[i]:
            continue
        stack = [i]
        comp = []
        visited[i] = True
        while stack:
            cur = stack.pop()
            comp.append(cur)
            for nb in adj[cur]:
                if not visited[nb]:
                    visited[nb] = True
                    stack.append(nb)
        components.append(comp)

    # create output feature class
    arcpy.management.CreateFeatureclass(
        "in_memory",
        out_fc,
        "POLYGON",
        spatial_reference=sr
    )

    # if CreateFeatureclass returned a full path different from out_fc, use that path for insert
    out_fc_final = "in_memory\\" + out_fc

    # add component ID field
    arcpy.management.AddField(out_fc_final, "ClusterID", "LONG")

    # union geometries per component and insert
    with arcpy.da.InsertCursor(out_fc_final, ["SHAPE@", "ClusterID"]) as icur:
        for comp_id, comp in enumerate(components, start=1):
            geom_list = [geoms[idx] for idx in comp]
            # union progressively to avoid very large single union call
            merged = geom_list[0]
            for g in geom_list[1:]:
                merged = merged.union(g)
            icur.insertRow([merged, comp_id])

    arcpy.AddMessage("Created {} clusters from {} input buffers.".format(len(components), n))

def create_near_map(distance_str, in_fc, near_fc,):
    """
    Creates a near table and returns it in a map with only near rank 1 entries and the key is oid of in fc
    """
    near_table = "in_memory\\near_table"
    arcpy.GenerateNearTable_analysis(in_features=in_fc,
                                near_features=near_fc,
                                out_table=near_table,
                                search_radius=distance_str,
                                location="LOCATION",
                                angle="NO_ANGLE",
                                closest="ALL",   
                                method="PLANAR")

    near_map = {}
    with arcpy.da.SearchCursor(near_table, ["IN_FID", "NEAR_X", "NEAR_Y", "NEAR_DIST", "NEAR_RANK"]) as s:
        for in_fid, nx, ny, nd, nr in s:
            if nr != 1:
                continue
            if nx is None or ny is None:
                continue
            near_map[int(in_fid)] = (float(nx), float(ny), float(nd))
    
    arcpy.management.Delete(near_table)

    return near_map

def create_near_map_unmatched(distance_str, in_fc, near_fc, unmatched_oids):
    points_lyr = "points_lyr_unmatched"
    arcpy.MakeFeatureLayer_management(in_fc, points_lyr)

    oid_field = arcpy.Describe(in_fc).oidFieldName

    in_list = ",".join(map(str, unmatched_oids))
    where = f"{arcpy.AddFieldDelimiters(in_fc, oid_field)} IN ({in_list})"

    arcpy.SelectLayerByAttribute_management(points_lyr, "NEW_SELECTION", where)

    near_map = create_near_map(distance_str, points_lyr, near_fc)

    arcpy.Delete_management(points_lyr)

    return near_map
#########################################################
# Her har jeg startet
#########################################################
def create_in_memory_point_fc(name, spatial_ref):
    fc = f"in_memory/{name}"
    if arcpy.Exists(fc):
        arcpy.management.Delete(fc)
    arcpy.management.CreateFeatureclass(
        "in_memory", name, "POINT", spatial_reference=spatial_ref
    )
    return fc


def insert_points(fc, points, spatial_ref):
    if not points:
        return
    with arcpy.da.InsertCursor(fc, ["SHAPE@"]) as cursor:
        for p in points:
            if isinstance(p, tuple) and len(p) == 2:
                geom = arcpy.PointGeometry(arcpy.Point(p[0], p[1]), spatial_ref)
            else:
                geom = p
            cursor.insertRow([geom])


def collect_endpoints(layer_name):
    end_counts = {}
    ramp_end_counts = {}
    with arcpy.da.SearchCursor(layer_name, ["SHAPE@", "typeveg"]) as cursor:
        for geom, t in cursor:
            s, e = get_endpoints(geom)
            ks = (s.firstPoint.X, s.firstPoint.Y)
            ke = (e.firstPoint.X, e.firstPoint.Y)
            end_counts[ks] = end_counts.get(ks, 0) + 1
            end_counts[ke] = end_counts.get(ke, 0) + 1
            if t == "rampe":
                ramp_end_counts[ks] = ramp_end_counts.get(ks, 0) + 1
                ramp_end_counts[ke] = ramp_end_counts.get(ke, 0) + 1
    return end_counts, ramp_end_counts


def split_and_select(dissolved_fc, split_points_fc, splitted_fc, ramp_endpoints):
    arcpy.management.Dissolve(
        "roads_lyr", dissolved_fc, dissolve_field=["typeveg"], multi_part="SINGLE_PART"
    )
    arcpy.management.SplitLineAtPoint(dissolved_fc, split_points_fc, splitted_fc)
    arcpy.management.MakeFeatureLayer(splitted_fc, "splitted_lyr")
    arcpy.management.SelectLayerByLocation(
        "splitted_lyr", "INTERSECT", ramp_endpoints, "5 Meters"
    )
    arcpy.management.SelectLayerByAttribute(
        "splitted_lyr", "SUBSET_SELECTION", "typeveg <> 'rampe'"
    )


def find_crossing_points(selected_layer, in_memory_layer):
    if arcpy.Exists(in_memory_layer):
        arcpy.management.Delete(in_memory_layer)
    arcpy.analysis.Intersect(
        [selected_layer, selected_layer], in_memory_layer, output_type="POINT"
    )
    coords = []
    with arcpy.da.SearchCursor(in_memory_layer, ["SHAPE@XY"]) as cur:
        for ((x, y),) in cur:
            if x is None or y is None:
                continue
            coords.append((round(x, 6), round(y, 6)))
    return in_memory_layer, coords


#########################################################

##################
# Main functions
##################


@timing_decorator
def add_ramps() -> None:
    """
    Adds all the ramp objects into the
    road layer used in further analysis.
    """
    print("\nAdding ramps to the data...")
    roads = data_files["input"]
    ramps = data_files["ramps"]

    temp_ramps = r"in_memory\ramps_temp"
    arcpy.conversion.FeatureClassToFeatureClass(ramps, "in_memory", "ramps_temp")

    arcpy.management.Append(inputs=temp_ramps, target=roads, schema_type="NO_TEST")
    print("Ramps successfully added to the data!\n")


@timing_decorator
def fetch_roundabouts() -> None:
    """
    Collects all the roundabouts, dissolves them into one element per
    roundabout and creates a FeatureLayer with those shorter than 150m.
    """
    print("\nCollects relevant roundabouts...")
    roads = data_files["input"]
    roundabouts = data_files["roundabouts_1"]
    small_roundabouts = data_files["roundabouts_2"]

    arcpy.management.MakeFeatureLayer(
        roads, "roundabouts_lyr", where_clause="typeveg = 'rundkjøring'"
    )
    arcpy.management.MakeFeatureLayer(
        roads, "ramps_lyr", where_clause="typeveg = 'rampe'"
    )

    arcpy.management.Dissolve(
        in_features="roundabouts_lyr",
        out_feature_class=roundabouts,
        dissolve_field=[],
        multi_part="SINGLE_PART",
        unsplit_lines="DISSOLVE_LINES",
    )

    arcpy.management.MakeFeatureLayer(
        roundabouts, "roundabouts_lyr", where_clause="Shape_Length < 150"
    )

    arcpy.management.SelectLayerByLocation(
        in_layer="roundabouts_lyr",
        overlap_type="INTERSECT",
        select_features="ramps_lyr",
        search_distance="5 Meters",
        selection_type="NEW_SELECTION",
    )

    arcpy.management.CopyFeatures("roundabouts_lyr", small_roundabouts)

    print("Relevant roundabouts successfully collected!\n")


@timing_decorator
def clean_ramps_near_roundabouts() -> None:
    """
    Removes roundabouts, fetches all road instances going into this in
    a single point, and deletes those having both ends in this point.
    """
    print("\nClean ramps near roundabouts...")
    roads = data_files["input"]
    small_roundabouts = data_files["roundabouts_2"]

    cleaned_roads = data_files["cleaned_roads"]
    arcpy.management.CopyFeatures(roads, cleaned_roads)

    arcpy.management.MakeFeatureLayer(cleaned_roads, "roads_lyr")

    roundabouts = [
        (oid, geom)
        for oid, geom in arcpy.da.SearchCursor(small_roundabouts, ["OID@", "SHAPE@"])
    ]

    oid_geom_pairs = defaultdict(list)
    for r_id, r_geom_roundabout in tqdm(
        roundabouts,
        desc="Checks roads against roundabouts",
        colour="yellow",
        leave=False,
    ):
        temp_geom = arcpy.management.CopyFeatures(
            r_geom_roundabout, "in_memory/temp_roundabout"
        )
        arcpy.management.SelectLayerByLocation(
            in_layer="roads_lyr",
            overlap_type="WITHIN_A_DISTANCE",
            select_features=temp_geom,
            search_distance="1 Meters",
            selection_type="NEW_SELECTION",
        )
        with arcpy.da.SearchCursor(
            "roads_lyr", ["OID@", "SHAPE@", "typeveg"]
        ) as cursor:
            for oid, geom, r_type in cursor:
                oid_geom_pairs[r_id].append([r_geom_roundabout, oid, geom, r_type])
        arcpy.management.Delete("in_memory/temp_roundabout")

    changed = {}

    for key in tqdm(
        oid_geom_pairs, desc="Edits the geometry", colour="yellow", leave=False
    ):
        to_edit = oid_geom_pairs[key]
        for i in range(len(to_edit)):
            if to_edit[i][1] in changed:
                to_edit[i][2] = changed[to_edit[i][1]]
        new_roads = change_geom_in_roundabouts(oid_geom_pairs[key])
        oids = [oid for oid in new_roads.keys()]
        if len(oids) > 0:
            arcpy.management.SelectLayerByAttribute(
                in_layer_or_view="roads_lyr",
                selection_type="NEW_SELECTION",
                where_clause=f"OBJECTID in ({','.join(str(oid) for oid in oids)})",
            )
            with arcpy.da.UpdateCursor("roads_lyr", ["OID@", "SHAPE@"]) as cursor:
                for oid, _ in cursor:
                    if new_roads[oid] == None:
                        cursor.deleteRow()
                    else:
                        cursor.updateRow([oid, new_roads[oid]])
                        changed[oid] = new_roads[oid]

    print("Ramps near roundabouts successfully cleaned!\n")


@timing_decorator
def merge_ramps() -> None:
    """
    Merges all the ramps into longer instances, but splits those that contains junctions,
    or crossing over other roads in the same level using topological relations.
    """
    print("\nMerge ramps...")
    roads_fc = data_files["cleaned_roads"]
    dissolved_fc = data_files["dissolved_ramps"]
    intermediate_fc = data_files["intermediate_ramps"]
    merged_fc = data_files["merged_ramps"]

    arcpy.management.MakeFeatureLayer(
        roads_fc, "ramps_lyr", where_clause="typeveg = 'rampe'"
    )

    arcpy.management.MakeFeatureLayer(roads_fc, "roads_lyr")
    
    after_merge = r"in_memory\after_merge"
    arcpy.management.Dissolve(
        in_features="ramps_lyr",
        out_feature_class=dissolved_fc,
        dissolve_field=[],
        multi_part="SINGLE_PART",
    )

    merge_lines_by_endpoint_fast(dissolved_fc, after_merge, tolerance=50)
    

    arcpy.analysis.Buffer(after_merge, "in_memory\\buffer_ramps_50m", "50 Meters")
    combine_intersecting_buffers("in_memory\\buffer_ramps_50m", "buffer_ramps_50m_dissolved")

    joined_output = "in_memory\\lines_with_group_id"
    arcpy.analysis.SpatialJoin(
        target_features=after_merge,
        join_features="in_memory\\buffer_ramps_50m_dissolved",
        out_feature_class=joined_output,
        join_type="KEEP_COMMON",
        match_option="INTERSECT"
    )
    fields = [f.name for f in arcpy.ListFields(joined_output)]
    print(fields)
    arcpy.management.Dissolve(joined_output, intermediate_fc, dissolve_field="ClusterID")



    arcpy.management.SelectLayerByAttribute("roads_lyr", "CLEAR_SELECTION")
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view="roads_lyr",
        selection_type="NEW_SELECTION",
        where_clause="typeveg <> 'rampe'",
    )

    arcpy.management.CopyFeatures("roads_lyr", merged_fc)

    
    existing_fields = [f.name for f in arcpy.ListFields(intermediate_fc)]
    attr_fields = [
        (f.name, f.type)
        for f in arcpy.ListFields(merged_fc)
        if f.type not in ("Geometry", "OID") and f.name not in existing_fields
    ]

    variants = {
        "String": "TEXT",
        "Integer": "LONG",
        "SmallInteger": "LONG",
        "Double": "DOUBLE",
        "Date": "DATE",
    }
    for field_name, field_type in tqdm(
        attr_fields, desc="Updating attributes", colour="yellow", leave=False
    ):
        string = variants[field_type]
        if string == "TEXT":
            arcpy.management.AddField(
                intermediate_fc, field_name, string, field_length=255
            )
        else:
            arcpy.management.AddField(intermediate_fc, field_name, string)

    arcpy.management.SelectLayerByAttribute("roads_lyr", "CLEAR_SELECTION")
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view="roads_lyr",
        selection_type="NEW_SELECTION",
        where_clause="typeveg = 'rampe'",
    )
    road_attrs = []
    with arcpy.da.SearchCursor(
        "roads_lyr", ["SHAPE@"] + [f[0] for f in attr_fields] + ["typeveg"]
    ) as cursor:
        for row in cursor:
            road_attrs.append(row)

    with arcpy.da.UpdateCursor(
        intermediate_fc, ["SHAPE@"] + [f[0] for f in attr_fields]
    ) as cursor:
        for row_orig in tqdm(cursor, desc="Updating attributes", leave=False):
            ramp_geom = row_orig[0]
            update = defaultdict(set)
            for road_row in road_attrs:
                road_geom = road_row[0]
                road_type = road_row[-1]
                if road_type != "rampe" and ramp_geom.intersect(road_geom, 2):
                    for i, el in enumerate(road_row[1:-1]):  # skip SHAPE@ and typeveg
                        update[attr_fields[i]].add(el)

            row_orig = list(row_orig)

            final_values = {}
            for field, values in update.items():
                field = field[0]
                values = list(values)
                if field.lower() == "medium":
                    values = [v for v in values if v is not None]
                    if values:
                        final_values[field] = values[0]
                    else:
                        final_values[field] = "T"
                else:
                    final_values[field] = values[0]
            if "medium" not in final_values:
                final_values["medium"] = "T"
            for i, field in enumerate(attr_fields, start=1):
                row_orig[i] = final_values.get(field, row[i])
            cursor.updateRow(row_orig)
    

    arcpy.management.Append(
        inputs=intermediate_fc, target=merged_fc, schema_type="NO_TEST"
    )

    print("Ramps successfully merged!\n")


@timing_decorator
def make_ramp_points() -> None:
    """
    Create center points for the ramps and move them to a fitting spot
    """
    print("\nGeneralize ramps...")

    roads_fc = data_files["merged_ramps"]
    ramp_points_fc = data_files["ramp_points"]
    output_fc = data_files["generalized_ramps"]
    out_fc = data_files["ramp_points_moved"]
    
    arcpy.management.CopyFeatures(roads_fc, output_fc)
    arcpy.management.MakeFeatureLayer(
        output_fc, "roads_lyr", where_clause="typeveg <> 'rampe'"
    )
    arcpy.management.MakeFeatureLayer(
        output_fc, "ramps_lyr", where_clause="typeveg = 'rampe'"
    )
    
    # Rampe centers
    arcpy.management.FeatureToPoint("ramps_lyr", ramp_points_fc, 'CENTROID')

    # Select roads within 500 meters to iterate over fewer objects
    arcpy.analysis.Buffer(ramp_points_fc, "in_memory\\buffer_500m", "500 Meters", dissolve_option="ALL")
    arcpy.management.SelectLayerByLocation("roads_lyr", "INTERSECT", "in_memory\\buffer_500m", selection_type="NEW_SELECTION")

    #Create priority 1 points (motorvei krysser ikke motorvei forskjellig medium)
    arcpy.management.MakeFeatureLayer("roads_lyr", "motorveg_t_lyr", where_clause="(motorvegtype = 'Motortrafikkveg' or motorvegtype = 'Motorveg') and medium = 'T'")
    arcpy.management.MakeFeatureLayer("roads_lyr", "motorveg_l_lyr", where_clause="(motorvegtype = 'Motortrafikkveg' or motorvegtype = 'Motorveg') and medium = 'L'")
    arcpy.management.MakeFeatureLayer("roads_lyr", "motorveg_u_lyr", where_clause="(motorvegtype = 'Motortrafikkveg' or motorvegtype = 'Motorveg') and medium = 'U'")

    arcpy.management.MakeFeatureLayer("roads_lyr", "ikke_motorveg_t_lyr", where_clause="(motorvegtype <> 'Motortrafikkveg' and motorvegtype <> 'Motorveg') and medium = 'T'")
    arcpy.management.MakeFeatureLayer("roads_lyr", "ikke_motorveg_l_lyr", where_clause="(motorvegtype <> 'Motortrafikkveg' and motorvegtype <> 'Motorveg') and medium = 'L'")
    arcpy.management.MakeFeatureLayer("roads_lyr", "ikke_motorveg_u_lyr", where_clause="(motorvegtype <> 'Motortrafikkveg' and motorvegtype <> 'Motorveg') and medium = 'U'")


    intersect1 = "in_memory\\intersect1"
    intersect2 = "in_memory\\intersect2"
    intersect3 = "in_memory\\intersect3"
    intersect4 = "in_memory\\intersect4"
    intersect5 = "in_memory\\intersect5"
    priority1 = "in_memory\\priority1"

    arcpy.Intersect_analysis(["motorveg_t_lyr", "ikke_motorveg_l_lyr"], intersect1, join_attributes="ALL", output_type="POINT")
    arcpy.Intersect_analysis(["motorveg_t_lyr", "ikke_motorveg_u_lyr"], intersect2, join_attributes="ALL", output_type="POINT")
    arcpy.Intersect_analysis(["motorveg_l_lyr", "ikke_motorveg_u_lyr"], intersect3, join_attributes="ALL", output_type="POINT")
    arcpy.Intersect_analysis(["motorveg_l_lyr", "ikke_motorveg_t_lyr"], intersect4, join_attributes="ALL", output_type="POINT")
    arcpy.Intersect_analysis(["motorveg_u_lyr", "ikke_motorveg_t_lyr"], intersect5, join_attributes="ALL", output_type="POINT")
    arcpy.Intersect_analysis(["motorveg_u_lyr", "ikke_motorveg_l_lyr"], priority1, join_attributes="ALL", output_type="POINT")


    arcpy.management.Append([intersect1, intersect2, intersect3, intersect4, intersect5], priority1)


    #Create priority 1.5 points ( motorvei krysser motorvei forskjellig medium)
    intersect8 = "in_memory\\intersect8"
    intersect9 = "in_memory\\intersect9"
    priority1_5 = "in_memory\\priority1_5"

    arcpy.Intersect_analysis(["motorveg_t_lyr", "motorveg_l_lyr"], intersect8, join_attributes="ALL", output_type="POINT")
    arcpy.Intersect_analysis(["motorveg_t_lyr", "motorveg_u_lyr"], intersect9, join_attributes="ALL", output_type="POINT")
    arcpy.Intersect_analysis(["motorveg_u_lyr", "motorveg_l_lyr"], priority1_5, join_attributes="ALL", output_type="POINT")

    arcpy.management.Append([intersect8, intersect9], priority1_5)
    


    #Create priority 2 points ( vei krysser vei forskjellig medium)
    intersect6 = "in_memory\\intersect6"
    intersect7 = "in_memory\\intersect7"

    priority2 = "in_memory\\priority2"
    arcpy.management.MakeFeatureLayer("roads_lyr", "roads_t_lyr", where_clause="medium = 'T'")
    arcpy.management.MakeFeatureLayer("roads_lyr", "roads_l_lyr", where_clause="medium = 'L'")
    arcpy.management.MakeFeatureLayer("roads_lyr", "roads_u_lyr", where_clause="medium = 'U'")
    arcpy.management.MakeFeatureLayer("roads_lyr", "roads_ul_lyr", where_clause="medium <> 'T'")



    arcpy.Intersect_analysis(["roads_t_lyr", "roads_l_lyr"], intersect6, join_attributes="ALL", output_type="POINT")
    arcpy.Intersect_analysis(["roads_t_lyr", "roads_u_lyr"], intersect7, join_attributes="ALL", output_type="POINT")
    arcpy.Intersect_analysis(["roads_u_lyr", "roads_l_lyr"], priority2, join_attributes="ALL", output_type="POINT")

    arcpy.management.Append([intersect6, intersect7], priority2)

    # Remove endpoints from priority points
    remove_endpoints_points("roads_ul_lyr", priority1)
    remove_endpoints_points("roads_ul_lyr", priority1_5)
    remove_endpoints_points("roads_ul_lyr", priority2)

    # Create near maps for each priority
    distance_str = "210 Meters"
    near1_map = create_near_map(distance_str, ramp_points_fc, priority1)

    # oids not in priority 1
    all_oids = []
    oid_field = arcpy.Describe(ramp_points_fc).oidFieldName
    with arcpy.da.SearchCursor(ramp_points_fc, [oid_field]) as sc:
        for row in sc:
            all_oids.append(int(row[0]))

    unmatched_oids = [oid for oid in all_oids if oid not in near1_map]


    near1_5_map = create_near_map_unmatched(distance_str, ramp_points_fc, priority1_5, unmatched_oids)     
    unmatched_oids += [oid for oid in all_oids if oid not in near1_5_map]

    near2_map = create_near_map_unmatched(distance_str, ramp_points_fc, priority2, unmatched_oids)  
    unmatched_oids += [oid for oid in all_oids if oid not in near2_map]

    arcpy.management.MakeFeatureLayer("roads_lyr", "motorveg_lyr", where_clause="motorvegtype = 'Motortrafikkveg' or motorvegtype = 'Motorveg'")

    near3_map = create_near_map_unmatched(distance_str, ramp_points_fc, "motorveg_lyr", unmatched_oids)
    unmatched_oids += [oid for oid in unmatched_oids if oid not in near3_map]

    near4_map = create_near_map_unmatched(distance_str, ramp_points_fc, "roads_lyr", unmatched_oids)



    # make output 
    sr = arcpy.Describe(ramp_points_fc).spatialReference

    arcpy.management.CreateFeatureclass(
        os.path.dirname(out_fc),
        os.path.basename(out_fc),
        "POINT",
        spatial_reference=arcpy.Describe(ramp_points_fc).spatialReference
    )

    existing_out_fields = [f.name for f in arcpy.ListFields(out_fc) if f.type not in ("OID", "Geometry")]
    out_fields = ["SHAPE@", "priority"] + existing_out_fields
    in_fields = [oid_field, "SHAPE@"] + existing_out_fields

    arcpy.management.AddField(out_fc, "priority", "DOUBLE")


    with arcpy.da.SearchCursor(ramp_points_fc, in_fields) as scur, arcpy.da.InsertCursor(out_fc, out_fields) as icur:
        for row in scur:
            oid = int(row[0])
            orig_geom = row[1]
            # Determine snapped location
            if oid in near1_map:
                nx, ny, nd = near1_map[oid]
                new_geom = arcpy.PointGeometry(arcpy.Point(nx, ny), sr)
                priority = [1]
            elif oid in near1_5_map:
                nx, ny, nd = near1_5_map[oid]
                new_geom = arcpy.PointGeometry(arcpy.Point(nx, ny), sr)
                priority = [1.5]
            elif oid in near2_map:
                nx, ny, nd = near2_map[oid]
                new_geom = arcpy.PointGeometry(arcpy.Point(nx, ny), sr)
                priority = [2]
            elif oid in near3_map:
                nx, ny, nd = near3_map[oid]
                new_geom = arcpy.PointGeometry(arcpy.Point(nx, ny), sr)
                priority = [3]
            elif oid in near4_map:
                nx, ny, nd = near4_map[oid]
                new_geom = arcpy.PointGeometry(arcpy.Point(nx, ny), sr)
                priority = [4]
            else:
                new_geom = orig_geom
                priority = [0]

            insert_row = [new_geom] + priority 
            icur.insertRow(insert_row)


    # Remove duplicates (maybe unnecessary, might be necessary if we divide oslo from the rest)
    arcpy.DeleteIdentical_management(in_dataset=out_fc, fields="Shape", xy_tolerance="100 Meters")

    # Remove the ramp lines from the roads
    arcpy.management.DeleteFeatures("ramps_lyr")
    
    print("Ramps successfully generalized!\n")





@timing_decorator
def delete_intermediate_files() -> None:
    """
    Deletes the intermediate files used during the process.
    """
    for file in files_to_delete:
        arcpy.management.Delete(data_files[file])


if __name__ == "__main__":
    main()
