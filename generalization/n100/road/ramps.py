# Import packages
import os
import arcpy
from collections import defaultdict
from tqdm import tqdm
import numpy as np

arcpy.env.overwriteOutput = True

# Importing custom input files modules
from input_data import input_n100

# Importing custom modules
from file_manager.n100.file_manager_roads import Road_N100
from custom_tools.decorators.timing_decorator import timing_decorator

data_files = {
    # Stores all the relevant file paths to the geodata used in this Python file
    "input_1": Road_N100.data_preparation___road_single_part_2___n100_road.value,
    "ramps": Road_N100.ramps__ramps__n100_road.value,
    "roundabouts_1": Road_N100.ramps__collapsed_roundabouts__n100_road.value,
    "roundabouts_2": Road_N100.ramps__small_roundabouts__n100_road.value,
    "cleaned_roads": Road_N100.ramps__roads_with_cleaned_roundabouts__n100_road.value,
    "buffered_ramps": Road_N100.ramps__buffered_ramps__n100_road.value,
    "roads_near_ramps": Road_N100.ramps__roads_near_ramp__n100_road.value,
    "endpoints": Road_N100.ramps__endpoints__n100_road.value,
    "dissolved_ramps": Road_N100.ramps__dissolved_ramps__n100_road.value,
    "merged_ramps": Road_N100.ramps__merged_ramps__n100_road.value,
    "test": Road_N100.ramps__test__n100_road.value,
}

files_to_delete = [
    # Stores all the keys from 'data_files' that should be deleted in the end
    "roundabouts_1",
    "roundabouts_2",
    "roads_near_ramps",
    "endpoints",
    "dissolved_ramps",
]


@timing_decorator
def collapse_roundabouts():
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

    # Deletes all the intermediate files created during the process
    delete_intermediate_files()


##################
# Help functions
##################


def get_endpoints(
    polyline: arcpy.Geometry,
) -> tuple[arcpy.PointGeometry, arcpy.PointGeometry]:
    """
    Returns the start and end points of a polyline

    Args:
        polyline (arcpy.Geometry): The geometry (line) to be analysed

    Returns:
        tuple(arcpy.PointGeometry): tuple with start and end points
    """
    return (
        arcpy.PointGeometry(polyline.firstPoint, polyline.spatialReference),
        arcpy.PointGeometry(polyline.lastPoint, polyline.spatialReference),
    )


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


def calculate_angle(
    p1: arcpy.Geometry, p2: arcpy.Geometry, p3: arcpy.Geometry
) -> float:
    """
    Calculates the angle in point 2 between point 1 and 3.

    Args:
        p1 (arcpy.Geometry): Point 1
        p2 (arcpy.Geometry): Point 2 (the angle to be calculated is in this point)
        p3 (arcpy.Geometry): Point 3

    Returns:
        float: The angle in point 2
    """
    # Vectors from p2 to p1, and p2 to p3
    v1 = np.array([p1.X - p2.X, p1.Y - p2.Y])
    v2 = np.array([p3.X - p2.X, p3.Y - p2.Y])

    # Lenghts of the vectors
    len1 = np.linalg.norm(v1)
    len2 = np.linalg.norm(v2)

    if len1 == 0 or len2 == 0:
        return 180  # Undefined angle, treated as straight line

    # Calculate scalar product
    dot = np.dot(v1, v2)

    # Calculates angle in degrees
    cos_angle = dot / (len1 * len2)
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    angle_rad = np.arccos(cos_angle)

    return np.degrees(angle_rad)


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
    roads = data_files["input_1"]
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
    roads = data_files["input_1"]
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
    roads = data_files["input_1"]
    small_roundabouts = data_files["roundabouts_2"]

    cleaned_roads = data_files["cleaned_roads"]
    arcpy.management.CopyFeatures(roads, cleaned_roads)

    arcpy.management.MakeFeatureLayer(cleaned_roads, "roads_lyr")

    roundabouts = []
    with arcpy.da.SearchCursor(small_roundabouts, ["OID@", "SHAPE@"]) as cursor:
        for oid, geom in tqdm(
            cursor, desc="Loads roundabouts", colour="yellow", leave=False
        ):
            roundabouts.append((oid, geom))

    road_geoms = []
    with arcpy.da.SearchCursor("roads_lyr", ["OID@", "SHAPE@", "typeveg"]) as cursor:
        for r_oid, r_geom, r_type in tqdm(
            cursor, desc="Loads roads", colour="yellow", leave=False
        ):
            road_geoms.append((r_oid, r_geom, r_type))

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
                oid_geom_pairs[r_id].append((r_geom_roundabout, oid, geom, r_type))
        arcpy.management.Delete("in_memory/temp_roundabout")

    for key in tqdm(
        oid_geom_pairs, desc="Edits the geometry", colour="yellow", leave=False
    ):
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

    print("Ramps near roundabouts successfully cleaned!\n")


@timing_decorator
def merge_ramps() -> None:
    """
    Merges all the ramps to longer instances, but splits those that contains junctions,
    or crossing over other roads in the same level using topological relations.
    """
    print("\nMerge ramps...")
    roads_fc = data_files["cleaned_roads"]
    buffer_fc = data_files["buffered_ramps"]
    relevant_roads_fc = data_files["roads_near_ramps"]
    point_fc = data_files["endpoints"]
    dissolved_fc = data_files["dissolved_ramps"]
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
        out_feature_class=merged_fc,
        search_radius="5 Meters",
    )

    splitted_geometries = []

    with arcpy.da.UpdateCursor(merged_fc, ["SHAPE@"]) as cursor:
        for row in cursor:
            polyline = row[0]
            first, second = split_polyline_at_index(polyline)
            if first and second:
                cursor.deleteRow()
                splitted_geometries.extend([first, second])

    with arcpy.da.InsertCursor(merged_fc, ["SHAPE@"]) as insert_cursor:
        for line in splitted_geometries:
            insert_cursor.insertRow([line])

    print("Ramps successfully merged!")


"""
test = data_files["test"]
arcpy.management.CopyFeatures("ramps_lyr", test)
#"""


@timing_decorator
def delete_intermediate_files() -> None:
    """
    Deletes the intermediate files used during the process
    of snapping roads away from the dam buffers.
    """
    for file in files_to_delete:
        arcpy.management.Delete(data_files[file])


if __name__ == "__main__":
    collapse_roundabouts()
