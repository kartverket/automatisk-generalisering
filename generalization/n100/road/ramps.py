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
    "roads_near_ramps": Road_N100.ramps__roads_near_ramp__n100_road.value,
    "endpoints": Road_N100.ramps__endpoints__n100_road.value,
    "dissolved_ramps": Road_N100.ramps__dissolved_ramps__n100_road.value,
    "intermediate_ramps": Road_N100.ramps__intermediate_ramps__n100_road.value,
    "merged_ramps": Road_N100.ramps__merged_ramps__n100_road.value,
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
]


@timing_decorator
def generalize_ramps():
    """
    Simplification of ramps
    """
    #add_ramps()
    fetch_roundabouts()
    clean_ramps_near_roundabouts()
    merge_ramps()

    make_centerpoint()
    """
    Generalization of ramps
    """
    generalize()
    """
    Deletes all the intermediate files created during the process
    """
    delete_intermediate_files()


##################
# Help functions
##################


def get_key_points(
    polyline: arcpy.Geometry,
) -> tuple[arcpy.Point, arcpy.Point, arcpy.Point, arcpy.Point]:
    """
    Returns the first, second, second-to-last, and last points of a polyline.

    Args:
        polyline (arcpy.Geometry): The polyline geometry to be analyzed.

    Returns:
        tuple[arcpy.Point, arcpy.Point, arcpy.Point, arcpy.Point]:
            A tuple containing the first, second, second-to-last, and last points.
            Returns None if the polyline has fewer than three points.
    """
    points = polyline.getPart(0)
    num_points = len(points)

    if num_points < 3:
        return None

    first = points[0]
    second = points[1]
    second_last = points[-2]
    last = points[-1]

    return (first, second, second_last, last)


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


def find_ramp_junctions(ramps: str) -> dict[list]:
    """
    Creates a dictionary keeping all the junctions where only ramps are considered.

    Args:
        ramps (str): Path to a feature layer containing all the ramps

    Returns:
        dict[list]: A dictionary were each value is a list of tuples
        storing the oid and shape of the relevant ramps that occure
        in potential junctions
    """
    ramp_geoms = {}
    end_points = {}
    junctions = {}
    with arcpy.da.SearchCursor(ramps, ["OID@", "SHAPE@"]) as search:
        for oid, geom in search:
            ramp_geoms[oid] = geom
            start, end = get_endpoints(geom)
            start, end = start.firstPoint, end.firstPoint

            if end_points.get((start.X, start.Y), None) != None:
                end_points[(start.X, start.Y)][0] += 1
                end_points[(start.X, start.Y)].append(oid)
            else:
                end_points[(start.X, start.Y)] = [1, oid]

            if end_points.get((end.X, end.Y), None) != None:
                end_points[(end.X, end.Y)][0] += 1
                end_points[(end.X, end.Y)].append(oid)
            else:
                end_points[(end.X, end.Y)] = [1, oid]

    count = 1

    for values in end_points.values():
        if values[0] > 2:
            key = "Junction " + str(count)
            junctions[key] = []
            for i in range(1, len(values)):
                junctions[key].append((values[i], ramp_geoms[values[i]]))
            count += 1
    return junctions


def check_ends(ramp: arcpy.Polyline, roads: str) -> arcpy.Polyline:
    """
    Fetches the start and end points of the ramp and counts the number of roads
    connecting to these points. The end having the largest number of roads is
    considered as the least trafficated end of the ramp. The ramp is returned
    as it is or reversed depending on this, making further analysis possible.

    Args:
        ramp (arcpy.Polyline): The polyline representing the ramp to consider
        roads (str): Path to a feature layer containing relevant, surrounding roads

    Returns:
        arcpy.Polyline: The same ramp either as it is or reversed
    """
    s, e = get_endpoints(ramp)
    tolerance = 0.5  # [m]
    best_count = 0
    best_index = None
    for i, pnt in enumerate([s, e]):
        count = 0
        with arcpy.da.SearchCursor(roads, ["SHAPE@"]) as search:
            for row in search:
                geom = row[0]
                if (
                    geom.firstPoint
                    and arcpy.PointGeometry(geom.firstPoint).distanceTo(pnt) < tolerance
                    or geom.lastPoint
                    and arcpy.PointGeometry(geom.lastPoint).distanceTo(pnt) < tolerance
                ):
                    count += 1
        if count > best_count:
            best_count = count
            best_index = i
    if best_index == 1:
        return reverse_geometry(ramp)
    return ramp


