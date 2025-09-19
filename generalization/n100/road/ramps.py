# Import packages
import arcpy
from collections import defaultdict
from tqdm import tqdm

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

    "test": Road_N100.ramps__test__n100_road.value
}

files_to_delete = [
    # Stores all the keys from 'data_files' that should be deleted in the end
]

@timing_decorator
def collapse_roundabouts():
    """
    Adds the ramps to the dataset and
    simplifies the structures around them a bit.
    """
    #add_ramps()
    fetch_roundabouts()
    clean_ramps_near_roundabouts()
    merge_ramps()

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

def points_equal(p1, p2, tolerance=1e-6) -> bool:
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

def reverse_geometry(polyline: arcpy.Geometry) -> arcpy.Polyline:
    """
    Createas a reversed copy of the input geometry (line).
    Only singlepart.

    Args:
        polyline (arcpy.Geometry): The line to be reversed

    Returns:
        arcpy.Polyline: The reversed line
    """
    reversed_parts = []
    for part in polyline:
        reversed_parts.append(arcpy.Array(list(reversed(part))))
    return arcpy.Polyline(arcpy.Array(reversed_parts), polyline.spatialReference)

def merge_lines(
    line1: arcpy.Geometry, line2: arcpy.Geometry, tolerance: float = 2.0
) -> arcpy.Polyline:
    """
    Merges two lines into one common one.
    Calls itself with reversed geometries if incorrect directions of the input geometries.

    Args:
        line1 (arcpy.Geometry): The first line to merge
        line2 (arcpy.Geometry): The second line to merge
        tolerance (float): Float number showing tolerance of connection to be merged, default 2.0

    Returns:
        arcpy.Polyline | None: A merged polyline containing both the geometries. None if something fails
    """
    l1_start, l1_end = get_endpoints(line1)
    l2_start, l2_end = get_endpoints(line2)

    # Find the matching endpoints
    if l1_end.distanceTo(l2_start) < tolerance:
        # Correct order
        merged = arcpy.Array()
        for part in line1:
            for pt in part:
                merged.add(pt)
        for part in line2:
            for i, pt in enumerate(part):
                if i == 0 and pt.equals(line1.lastPoint):
                    continue
                merged.add(pt)
        return arcpy.Polyline(merged, line1.spatialReference)

    elif l1_end.distanceTo(l2_end) < tolerance:
        # Reverse line2
        line2_rev = reverse_geometry(line2)
        return merge_lines(line1, line2_rev, tolerance)

    elif l1_start.distanceTo(l2_start) < tolerance:
        # Reverse line1
        line1_rev = reverse_geometry(line1)
        return merge_lines(line1_rev, line2, tolerance)

    elif l1_start.distanceTo(l2_end) < tolerance:
        # Reverse both
        line1_rev = reverse_geometry(line1)
        line2_rev = reverse_geometry(line2)
        return merge_lines(line1_rev, line2_rev, tolerance)

    else:
        # No match
        return None

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

    arcpy.management.Append(
        inputs=temp_ramps, target=roads, schema_type="NO_TEST"
    )
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

    arcpy.management.MakeFeatureLayer(roads, "roundabouts_lyr", where_clause="typeveg = 'rundkjøring'")
    arcpy.management.MakeFeatureLayer(roads, "ramps_lyr", where_clause="typeveg = 'rampe'")

    arcpy.management.Dissolve(
        in_features="roundabouts_lyr",
        out_feature_class=roundabouts,
        dissolve_field=[],
        multi_part="SINGLE_PART",
        unsplit_lines="DISSOLVE_LINES"
    )

    arcpy.management.MakeFeatureLayer(roundabouts, "roundabouts_lyr", where_clause="Shape_Length < 150")

    arcpy.management.SelectLayerByLocation(
        in_layer="roundabouts_lyr",
        overlap_type="INTERSECT",
        select_features="ramps_lyr",
        search_distance="5 Meters",
        selection_type="NEW_SELECTION"
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
        for oid, geom in tqdm(cursor, desc="Laster rundkjøringer", leave=False):
            roundabouts.append((oid, geom))

    road_geoms = []
    with arcpy.da.SearchCursor("roads_lyr", ["OID@", "SHAPE@", "typeveg"]) as cursor:
        for r_oid, r_geom, r_type in tqdm(cursor, desc="Laster veger", leave=False):
            road_geoms.append((r_oid, r_geom, r_type))

    oid_geom_pairs = defaultdict(list)
    for r_id, r_geom_roundabout in tqdm(roundabouts, desc="Sjekker veger mot rundkjøringer", leave=False):
        temp_geom = arcpy.management.CopyFeatures(r_geom_roundabout, "in_memory/temp_roundabout")
        arcpy.management.SelectLayerByLocation(
            in_layer="roads_lyr",
            overlap_type="WITHIN_A_DISTANCE",
            select_features=temp_geom,
            search_distance="1 Meters",
            selection_type="NEW_SELECTION"
        )
        with arcpy.da.SearchCursor("roads_lyr", ["OID@", "SHAPE@", "typeveg"]) as cursor:
            for oid, geom, r_type in cursor:
                oid_geom_pairs[r_id].append((r_geom_roundabout, oid, geom, r_type))
        arcpy.management.Delete("in_memory/temp_roundabout")

    for key in tqdm(oid_geom_pairs, desc="Endrer geometrien", leave=False):
        new_roads = change_geom_in_roundabouts(oid_geom_pairs[key])
        oids = [oid for oid in new_roads.keys()]
        if len(oids) > 0:
            arcpy.management.SelectLayerByAttribute(
                in_layer_or_view="roads_lyr",
                selection_type="NEW_SELECTION",
                where_clause=f"OBJECTID in ({','.join(str(oid) for oid in oids)})"
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
    """
    roads = data_files["cleaned_roads"]
    
    arcpy.management.MakeFeatureLayer(roads, "ramps_lyr", where_clause="typeveg = 'rampe'")

    test = data_files["test"]
    arcpy.management.CopyFeatures("ramps_lyr", test)

if __name__ == "__main__":
    collapse_roundabouts()
