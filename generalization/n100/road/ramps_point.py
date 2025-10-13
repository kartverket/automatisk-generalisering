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
def generalize_ramps():
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
    generalize()
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


def merge_lines_by_endpoint(input_fc, output_fc, tolerance=2.0):
    """
    Merges all lines in input_fc whose endpoints are within 'tolerance' distance.
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

    # Merge lines by endpoint proximity
    merged_geoms = []
    for i, line in enumerate(lines):
        if line["used"]:
            continue
        group = [line]
        line["used"] = True
        changed = True
        while changed:
            changed = False
            for other in lines:
                if other["used"]:
                    continue
                for pt in [other["start"], other["end"]]:
                    for g in group:
                        if (math.hypot(pt.X - g["start"].X, pt.Y - g["start"].Y) <= tolerance or
                            math.hypot(pt.X - g["end"].X, pt.Y - g["end"].Y) <= tolerance):
                            group.append(other)
                            other["used"] = True
                            changed = True
                            break
                    if changed:
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

    merge_lines_by_endpoint(dissolved_fc, intermediate_fc, tolerance=50)

    """arcpy.management.SplitLineAtPoint(
        in_features=dissolved_fc,
        point_features=point_fc,
        out_feature_class=intermediate_fc,
        search_radius="5 Meters",
    )"""

    splitted_geometries = []

    """with arcpy.da.UpdateCursor(intermediate_fc, ["SHAPE@"]) as cursor:
        for row in cursor:
            polyline = row[0]
            first, second = split_polyline_at_index(polyline)
            if first and second:
                cursor.deleteRow()
                splitted_geometries.extend([first, second])

    with arcpy.da.InsertCursor(intermediate_fc, ["SHAPE@"]) as insert_cursor:
        for line in splitted_geometries:
            insert_cursor.insertRow([line]) """

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

#########################################################
# Her har jeg startet
#########################################################
@timing_decorator
def generalize() -> None:
    """
    Generalizes all the ramps by first categorizing each ramp,
    then performing a generalization based on its category.
    """
    print("\nGeneralize ramps...")

    roads_fc = data_files["merged_ramps"]
    buffer_100_fc = data_files["buffered_ramps_100"]
    dissolved_fc = data_files["dissolved_group"]
    splitted_fc = data_files["splitted_group"]
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

    arcpy.management.FeatureToPoint("ramps_lyr", ramp_points_fc, 'CENTROID')


    #Create priority 1 points
    arcpy.management.MakeFeatureLayer("roads_lyr", "motorveg_t_lyr", where_clause="(motorvegtype = 'Motortrafikkveg' or motorvegtype = 'Motorveg') and medium = 'T'")
    arcpy.management.MakeFeatureLayer("roads_lyr", "motorveg_ul_lyr", where_clause="(motorvegtype = 'Motortrafikkveg' or motorvegtype = 'Motorveg') and medium <> 'T'")

    arcpy.management.MakeFeatureLayer("roads_lyr", "ikke_motorveg_t_lyr", where_clause="(motorvegtype <> 'Motortrafikkveg' and motorvegtype <> 'Motorveg') and medium = 'T'")
    arcpy.management.MakeFeatureLayer("roads_lyr", "ikke_motorveg_ul_lyr", where_clause="(motorvegtype <> 'Motortrafikkveg' and motorvegtype <> 'Motorveg') and medium <> 'T'")

    intersect1 = "in_memory\\intersect_motorvei_other"
    priority1 = "in_memory\\priority1"

    arcpy.Intersect_analysis(["motorveg_t_lyr", "ikke_motorveg_ul_lyr"], intersect1, join_attributes="ALL", output_type="POINT")
    arcpy.Intersect_analysis(["motorveg_ul_lyr", "ikke_motorveg_t_lyr"], priority1, join_attributes="ALL", output_type="POINT")

    arcpy.management.Append(intersect1, priority1)


    #Create priority 2 points
    priority2 = "in_memory\\priority2"
    arcpy.management.MakeFeatureLayer("roads_lyr", "roads_t_lyr", where_clause="medium = 'T'")
    arcpy.management.MakeFeatureLayer("roads_lyr", "roads_ul_lyr", where_clause="medium <> 'T'")

    arcpy.Intersect_analysis(["roads_t_lyr", "roads_ul_lyr"], priority2, join_attributes="ALL", output_type="POINT")

    # Temporary in-memory feature class to hold endpoints (optional)
    endpoints_fc = "in_memory\\collected_endpoints"
        # Helper: return tuple of endpoint point geometries for a polyline geometry
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

    sr = arcpy.Describe("roads_ul_lyr").spatialReference
    arcpy.CreateFeatureclass_management("in_memory", "collected_endpoints", "POINT", spatial_reference=sr)

        # Add an attribute to reference source road OID (optional)
    arcpy.AddField_management(endpoints_fc, "src_oid", "LONG")

    # Collect endpoints: loop through roads, check intersection with any point in priority2
    road_oid_field = arcpy.Describe("roads_ul_lyr").OIDFieldName


    # Use a search cursor on roads and a spatial selection to test intersection quickly
    with arcpy.da.SearchCursor("roads_ul_lyr", [road_oid_field, "SHAPE@"]) as road_cur, \
        arcpy.da.InsertCursor(endpoints_fc, ["SHAPE@", "src_oid"]) as ins_cur:
        for road_row in road_cur:
            oid = road_row[0]
            geom = road_row[1]
            # Create a temporary layer selection of points that intersect this line
            # Using in_memory selection to avoid changing original layer selection
            # Use a where_clause that selects nothing then select by location
            temp_points = arcpy.management.MakeFeatureLayer(priority2, "temp_points_lyr_" + str(oid)).getOutput(0)
            try:
                arcpy.management.SelectLayerByLocation(temp_points, "INTERSECT", geom, selection_type="NEW_SELECTION")
                count = int(arcpy.GetCount_management(temp_points).getOutput(0))
                if count > 0:
                    start_pg, end_pg = get_line_endpoints(geom)
                    ins_cur.insertRow([start_pg, oid])
                    ins_cur.insertRow([end_pg, oid])
            finally:
                # clean up temp layer
                if arcpy.Exists(temp_points):
                    arcpy.Delete_management(temp_points)
    
    points1_lyr = arcpy.management.MakeFeatureLayer(priority1, "priority1_lyr").getOutput(0)
    points2_lyr = arcpy.management.MakeFeatureLayer(priority2, "priority2_lyr").getOutput(0)
    endpoints_lyr = arcpy.management.MakeFeatureLayer(endpoints_fc, "endpoints_lyr").getOutput(0)

    # Select points that overlap (INTERSECT) endpoints
    arcpy.management.SelectLayerByLocation(points1_lyr, "INTERSECT", endpoints_lyr, selection_type="NEW_SELECTION")
    arcpy.management.SelectLayerByLocation(points2_lyr, "INTERSECT", endpoints_lyr, selection_type="NEW_SELECTION")


    # If any selected, delete them
    selected_count = int(arcpy.GetCount_management(points1_lyr).getOutput(0))
    if selected_count > 0:
        arcpy.DeleteRows_management(points1_lyr)

    selected_count = int(arcpy.GetCount_management(points2_lyr).getOutput(0))
    if selected_count > 0:
        arcpy.DeleteRows_management(points2_lyr)





    #near table for priority1
    distance_str = "210 Meters"
    near1_table = "in_memory\\near1_table"
    arcpy.GenerateNearTable_analysis(in_features=ramp_points_fc,
                                 near_features=priority1,
                                 out_table=near1_table,
                                 search_radius=distance_str,
                                 location="LOCATION",
                                 angle="NO_ANGLE",
                                 closest="ALL",   
                                 method="PLANAR")

    # Build a dictionary mapping input OID -> (NEAR_X, NEAR_Y, NEAR_DIST) for priority1, only nearest rank 1 if multiple
    near1_map = {}
    with arcpy.da.SearchCursor(near1_table, ["IN_FID", "NEAR_X", "NEAR_Y", "NEAR_DIST", "NEAR_RANK"]) as s:
        for in_fid, nx, ny, nd, nr in s:
            if nr != 1:
                continue
            if nx is None or ny is None:
                continue
            near1_map[int(in_fid)] = (float(nx), float(ny), float(nd))


    
    all_oids = []
    oid_field = arcpy.Describe(ramp_points_fc).oidFieldName
    with arcpy.da.SearchCursor(ramp_points_fc, [oid_field]) as sc:
        for row in sc:
            all_oids.append(int(row[0]))

    unmatched_oids = [oid for oid in all_oids if oid not in near1_map]

    
    #near table for priority2
    near2_table = "in_memory\\near2_table"
    # If there are unmatched points, create a layer selecting those, then run GenerateNearTable against P2
    near2_map = {}
    if unmatched_oids:
        # Create a feature layer for points and select unmatched
        points_lyr = "points_lyr_unmatched"
        arcpy.MakeFeatureLayer_management(ramp_points_fc, points_lyr)
        # Build a SQL selection: "OID IN (..)" — watch out for large lists; for very large datasets tile this operation
        in_list = ",".join(map(str, unmatched_oids))
        where = f"{arcpy.AddFieldDelimiters(ramp_points_fc, oid_field)} IN ({in_list})"
        arcpy.SelectLayerByAttribute_management(points_lyr, "NEW_SELECTION", where)

        # Run GenerateNearTable for the selected points only; nearest targets within distance_str
        arcpy.GenerateNearTable_analysis(in_features=points_lyr,
                                        near_features=priority2,
                                        out_table=near2_table,
                                        search_radius=distance_str,
                                        location="LOCATION",
                                        angle="NO_ANGLE",
                                        closest="ALL",
                                        method="PLANAR")

        # Populate near2_map with NEAR_RANK == 1
        with arcpy.da.SearchCursor(near2_table, ["IN_FID", "NEAR_X", "NEAR_Y", "NEAR_DIST", "NEAR_RANK"]) as s2:
            for in_fid, nx, ny, nd, nr in s2:
                if nr != 1:
                    continue
                if nx is None or ny is None:
                    continue
                near2_map[int(in_fid)] = (float(nx), float(ny), float(nd))

        # Clean up layer
        arcpy.Delete_management(points_lyr)
    



    unmatched_oids = [oid for oid in all_oids if oid not in near1_map and oid not in near2_map]
    oid_values = ",".join(str(int(v)) for v in unmatched_oids)
    where = "{} IN ({})".format(arcpy.AddFieldDelimiters(ramp_points_fc, oid_field), oid_values)
    arcpy.management.MakeFeatureLayer("roads_lyr", "motorveg_lyr", where_clause="motorvegtype = 'Motortrafikkveg' or motorvegtype = 'Motorveg'")


        # Prepare a temporary single-point featureclass in-memory for GenerateNearTable input
    # We'll iterate each selected point separately to call GenerateNearTable (avoids adding fields to original)
    with arcpy.da.SearchCursor(ramp_points_fc, [oid_field, "SHAPE@"], where_clause=where) as scur:
        updates = []
        for oid, geom in scur:
            # Create an in-memory single-point featureclass
            temp_pt_fc = arcpy.CreateFeatureclass_management("in_memory", "tmp_pt", "POINT", spatial_reference=geom.spatialReference).getOutput(0)
            with arcpy.da.InsertCursor(temp_pt_fc, ["SHAPE@"]) as icur:
                icur.insertRow([geom])

            # 1) Try motorvei within radius
            near_table = "in_memory\\near_tbl"
            if arcpy.Exists(near_table):
                arcpy.Delete_management(near_table)

            # GenerateNearTable with Location = True to get NEAR_X, NEAR_Y representing the point on the line
            arcpy.analysis.GenerateNearTable(in_features=temp_pt_fc,
                                             near_features="motorveg_lyr",
                                             out_table=near_table,
                                             search_radius="100 Meters",
                                             location="LOCATION",
                                             closest="ALL")  # ALL so we can pick the nearest if multiple results

            target_xy = None
            if int(arcpy.GetCount_management(near_table).getOutput(0)) > 0:
                # pick row with smallest NEAR_DIST
                with arcpy.da.SearchCursor(near_table, ["NEAR_DIST", "NEAR_X", "NEAR_Y"]) as ntcur:
                    min_dist = None
                    min_xy = None
                    for nd, nx, ny in ntcur:
                        if nd is None:
                            continue
                        if (min_dist is None) or (nd < min_dist):
                            min_dist = nd
                            min_xy = (nx, ny)
                    if min_xy:
                        target_xy = min_xy

            # 2) If no motorvei found within radius, find closest on road_fc (no radius)
            if target_xy is None:
                # remove prior near table
                if arcpy.Exists(near_table):
                    arcpy.Delete_management(near_table)
                arcpy.analysis.GenerateNearTable(in_features=temp_pt_fc,
                                                 near_features="roads_lyr",
                                                 out_table=near_table,
                                                 search_radius="100 Meters",
                                                 location="LOCATION",
                                                 closest="ALL")
                if int(arcpy.GetCount_management(near_table).getOutput(0)) > 0:
                    with arcpy.da.SearchCursor(near_table, ["NEAR_DIST", "NEAR_X", "NEAR_Y"]) as ntcur:
                        min_dist = None
                        min_xy = None
                        for nd, nx, ny in ntcur:
                            if nd is None:
                                continue
                            if (min_dist is None) or (nd < min_dist):
                                min_dist = nd
                                min_xy = (nx, ny)
                        if min_xy:
                            target_xy = min_xy

            # Clean up near_table and temp point
            if arcpy.Exists(near_table):
                arcpy.Delete_management(near_table)
            if arcpy.Exists(temp_pt_fc):
                arcpy.Delete_management(temp_pt_fc)

            # If target found, store for update
            if target_xy:
                updates.append((oid, target_xy))


    # Apply updates in a single update cursor pass
    if updates:
        # build a dict for fast lookup
        upd_dict = {oid: xy for oid, xy in updates}
        with arcpy.da.UpdateCursor(ramp_points_fc, [oid_field, "SHAPE@"], where_clause=where) as ucur:
            for row in ucur:
                oid = row[0]
                if oid in upd_dict:
                    nx, ny = upd_dict[oid]
                    new_pt = arcpy.Point(nx, ny)
                    new_geom = arcpy.PointGeometry(new_pt, row[1].spatialReference)
                    row[1] = new_geom
                    ucur.updateRow(row)











    sr = arcpy.Describe(ramp_points_fc).spatialReference

    arcpy.management.CreateFeatureclass(
        os.path.dirname(out_fc),
        os.path.basename(out_fc),
        "POINT",
        spatial_reference=arcpy.Describe(ramp_points_fc).spatialReference
    )

    existing_out_fields = [f.name for f in arcpy.ListFields(out_fc) if f.type not in ("OID", "Geometry")]
    out_fields = ["SHAPE@"] + existing_out_fields
    in_fields = [oid_field, "SHAPE@"] + existing_out_fields

    with arcpy.da.SearchCursor(ramp_points_fc, in_fields) as scur, arcpy.da.InsertCursor(out_fc, out_fields) as icur:
        for row in scur:
            oid = int(row[0])
            orig_geom = row[1]
            other_attrs = list(row[2:])  # remaining attributes
            # Determine snapped location
            if oid in near1_map:
                nx, ny, nd = near1_map[oid]
                new_geom = arcpy.PointGeometry(arcpy.Point(nx, ny), sr)
            elif oid in near2_map:
                nx, ny, nd = near2_map[oid]
                new_geom = arcpy.PointGeometry(arcpy.Point(nx, ny), sr)
            else:
                new_geom = orig_geom

            insert_row = [new_geom] + other_attrs 
            icur.insertRow(insert_row)











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
    generalize_ramps()
