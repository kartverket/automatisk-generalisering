# Importing packages
import arcpy

import os

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
    "centroids": Road_N100.roundabout__centroids__n100_road.value,
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


def change_geom_in_roundabouts(roads: list[tuple]) -> tuple[dict, arcpy.PointGeometry]:
    """
    Reorganizes the geometries to remove all roundabouts, and moves the end points
    for all connected roads into a single point. If a road has both ends connected
    to this point, the geometry is deleted.

    Args:
        roads (list[tuple]): a list of tuples containing information for
        relevant roads connected to a roundabout.
        Each tuple contains:
            geom for the complete roundabout
            str with road number for the relevant roundabout
            oid for the road instance
            geom for the road instance
            str with roadtype for the road instance
            str with medium for the road instance
            str with road number for the road instance

    Returns:
        new_roads (dict): A dictionary where key is the road oid and
        value is the new geometry for this road, None if the road should
        be deleted
        centroid (arcpy.PointGeometry): The point geometry of the center point
        of the collapsed roundabout
    """
    roundabout_geom = roads[0][0]
    roundabout_number = roads[0][1]
    roundabouts = [
        [oid, geom, medium]
        for _, _, oid, geom, t, medium, vegnummer in roads
        if t == "rundkjøring" and vegnummer == roundabout_number
    ]
    tunnel = True if all(medium == "U" for _, _, medium in roundabouts) else False
    i_dagen = True if all(medium != "U" for _, _, medium in roundabouts) else False
    if tunnel:
        other = [
            [oid, geom, vegnummer]
            for _, _, oid, geom, t, medium, vegnummer in roads
            if t != "rundkjøring" and medium == "U"
        ]
    elif i_dagen:
        other = [
            [oid, geom, vegnummer]
            for _, _, oid, geom, t, _, vegnummer in roads
            if t != "rundkjøring"
        ]
    else:
        # If an error occurs, return the original geometries
        return {oid: geom for _, _, oid, geom, _, _, _ in roads}

    centroid = get_center_point(roundabouts)
    tolerance = 0.1  # [m]

    def pt_key(pt):
        x = round(pt.firstPoint.X, 3) if hasattr(pt, "firstPoint") else round(pt.X, 3)
        y = round(pt.firstPoint.Y, 3) if hasattr(pt, "firstPoint") else round(pt.Y, 3)
        return (x, y)

    roads_by_number = defaultdict(list)
    oids = set()
    for o, g, v in other:
        roads_by_number[v].append([o, g])
    for key in roads_by_number:
        end_points = defaultdict(list)
        if len(roads_by_number[key]):
            for id, geom in roads_by_number[key]:
                start, end = get_endpoints(geom)
                if roundabout_geom.distanceTo(start) < tolerance:
                    start = pt_key(start)
                    end_points[start].append(id)
                if roundabout_geom.distanceTo(end) < tolerance:
                    end = pt_key(end)
                    end_points[end].append(id)

        for key in end_points:
            if len(end_points[key]) > 1:
                for oid in end_points[key]:
                    oids.add(oid)

    other = [[oid, geom] for oid, geom, _ in other if oid not in oids]

    for i in range(len(other)):
        geom = other[i][1]
        points = list(geom.getPart(0))
        start, end = get_endpoints(geom)
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
    return new_roads, centroid


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
        dissolve_field=["vegnummer"],
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

    spatial_ref = arcpy.Describe(cleaned_road_fc).SpatialReference

    arcpy.management.MakeFeatureLayer(cleaned_road_fc, "road_lyr")

    roundabouts = [
        (oid, geom, number)
        for oid, geom, number in arcpy.da.SearchCursor(
            roundabout_fc, ["OID@", "SHAPE@", "vegnummer"]
        )
    ]

    temp_roundabout = "in_memory/temp_roundabout"
    oid_geom_pairs = defaultdict(list)

    for r_id, r_geom, r_number in tqdm(
        roundabouts,
        desc="Checks roads against roundabouts",
        colour="yellow",
        leave=False,
    ):
        temp_geom = arcpy.management.CopyFeatures(r_geom, temp_roundabout)
        arcpy.management.SelectLayerByLocation(
            in_layer="road_lyr",
            overlap_type="INTERSECT",
            select_features=temp_geom,
            selection_type="NEW_SELECTION",
        )
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view="road_lyr",
            selection_type="SUBSET_SELECTION",
            where_clause="objtype = 'VegSenterlinje'",
        )
        with arcpy.da.SearchCursor(
            "road_lyr", ["OID@", "SHAPE@", "typeveg", "medium", "vegnummer"]
        ) as cursor:
            for oid, geom, road_type, medium, vegnummer in cursor:
                oid_geom_pairs[r_id].append(
                    [r_geom, r_number, oid, geom, road_type, medium, vegnummer]
                )
        if arcpy.Exists(temp_roundabout):
            arcpy.management.Delete(temp_roundabout)

    changed = {}
    centroids = []

    for key in tqdm(
        oid_geom_pairs, desc="Edits the geometry", colour="yellow", leave=False
    ):
        to_edit = oid_geom_pairs[key]
        for i in range(len(to_edit)):
            if to_edit[i][2] in changed:
                to_edit[i][3] = changed[to_edit[i][2]]
        new_roads, centroid = change_geom_in_roundabouts(oid_geom_pairs[key])
        centroids.append(centroid)
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

    # Creates a layer with the center points for all the roundabouts
    # just as a visual control of the created junction points
    centroid_fc = data_files["centroids"]
    path, name = os.path.split(centroid_fc)
    arcpy.management.CreateFeatureclass(
        path, name, "POINT", spatial_reference=spatial_ref
    )
    with arcpy.da.InsertCursor(centroid_fc, ["SHAPE@"]) as insert:
        for centroid in centroids:
            insert.insertRow([centroid])

    # """ Deletes intermediate files during the process
    for layer in [roundabout_fc, centroid_fc]:
        if arcpy.Exists(layer):
            arcpy.management.Delete(layer)
    # """

    print("Successfully created intersections of roundabouts!\n")


if __name__ == "__main__":
    generalize_roundabouts()