def categorize_ramp(ramp: arcpy.Polyline, roads: str) -> str | None:
    """
    Categorises the incoming ramp into categories deciding further processes.

    Args:
        ramp (arcpy.Polyline): The ramp to analyse
        roads (str): Path to feature layer with relevant roads used in the analyse

    Returns:
        str: A string saying the category of the ramp, used as key in further analyses
    """
    ramp = check_ends(ramp, roads)
    end_points = get_key_points(ramp)
    if end_points == None:
        return "No edit"

    p1, p2, p3, p4 = end_points
    v1 = np.array([p2.X - p1.X, p2.Y - p1.Y])
    v2 = np.array([p4.X - p3.X, p4.Y - p3.Y])
    v1_norm = v1 / np.linalg.norm(v1)
    v2_norm = v2 / np.linalg.norm(v2)
    cos_angle = np.dot(v1_norm, v2_norm)
    same_direction = cos_angle >= np.cos(np.deg2rad(90))

    overlap = False
    with arcpy.da.SearchCursor(roads, ["SHAPE@"]) as search:
        for row in search:
            if ramp.intersect(row[0], 2):
                overlap = True
                break

    if not overlap and same_direction:
        return "simple"
    return "No edit"


"""
def fix_simple(ramp: arcpy.Polyline, roads: str) -> arcpy.Polyline:
    

    start = ramp.firstPoint
    end = ramp.lastPoint

    road_geom_start = None
    road_geom_end = None
    tolerance = 0.1
    height_ratio = 0.5

    with arcpy.da.SearchCursor(roads, ["SHAPE@"]) as search:
        for row in search:
            geom = row[0]
            if geom.distanceTo(start) < tolerance and not road_geom_start:
                road_geom_start = geom
            elif geom.distanceTo(end) < tolerance and not road_geom_end:
                road_geom_end = geom
            if road_geom_start != None and road_geom_end != None:
                break
    
    if road_geom_start == None or road_geom_end == None:
        return ramp

    def to_vector(p1, p2):
        return np.array([p2.X - p1.X, p2.Y - p1.Y])

    def normalize(v):
        mag = np.hypot(v[0], v[1])
        return v / mag if mag != 0 else v
    
    v1 = normalize(to_vector(road_geom_start.firstPoint, road_geom_start.lastPoint))
    v2 = normalize(to_vector(road_geom_end.firstPoint, road_geom_end.lastPoint))

    x1, y1 = start.X, start.Y
    x2, y2 = end.X, end.Y
    dx1, dy1 = v1
    dx2, dy2 = v2
    denom = dx1*dy2 - dy1*dx2
    if abs(denom) < 1e-9:
        raise RuntimeError("Linjene er parallelle, ingen skjæring funnet")
    t = ((x2 - x1)*dy2 - (y2 - y1)*dx2) / denom
    ix = x1 + t*dx1
    iy = y1 + t*dy1
    inter_pt = arcpy.Point(ix, iy)

    v_h = to_vector(start, end)
    mid_h = np.array([(start.X + end.X) / 2.0, (start.Y + end.Y) / 2.0])
    
    perp = np.array([-v_h[1], v_h[0]], dtype=float)
    perp_unit = normalize(perp)

    vec_mid_to_inter = np.array([inter_pt.X - mid_h[0], inter_pt.Y - mid_h[1]])
    height_signed = np.dot(vec_mid_to_inter, perp_unit)
    height = abs(height_signed)

    sign = np.sign(height_signed) if height_signed != 0 else 1.0

    shift = sign * height * float(height_ratio)
    new_pt_xy = (inter_pt.X + perp_unit[0] * shift, inter_pt.Y + perp_unit[1] * shift)

    arr = arcpy.Array([arcpy.Point(start.X, start.Y),
                       arcpy.Point(new_pt_xy[0], new_pt_xy[1]),
                       arcpy.Point(end.X, end.Y)])
    new_line = arcpy.Polyline(arr, ramp.spatialReference)
    return new_line

def fix_simple_2(ramp: arcpy.Polyline, roads: str) -> arcpy.Polyline:
    """ """
    # Identifies the endpoint of the ramp connected to the roads with less traffic
    ramp = check_ends(ramp, roads)
    start, end = ramp.firstPoint, ramp.lastPoint
    connection_points = [start, end]
    fraction = 0.75 if ramp.pointCount > 5 else 0.5

    # Creates a point 70% from the connection point identified above to the other end point
    x = connection_points[0].X + fraction * (
        connection_points[1].X - connection_points[0].X
    )
    y = connection_points[0].Y + fraction * (
        connection_points[1].Y - connection_points[0].Y
    )

    p_frac = arcpy.Point(x, y)

    # Finds the closest geometry to the end point at the trafficated end
    nearest_geom = None
    min_dist = float("inf")

    for row in arcpy.da.SearchCursor(roads, ["SHAPE@"]):
        geom = row[0]
        dist = geom.distanceTo(connection_points[1])
        if dist < min_dist:
            min_dist = dist
            nearest_geom = geom
            if min_dist == 0:
                break

    if nearest_geom == None:
        return ramp

    # Calculates the new position of the adjusted ramp point
    dx = end.X - start.X
    dy = end.Y - start.Y
    length = np.hypot(dx, dy)
    ortho_dx = -dy / length
    ortho_dy = dx / length

    moved_pos = arcpy.Point(p_frac.X + ortho_dx * 40, p_frac.Y + ortho_dy * 40)
    moved_neg = arcpy.Point(p_frac.X - ortho_dx * 40, p_frac.Y - ortho_dy * 40)

    dist_pos = nearest_geom.distanceTo(
        arcpy.PointGeometry(moved_pos, ramp.spatialReference)
    )
    dist_neg = nearest_geom.distanceTo(
        arcpy.PointGeometry(moved_neg, ramp.spatialReference)
    )

    moved_point = moved_pos if dist_pos > dist_neg else moved_neg

    # Creates the new line
    new_array = arcpy.Array([start, moved_point, end])
    new_line = arcpy.Polyline(new_array, ramp.spatialReference)
    return new_line
"""

