# Importing packages
import arcpy

from collections import defaultdict
from tqdm import tqdm

arcpy.env.overwriteOutput = True

# Importing custom modules
from custom_tools.decorators.timing_decorator import timing_decorator
from file_manager.n100.file_manager_roads import Road_N100

from generalization.n100.road.dam import get_endpoints

data_files = {
    # Stores all the relevant file paths to the geodata used in this Python file
    "input": Road_N100.data_selection___nvdb_roads___n100_road.value,
    "roundabout": Road_N100.roundabout__roundabout__n100_road.value,
    "cleaned_road": Road_N100.roundabout__cleaned_road__n100_road.value,
}


@timing_decorator
def generalize_roundabouts():
    """
    Fjerner alle rundkjøringer og flytter tilhørende veisegmenter inn i et felles punkt.
    """
    fetch_roundabouts()
    create_intersections_of_roundabouts()


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
    for _, geom, _ in geoms:
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
    Reorganizes the geometries to remove all roundabouts, and moves the end points
    for all connected roads into a single point. If a road has both ends connected
    to this point, the geometry is deleted.

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
    roundabouts = [[oid, geom, medium] for _, oid, geom, t, medium in roads if t == "rundkjøring"]
    tunnel = True if all(medium == "U" for _, _, medium in roundabouts) else False
    if tunnel:
        other = [[oid, geom] for _, oid, geom, t, medium in roads if t != "rundkjøring" and medium == "U"]
    else:
        other = [[oid, geom] for _, oid, geom, t, medium in roads if t != "rundkjøring" and medium != "U"]

    centroid = get_center_point(roundabouts)
    
    for i in range(len(other)):
        geom = other[i][1]
        points = list(geom.getPart(0))
        start, end = get_endpoints(geom)
        tolerance = 5.0 # [m]
        if roundabout_geom.distanceTo(start) <= tolerance:
            points[0] = centroid.firstPoint
        if roundabout_geom.distanceTo(end) <= tolerance:
            points[-1] = centroid.firstPoint
        new_geom = arcpy.Polyline(arcpy.Array(points), geom.spatialReference)
        if points_equal(points[0], points[-1]):
            other[i][1] = None
        else:
            other[i][1] = new_geom

    new_roads = {oid: None for oid, _, _ in roundabouts}
    for oid, geom in other:
        new_roads[oid] = geom
    return new_roads

##################
# Main functions
##################


@timing_decorator
def fetch_roundabouts() -> None:
    """
    Collects all the roundabouts, dissolves them into one element
    per roundabout and stores the result in a FeatureLayer.
    """
    print("\nCollects roundabouts...")
    road_fc = data_files["input"]
    roundabout_fc = data_files["roundabout"]

    arcpy.management.MakeFeatureLayer(
        road_fc, "roundabout_lyr", where_clause="typeveg = 'rundkjøring'"
    )

    arcpy.management.Dissolve(
        in_features="roundabout_lyr",
        out_feature_class=roundabout_fc,
        dissolve_field=[],
        multi_part="SINGLE_PART",
        unsplit_lines="DISSOLVE_LINES",
    )

    print("Roundabouts successfully collected!\n")


@timing_decorator
def create_intersections_of_roundabouts() -> None:
    """
    Removes roundabouts, fetches all road instances going into this in
    a single point, and deletes those having both ends in this point.
    """
    print("\nCreate intersections of roundabouts...")
    road_fc = data_files["input"]
    roundabout_fc = data_files["roundabout"]
    cleaned_road_fc = data_files["cleaned_road"]

    arcpy.management.CopyFeatures(road_fc, cleaned_road_fc)

    arcpy.management.MakeFeatureLayer(cleaned_road_fc, "road_lyr")

    roundabouts = [
        (oid, geom)
        for oid, geom in arcpy.da.SearchCursor(roundabout_fc, ["OID@", "SHAPE@"])
    ]

    temp_roundabout = "in_memory/temp_roundabout"
    oid_geom_pairs = defaultdict(list)

    for r_id, r_geom_roundabout in tqdm(
        roundabouts,
        desc="Checks roads against roundabouts",
        colour="yellow",
        leave=False,
    ):
        temp_geom = arcpy.management.CopyFeatures(r_geom_roundabout, temp_roundabout)
        # TODO: Selekter kun de med samme medium
        # TODO: Sjekk om det finnes rundkjøringer med flere medium
        # TODO: Sjekk om det finnes rundkjøringer med f.eks. medium T der en medium U er direkte koblet (Ila, Trondheim)
        arcpy.management.SelectLayerByLocation(
            in_layer="road_lyr",
            overlap_type="WITHIN_A_DISTANCE",
            select_features=temp_geom,
            search_distance="5 Meters",
            selection_type="NEW_SELECTION",
        )
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view="road_lyr",
            selection_type="SUBSET_SELECTION",
            where_clause="objtype = 'VegSenterlinje'"
        )
        with arcpy.da.SearchCursor("road_lyr", ["OID@", "SHAPE@", "typeveg", "medium"]) as cursor:
            for oid, geom, r_type, medium in cursor:
                oid_geom_pairs[r_id].append([r_geom_roundabout, oid, geom, r_type, medium])
        if arcpy.Exists(temp_roundabout):
            arcpy.management.Delete(temp_roundabout)

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
                in_layer_or_view="road_lyr",
                selection_type="NEW_SELECTION",
                where_clause=f"OBJECTID in ({','.join(str(oid) for oid in oids)})",
            )
            with arcpy.da.UpdateCursor("road_lyr", ["OID@", "SHAPE@"]) as cursor:
                for oid, _ in cursor:
                    if new_roads[oid] == None:
                        cursor.deleteRow()
                    else:
                        cursor.updateRow([oid, new_roads[oid]])
                        changed[oid] = new_roads[oid]
    """
    if arcpy.Exists(roundabout_fc):
        arcpy.management.Delete(roundabout_fc)
    """
    print("Successfully created intersections of roundabouts!\n")


if __name__ == "__main__":
    generalize_roundabouts()