def fix_simple(line, near_lookup, oid):
    start = line.firstPoint
    end = line.lastPoint
    middle_geom = line.positionAlongLine(0.5, use_percentage=True)
    middle = middle_geom.firstPoint

    new_array = arcpy.Array([start, middle, end])
    new_line = arcpy.Polyline(new_array, line.spatialReference)
    if oid not in near_lookup:
        arcpy.AddWarning(f"OID {oid} not found in near_lookup, skipping.")
        return new_line

    near_x, near_y = near_lookup[oid]
    shifted = move_line_away(new_line, near_x, near_y, distance=75)

    return shifted

def move_line_away(geom, near_x, near_y, distance):
    sr = geom.spatialReference
    new_parts = arcpy.Array()
    for part in geom:
        part_arr = arcpy.Array()
        n = len(part)
        for i, p in enumerate(part):
            if i == 0 or i == n - 1:
                # Do not move endpoints
                part_arr.add(arcpy.Point(p.X, p.Y))
            else:
                dx = p.X - near_x
                dy = p.Y - near_y
                length = math.hypot(dx, dy)
                if length == 0:
                    new_x, new_y = p.X, p.Y
                else:
                    scale = distance / length
                    new_x = p.X + dx * scale
                    new_y = p.Y + dy * scale
                part_arr.add(arcpy.Point(new_x, new_y))
        new_parts.add(part_arr)
    return arcpy.Polyline(new_parts, sr)

def fix_bridge():
    return


def fix_long():
    return


def fix_complex():
    pass


##################
# Main functions
##################

@timing_decorator
def make_centerpoint():
    roads_fc = data_files["merged_ramps"]
    buffer_fc = "in_memory\\buffer_100_meter"
    rampe_centers = "in_memory\\rampe_centers"
    closest_points = r"C:\temp\roads.gdb\closest_points"
    
    arcpy.management.MakeFeatureLayer(
        roads_fc, "roads_lyr", where_clause="typeveg <> 'rampe'"
    )
    arcpy.management.MakeFeatureLayer(
        roads_fc, "ramps_lyr", where_clause="typeveg = 'rampe'"
    )


    arcpy.management.FeatureToPoint("ramps_lyr", rampe_centers, "CENTROID")



    arcpy.Buffer_analysis(rampe_centers, buffer_fc, "100 Meters", dissolve_option="ALL")

    arcpy.management.SelectLayerByLocation("roads_lyr", "INTERSECT", buffer_fc, selection_type="NEW_SELECTION")


    # Load all lines into memory: list of (oid, geometry)
    lines = []
    with arcpy.da.SearchCursor("roads_lyr", ["OID@", "SHAPE@"]) as lcur:
        for oid, geom in lcur:
            lines.append((oid, geom))

    
    sr = arcpy.Describe(rampe_centers).spatialReference
    arcpy.management.CreateFeatureclass(os.path.dirname(closest_points), os.path.basename(closest_points),
                                    "POINT", spatial_reference=sr)

    # Add fields
    arcpy.management.AddField(closest_points, "PointOID", "LONG")
    arcpy.management.AddField(closest_points, "NearestID", "LONG")
    arcpy.management.AddField(closest_points, "Distance", "DOUBLE")

    # For each point, find closest point-on-line
    point_fields = ["OID@", "SHAPE@"]
    with arcpy.da.SearchCursor(rampe_centers, point_fields) as pcur, \
        arcpy.da.InsertCursor(closest_points, ["PointOID", "NearestID", "Distance", "SHAPE@"]) as icur:

        for point_oid, point_geom in pcur:
            best_dist = None
            best_pt_on_line = None
            best_line_oid = None

            for line_oid, line_geom in lines:
                # queryPointAndDistance returns (pointOnLine, leftRight, partIndex, segmentIndex, lineDistance)
                res = line_geom.queryPointAndDistance(point_geom, use_percentage=False)
                if res is None:
                    print("RES IS NONE")
                    continue
                pt_on_line = res[0]
                dist = res[2]

              

                if best_dist is None or dist < best_dist:  
                    best_dist = dist
                    best_pt_on_line = pt_on_line
                    best_line_oid = line_oid

            # Insert result row; if no closest found, skip or insert nulls
            if best_pt_on_line is not None:
                icur.insertRow([point_oid, best_line_oid, best_dist, best_pt_on_line])
            else:
                icur.insertRow([point_oid, None, None, point_geom])
                print(f"No closest line found for point OID {point_oid}")




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
    buffer_fc = data_files["buffered_ramps"]
    relevant_roads_fc = data_files["roads_near_ramps"]
    point_fc = data_files["endpoints"]
    dissolved_fc = data_files["dissolved_ramps"]
    intermediate_fc = data_files["intermediate_ramps"]
    merged_fc = data_files["merged_ramps"]

    arcpy.management.MakeFeatureLayer(
        roads_fc, "ramps_lyr", where_clause="typeveg = 'rampe'"
    )

    create_buffer("ramps_lyr", "20 Meters", "ROUND", buffer_fc)

    arcpy.management.MakeFeatureLayer(roads_fc, "roads_lyr")

    arcpy.management.SelectLayerByLocation(
        in_layer="roads_lyr", overlap_type="INTERSECT", select_features=buffer_fc
    )

    arcpy.management.CopyFeatures("roads_lyr", relevant_roads_fc)

    end_points = {}
    with arcpy.da.SearchCursor("ramps_lyr", ["SHAPE@"]) as cursor:
        for row in cursor:
            s, e = get_endpoints(row[0])

            key_s = (s.firstPoint.X, s.firstPoint.Y)
            key_e = (e.firstPoint.X, e.firstPoint.Y)

            end_points[key_s] = end_points.get(key_s, 0) + 1
            end_points[key_e] = end_points.get(key_e, 0) + 1

    with arcpy.da.SearchCursor(relevant_roads_fc, ["SHAPE@", "typeveg"]) as cursor:
        for geom, t in cursor:
            if t == "rampe":
                continue
            s, e = get_endpoints(geom)

            key_s = (s.firstPoint.X, s.firstPoint.Y)
            key_e = (e.firstPoint.X, e.firstPoint.Y)

            if end_points.get(key_s, 0) > 0:
                end_points[key_s] += 1
            if end_points.get(key_e, 0) > 0:
                end_points[key_e] += 1

    valid_end_points = set()
    for pnt in tqdm(
        end_points, desc="Fetching valid endpoints", colour="yellow", leave=False
    ):
        if end_points[pnt] > 2:
            valid_end_points.add(pnt)

    spatial_ref = arcpy.Describe(roads_fc).spatialReference
    path, name = os.path.split(point_fc)
    arcpy.management.CreateFeatureclass(
        path, name, geometry_type="POINT", spatial_reference=spatial_ref
    )

    with arcpy.da.InsertCursor(point_fc, ["SHAPE@"]) as cursor:
        for x, y in tqdm(
            valid_end_points, desc="Adding points", colour="yellow", leave=False
        ):
            point = arcpy.Point(x, y)
            point_geom = arcpy.PointGeometry(point, spatial_ref)
            cursor.insertRow([point_geom])

    arcpy.management.Dissolve(
        in_features="ramps_lyr",
        out_feature_class=dissolved_fc,
        dissolve_field=[],
        multi_part="SINGLE_PART",
    )

    arcpy.management.SplitLineAtPoint(
        in_features=dissolved_fc,
        point_features=point_fc,
        out_feature_class=intermediate_fc,
        search_radius="5 Meters",
    )

    splitted_geometries = []

    with arcpy.da.UpdateCursor(intermediate_fc, ["SHAPE@"]) as cursor:
        for row in cursor:
            polyline = row[0]
            first, second = split_polyline_at_index(polyline)
            if first and second:
                cursor.deleteRow()
                splitted_geometries.extend([first, second])

    with arcpy.da.InsertCursor(intermediate_fc, ["SHAPE@"]) as insert_cursor:
        for line in splitted_geometries:
            insert_cursor.insertRow([line])

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
    with arcpy.da.SearchCursor("roads_lyr", ["SHAPE@"] + [f[0] for f in attr_fields] + ["typeveg"]) as cursor:
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
def generalize() -> None:
    """
    Generalizes all the ramps by first categorizing each ramp,
    then performing a generalization based on its category.
    """
    print("\nGeneralize ramps...")

    roads_fc = data_files["merged_ramps"]
    buffer_fc = data_files["buffered_ramps"]
    output_fc = data_files["generalized_ramps"]

    arcpy.management.CopyFeatures(roads_fc, output_fc)

    arcpy.management.MakeFeatureLayer(
        output_fc, "roads_lyr", where_clause="typeveg <> 'rampe'"
    )
    arcpy.management.MakeFeatureLayer(
        output_fc, "ramps_lyr", where_clause="typeveg = 'rampe'"
    )



            # Generate Near Table
    closest_points = r"C:\temp\roads.gdb\closest_points"
    near_table = "in_memory\\near_table"
    arcpy.analysis.GenerateNearTable(
        in_features="ramps_lyr",
        near_features=closest_points,
        out_table=near_table,
        search_radius="200 Meters",  # Adjust as needed
        location="LOCATION",
        angle="ANGLE",
        closest="TRUE",
        closest_count=1,
    )

    # Build a lookup of NEAR_X, NEAR_Y for each road feature
    near_lookup = {}
    with arcpy.da.SearchCursor(near_table, ["IN_FID", "NEAR_X", "NEAR_Y"]) as cursor:
        for fid, nx, ny in cursor:
            near_lookup[fid] = (nx, ny)





    buffers = [row[0] for row in arcpy.da.SearchCursor(buffer_fc, ["SHAPE@"])]

    for buffer in tqdm(
        buffers, desc="Analysing each buffer", colour="yellow", leave=False
    ):
        # Fetches all the roads, and then ramps, inside the buffer
        arcpy.management.SelectLayerByLocation(
            in_layer="roads_lyr",
            overlap_type="INTERSECT",
            select_features=buffer,
            selection_type="NEW_SELECTION",
        )
        arcpy.management.SelectLayerByLocation(
            in_layer="ramps_lyr",
            overlap_type="INTERSECT",
            select_features=buffer,
            selection_type="NEW_SELECTION",
        )
        # Generalizes junctions of ramps
        conflicts = find_ramp_junctions("ramps_lyr")
        oids = set()
        for key in conflicts:
            for oid, _ in conflicts[key]:
                oids.add(oid)
        ###
        # TODO: Generalize
        ###
        with arcpy.da.UpdateCursor("ramps_lyr", ["OID@", "SHAPE@"]) as cursor:
            for oid, ramp in cursor:
                if oid in oids:
                    continue
                # For each ramp, categorize it...
                category = categorize_ramp(ramp, "roads_lyr")
                # ... and generalize it
                if category == "simple":
                    row[0] = fix_simple(ramp, near_lookup, oid)
                    cursor.updateRow(row)
                elif category == "bridge":
                    fix_bridge()
                elif category == "long":
                    fix_long()
                elif category == "complex":
                    fix_complex()
                elif category == "No edit":
                    continue
    print("Ramps successfully generalized!\n")


@timing_decorator
def delete_intermediate_files() -> None:
    """
    Deletes the intermediate files used during the process.
    """
    for file in files_to_delete:
        arcpy.management.Delete(data_files[file])


if __name__ == "__main__":
    generalize_ramps()
