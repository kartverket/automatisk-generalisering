# Importing packages
from collections import defaultdict
import arcpy
import numpy as np
import math
import os

arcpy.env.overwriteOutput = True

# Importing custom input files modules
from input_data import input_n100

# Importing custom modules
from file_manager.n250.file_manager_roads import Road_N250
from env_setup import environment_setup
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools import custom_arcpy

data_files = {
    # Stores all the relevant file paths to the geodata used in this Python file
    "input": Road_N250.data_preparation___resolve_road_conflicts___n250_road.value,
    "output": Road_N250.dam__cleaned_roads__n250_road.value,
    "roads_input": Road_N250.dam__relevant_roads__n250_road.value,
    "dam_input": Road_N250.dam__relevant_dam__n250_road.value,
    "water_input": Road_N250.dam__relevant_water__n250_road.value,
    "dam_35m": Road_N250.dam__dam_buffer_35m__n250_road.value,
    "roads_inside": Road_N250.dam__roads_inside_with_data__n250_road.value,
    "roads_outside": Road_N250.dam__roads_outside__n250_road.value,
    "water_clipped": Road_N250.dam__water_clipped__n250_road.value,
    "water_center": Road_N250.dam__water_center__n250_road.value,
    "buffer_water": Road_N250.dam__buffer_water__n250_road.value,
    "water_singleparts": Road_N250.dam__water_singleparts__n250_road.value,
    "dam_buffer_sti": Road_N250.dam__dam_buffer_sti__n250_road.value,
    "roads_clipped_sti": Road_N250.dam__roads_clipped_sti__n250_road.value,
    "roads_moved": Road_N250.dam__roads_moved__n250_road.value,
    "roads_shifted": Road_N250.dam__roads_shifted__n250_road.value,
    "dam_150m": Road_N250.dam__dam_buffer_150m__n250_road.value,
    "dam_60m_flat": Road_N250.dam__dam_buffer_60m_flat__n250_road.value,
    "dam_5m": Road_N250.dam__dam_buffer_5m_flat__n250_road.value,
    "dam_60m": Road_N250.dam__dam_buffer_60m__n250_road.value,
    "water_55m": Road_N250.dam__water_buffer_55m__n250_road.value,
    "buffer_line": Road_N250.dam__dam_buffer_60m_line__n250_road.value,
    "intermediate": Road_N250.dam__roads_intermediate__n250_road.value,
    "paths_in_dam": Road_N250.dam__paths_in_dam__n250_road.value,
    "paths_in_dam_valid": Road_N250.dam__paths_in_dam_valid__n250_road.value,
}

files_to_delete = [
    # Stores all the keys from 'data_files' that should be deleted in the end
    "water_input",
    "dam_35m",
    "roads_inside",
    "roads_outside",
    "water_clipped",
    "water_center",
    "buffer_water",
    "water_singleparts",
    "dam_buffer_sti",
    "roads_clipped_sti",
    "roads_moved",
    "roads_shifted",
    "dam_150m",
    "dam_60m_flat",
    "dam_5m",
    "dam_60m",
    "water_55m",
    "intermediate",
    "paths_in_dam",
    "paths_in_dam_valid",
]


@timing_decorator
def generalize_dam():
    """
    Hva den gjør:
       Denne tar veier som går innen 60 meter av demninger og flytter de ut til 60 meter unna demningen.

    Hvorfor:
        For at symbologien skal være synlig i N100 kartet.
    """

    # Setup
    environment_setup.main()

    # Data preparation
    fetch_data()

    # Data preparation
    create_buffer()
    create_buffer_line()

    if data_check():
        # Move dam away from lakes
        clip_and_erase_pre()
        snap_merge_before_moving()
        edit_geom_pre()
        snap_and_merge_pre()

        # Snap roads to buffer
        roads = connect_roads_with_buffers()
        roads = merge_instances(roads)
        snap_roads(roads)
        remove_sharp_angles(roads)

        # Deletes all the intermediate files created during the process
        delete_intermediate_files()


##################
# Help functions
##################


def data_check():
    """
    sjekker om det er noen veier innen 60 meter av demninger
    """
    buffer_fc = data_files["dam_60m_flat"]
    arcpy.MakeFeatureLayer_management(data_files["roads_input"], "roads_lyr")
    arcpy.SelectLayerByLocation_management(
        in_layer="roads_lyr",
        overlap_type="INTERSECT",
        select_features=buffer_fc,
        selection_type="NEW_SELECTION",
    )
    count = int(arcpy.GetCount_management("roads_lyr").getOutput(0))
    if count == 0:
        print("No roads close to dam...")
        arcpy.management.CopyFeatures(
            in_features=data_files["input"], out_feature_class=data_files["output"]
        )
        return False
    else:
        return True


def build_backup(layer):
    """
    Bygger en backup dict av en layer
    """
    # 1. Discover all non-OID, non-Geometry fields in backup
    all_fields = arcpy.ListFields(layer)
    attr_fields = [
        f.name
        for f in all_fields
        if f.type not in ("OID", "Geometry", "Blob", "Raster")
    ]

    # 2. Build your cursor field lists
    #    - search_fields: includes OID@ so you can key the dict
    #    - insert_fields: includes SHAPE@ plus all attribute fields
    insert_fields = ["SHAPE@"] + attr_fields
    search_fields = ["OID@"] + insert_fields

    # 3. Read originals into an in-memory dict
    backup = {}
    with arcpy.da.SearchCursor(layer, search_fields) as s_cur:
        for row in s_cur:
            oid = row[0]
            geom_and_attrs = row[1:]
            backup[oid] = geom_and_attrs

    return backup


def restore_deleted_lines(layer, backup):
    """
    Gjennopretter features som har blitt slettet under snapping
    """
    deleted_lines = []
    # 1. Discover all non-OID, non-Geometry fields in backup
    all_fields = arcpy.ListFields(layer)
    attr_fields = [
        f.name
        for f in all_fields
        if f.type not in ("OID", "Geometry", "Blob", "Raster")
    ]

    # 2. Build your cursor field lists
    #    - search_fields: includes OID@ so you can key the dict
    #    - insert_fields: includes SHAPE@ plus all attribute fields
    insert_fields = ["SHAPE@"] + attr_fields

    # 3. Delete features with None geometry after snapping
    with arcpy.da.UpdateCursor(layer, ["OID@", "SHAPE@"]) as cursor:
        for oid, geom in cursor:
            if geom is None:
                deleted_lines.append(oid)
                cursor.deleteRow()

    # 4. Insert missing features back into your target feature class
    with arcpy.da.InsertCursor(layer, insert_fields) as i_cur:
        for oid in deleted_lines:
            if oid in backup:
                i_cur.insertRow(backup[oid])


def merge_all_lines2(fc, tolerance=5.0):
    """
    Merges all lines in a feature class that share endpoints and have the same objtype and vegkategori.
    """
    # 1. Determine non‐OID/Geometry fields and their positions
    all_fields = [
        f.name for f in arcpy.ListFields(fc) if f.type not in ("OID", "Geometry")
    ]

    # Ensure the required fields exist
    for req in ("objtype", "vegkategori"):
        if req not in all_fields:
            raise ValueError(f"Field '{req}' is missing in {fc}")

    idx_objtype = all_fields.index("objtype")
    idx_vegkategori = all_fields.index("vegkategori")

    # 2. Read all lines into memory
    lines = []
    with arcpy.da.SearchCursor(fc, ["OID@", "SHAPE@"] + all_fields) as cur:
        for oid, geom, *attrs in cur:
            lines.append({"oid": oid, "shape": geom, "attrs": attrs})

    # 3. Build adjacency graph—only if objtype & medium match *and* endpoints are within tolerance
    adj = defaultdict(set)
    for i, ln1 in enumerate(lines):
        ot1 = ln1["attrs"][idx_objtype]
        md1 = ln1["attrs"][idx_vegkategori]
        eps1 = get_endpoints_cords(ln1["shape"])

        for j, ln2 in enumerate(lines[i + 1 :], start=i + 1):
            # Skip if attributes don’t match
            ot2 = ln2["attrs"][idx_objtype]
            md2 = ln2["attrs"][idx_vegkategori]
            if (ot1, md1) != (ot2, md2):
                continue

            # Check endpoint proximity
            eps2 = get_endpoints_cords(ln2["shape"])
            if any(within_tol(p1, p2, tolerance) for p1 in eps1 for p2 in eps2):
                adj[i].add(j)
                adj[j].add(i)

    # 4. Find connected components (clusters)
    visited = set()
    clusters = []
    for i in range(len(lines)):
        if i in visited:
            continue
        stack, comp = [i], []
        while stack:
            curr = stack.pop()
            if curr in visited:
                continue
            visited.add(curr)
            comp.append(curr)
            stack.extend(adj[curr] - visited)
        clusters.append(comp)

    # 5. Union geometries per cluster and carry forward attributes
    merged = []
    for comp in clusters:
        shapes = [lines[k]["shape"] for k in comp]
        # dissolve shapes
        cumul = shapes[0]
        for s in shapes[1:]:
            cumul = cumul.union(s)
        # re‐use attrs from the first member of the cluster
        merged.append((cumul, lines[comp[0]]["attrs"]))

    # 6. Overwrite the feature class with merged results
    arcpy.DeleteRows_management(fc)
    out_fields = ["SHAPE@"] + all_fields
    with arcpy.da.InsertCursor(fc, out_fields) as icur:
        for geom, attrs in merged:
            icur.insertRow([geom] + attrs)

    print(f"Merged {len(lines)} lines into {len(merged)} features.")


def within_tol(pt1, pt2, tol):
    """Euclidean distance test."""
    return math.hypot(pt1.X - pt2.X, pt1.Y - pt2.Y) <= tol


def get_endpoints_cords(polyline):
    """Return a list of Point objects for the start/end of every part."""
    pts = []
    for part in polyline:
        coords = list(part)
        if coords:
            pts.append(coords[0])
            pts.append(coords[-1])
    return pts


def snap_by_objtype(layer):
    """
    Snapper veier med samme objtype
    """
    # Get all unique objtypes
    objtypes = set()
    with arcpy.da.SearchCursor(layer, ["objtype"]) as cursor:
        for row in cursor:
            objtypes.add(row[0])

    for obj in objtypes:
        # Make a feature layer for this objtype
        layer_name = f"roads_moved_{obj}"
        arcpy.management.MakeFeatureLayer(layer, layer_name, f"objtype = '{obj}'")
        # Snap only within this objtype group
        snap_env = [[layer_name, "END", "40 Meters"]]
        arcpy.Snap_edit(layer_name, snap_env)

        arcpy.Delete_management(layer_name)


def move_line_away(geom, near_x, near_y, distance):
    """
    Move a polyline geometry away from a point (near_x, near_y) by a specified distance.
    """
    sr = geom.spatialReference
    centroid = geom.centroid
    dx = centroid.X - near_x
    dy = centroid.Y - near_y
    length = math.hypot(dx, dy)
    if length == 0:
        # No movement if centroid is at water center
        shift_x, shift_y = 0, 0
    else:
        scale = distance / length
        shift_x = dx * scale
        shift_y = dy * scale

    new_parts = arcpy.Array()
    for part in geom:
        part_arr = arcpy.Array()
        for p in part:
            new_x = p.X + shift_x
            new_y = p.Y + shift_y
            part_arr.add(arcpy.Point(new_x, new_y))
        new_parts.add(part_arr)
    return arcpy.Polyline(new_parts, sr)


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


def add_road(road_lyr: str, roads: dict[list], tolerance: float = 2.0) -> dict[list]:
    """
    Adds roads selected in road_lyr to the dictionary roads
    if they are connected (closer than tolerance).
    These are the roads relevant for the movement analysis.

    Args:
        road_lyr (str): String to the feature layer
        roads (dict[list]): Dictionary with relevant road objects
        tolerance (float): Float number showing tolerance of connection to be added, default 2.0

    Returns:
        roads (dict[list]): Updated dictionary with relevant road objects
    """
    # Build endpoint lookup for existing roads in the road dictionary
    endpoint_lookup = defaultdict(list)
    for oid, (geom, _, _) in roads.items():
        start, end = get_endpoints(geom)
        # Uses rounded coordinates for fast lookup and more similarity
        for pt in [start, end]:
            key = (round(pt.centroid.X, 2), round(pt.centroid.Y, 2))
            endpoint_lookup[key].append(oid)

    # Add new roads if they have a endpoint closer than tolerance to an existing road
    with arcpy.da.SearchCursor(
        road_lyr, ["OID@", "SHAPE@", "objtype", "vegkategori"]
    ) as cursor:
        for oid, geom, obj, category in cursor:
            if oid in roads:
                continue
            start, end = get_endpoints(geom)
            added = False
            for pt in [start, end]:
                key = (round(pt.centroid.X, 2), round(pt.centroid.Y, 2))
                # Check if the endpoints are close to another geometry
                for other_key in endpoint_lookup:
                    for other_oid in endpoint_lookup.get(other_key, []):
                        other_geom = roads[other_oid][0]
                        distance = pt.distanceTo(other_geom)
                        if distance < tolerance:
                            roads[oid] = [geom, obj, category]
                            # Add endpoints of this road to lookup for future checks
                            for new_pt in [start, end]:
                                new_key = (
                                    round(new_pt.centroid.X, 2),
                                    round(new_pt.centroid.Y, 2),
                                )
                                endpoint_lookup[new_key].append(oid)
                            added = True
                            break
                    if added:
                        break
                if added:
                    break

    return roads


def find_merge_candidate(
    short_geom: arcpy.Geometry,
    all_roads: list[list],
    buffer: arcpy.Geometry,
    tolerance: float = 2.0,
) -> str | None:
    """
    Finds a road geometry that shares a common end point

    Args:
        short_geom (arcpy.Geometry): The geometry that should be checked
        all_roads (list[list]): oid and geom of relevant roads to connect to
        buffer (arcpy.Geometry): The geometry of the relevant buffer
        tolerance (float): Float number showing tolerance of connection to be added, default 2.0

    Returns:
        str | None: The oid of the matched road oid if one, else None
    """
    start, end = get_endpoints(short_geom)
    for oid, geom in all_roads:
        s, e = get_endpoints(geom)
        endpoint_pairs = [(start, s), (start, e), (end, s), (end, e)]
        for p1, p2 in endpoint_pairs:
            if p1.distanceTo(p2) < tolerance:
                if buffer.contains(p1) and buffer.contains(p2):
                    return oid
    return None


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


def create_single_buffer_line(buffer: arcpy.Geometry, water) -> None:
    """
    Creates a polyline showing the edges of a buffer, excluding areas in water,
    and saves it to a temporarly 'in_memory'-layer.

    Args:
        buffer (arcpy.Geometry): The buffer to create the line from
        water: The feature layer containing the water geometries
    """
    line = r"in_memory\dam_line_single"
    final = r"in_memory\dam_line_final"
    arcpy.management.PolygonToLine(buffer, line)
    arcpy.analysis.Erase(line, water, final)


def cluster_points(points: list[tuple], tolerance: float = 1.0) -> list[list]:
    """
    Clusters points that are within the tolerance
    distance of each other.

    Args:
        points (list[tuple]): A list of tuples containing all the points to be clustered
        tolerance (float): Float number showing tolerance of connection to be clustered, default 2.0

    Returns:
        list[list]: A list of list where the internal lists are each cluster with the relevant point information
    """
    clusters = []
    for pt, idx in points:
        found = False
        for cluster in clusters:
            if any(pt.distanceTo(other[0]) < tolerance for other in cluster):
                # The points are close enough to be in the same cluster
                # With other words: snap them to the same coordinate
                cluster.append((pt, idx))
                found = True
                break
        if not found:
            clusters.append([(pt, idx)])
    return clusters


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
        return 360  # Undefined angle, treated as straight line

    # Calculate scalar product
    dot = np.dot(v1, v2)

    # Calculates angle in degrees
    cos_angle = dot / (len1 * len2)
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    angle_rad = np.arccos(cos_angle)

    return np.degrees(angle_rad)


def not_road_intersection(point: arcpy.Geometry, road_oid: str, roads: str) -> bool:
    """
    Checks if the point is connected to a road intersection or not.

    Args:
        point (arcpy.Geometry): The point geometry to consider
        road_oid (str): The oid of the road containing this point
        roads (str): Feature layer containing all the relevant roads

    Returns:
        bool: False if the point is in a road intersection, otherwise True
    """
    point_geom = arcpy.PointGeometry(point)
    tolerance = 5

    with arcpy.da.SearchCursor(roads, ["OID@", "SHAPE@"]) as cursor:
        for oid, shape in cursor:
            if shape == None or oid == road_oid:
                continue
            if shape.distanceTo(point_geom) <= tolerance:
                return False
    return True


##################
# Main functions
##################


@timing_decorator
def fetch_data():
    print("Fetching data...")

    input = [
        [data_files["input"], None, data_files["roads_input"]],  # Roads
        [input_n100.AnleggsLinje, "objtype = 'Dam'", data_files["dam_input"]],  # Dam
        [
            input_n100.ArealdekkeFlate,
            "OBJTYPE = 'Havflate' OR OBJTYPE = 'Innsjø' OR OBJTYPE = 'InnsjøRegulert'",
            data_files["water_input"],
        ],  # Water
    ]
    for data in input:
        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=data[0],
            expression=data[1],
            output_name=data[2],
            selection_type="NEW_SELECTION",
        )
    print("Data fetched!")


@timing_decorator
def create_buffer():
    print("Creating buffers...")
    dam_fc = data_files["dam_input"]
    water_fc = data_files["water_input"]

    arcpy.management.MakeFeatureLayer(water_fc, "water_lyr")
    arcpy.management.SelectLayerByLocation(
        in_layer="water_lyr",
        select_features=dam_fc,
        overlap_type="WITHIN_A_DISTANCE",
        search_distance="100 Meters",
        selection_type="NEW_SELECTION",
    )

    buffers = [
        [dam_fc, data_files["dam_60m_flat"], "60 Meters"],
        [dam_fc, data_files["dam_5m"], "5 Meters"],
        [dam_fc, data_files["dam_60m"], "60 Meters"],
        ["water_lyr", data_files["water_55m"], "55 Meters"],
    ]
    for i in range(len(buffers)):
        type = "FLAT" if i < 2 else "ROUND"
        arcpy.analysis.Buffer(
            in_features=buffers[i][0],
            out_feature_class=buffers[i][1] + "_buffer",
            buffer_distance_or_field=buffers[i][2],
            line_end_type=type,
            dissolve_option="NONE",
            method="PLANAR",
        )
        arcpy.management.Dissolve(
            in_features=buffers[i][1] + "_buffer",
            out_feature_class=buffers[i][1],
            dissolve_field=[],
            multi_part="SINGLE_PART",
        )
    print("Buffers created")


@timing_decorator
def create_buffer_line():
    print("Creates dam buffer as line...")
    buffer = data_files["dam_60m"]
    line = data_files["buffer_line"]
    arcpy.management.PolygonToLine(in_features=buffer, out_feature_class=line)
    print("Dam buffer as line created")


@timing_decorator
def clip_and_erase_pre():
    """
    Hva den gjør:
        Seperer veier som er innen en mindre buffer rundt demningene og veier som er utenfor, i forbredelse på å flytte veiene.
        Hvis bru eller sti går over demningen blir det ikke inkludert i veier som skal flyttes
    """
    print("Clipping and erasing roads near dam...")
    dam_fc = data_files["dam_input"]
    roads_fc = data_files["roads_input"]

    buffer_fc = data_files["dam_35m"]
    pre_dissolve = data_files["roads_inside"]
    outside_fc = data_files["roads_outside"]

    water = data_files["water_input"]
    water_clipped = data_files["water_clipped"]
    water_center = data_files["water_center"]
    buffer_water = data_files["buffer_water"]
    water_single = data_files["water_singleparts"]

    buffer_sti = data_files["dam_buffer_sti"]
    clipped_sti = data_files["roads_clipped_sti"]

    arcpy.Buffer_analysis(
        dam_fc, buffer_fc, "35 Meters", line_end_type="FLAT", dissolve_option="NONE"
    )

    # sletter buffere med bruer slik at de ikke blir flyttet
    fld = arcpy.AddFieldDelimiters(roads_fc, "medium")
    arcpy.MakeFeatureLayer_management(
        roads_fc, "roads_L_lyr", where_clause=f"{fld} = 'L'"
    )

    arcpy.MakeFeatureLayer_management(buffer_fc, "buffer_lyr")

    arcpy.SelectLayerByLocation_management(
        in_layer="buffer_lyr", overlap_type="INTERSECT", select_features="roads_L_lyr"
    )

    arcpy.DeleteFeatures_management("buffer_lyr")

    # sletter buffere med stier som går rett over demninger slik at de ikke blir flyttet
    arcpy.Buffer_analysis(
        dam_fc, buffer_sti, "5 Meters", line_end_type="FLAT", dissolve_option="NONE"
    )
    arcpy.Clip_analysis(roads_fc, buffer_sti, clipped_sti)

    fields = ["objtype", "SHAPE@"]

    with arcpy.da.UpdateCursor(clipped_sti, fields) as cursor:
        for objtype, geom in cursor:
            length = geom.length
            # Keep only features where objtype == 'sti' and length > 50
            if objtype != "Sti" or length <= 50:
                cursor.deleteRow()

    arcpy.MakeFeatureLayer_management(buffer_fc, "buffer_lyr_sti")
    arcpy.MakeFeatureLayer_management(clipped_sti, "roads_clipped_sti_lyr")

    arcpy.SelectLayerByLocation_management(
        "buffer_lyr_sti", "INTERSECT", "roads_clipped_sti_lyr"
    )

    arcpy.DeleteFeatures_management("buffer_lyr_sti")

    # Clip and erase veier
    arcpy.Clip_analysis(roads_fc, buffer_fc, pre_dissolve)
    arcpy.Erase_analysis(roads_fc, buffer_fc, outside_fc)

    # Lag senterpunkt for vann inni buffer
    arcpy.Buffer_analysis(dam_fc, buffer_water, "75 Meters", dissolve_option="NONE")
    arcpy.Clip_analysis(water, buffer_water, water_clipped)
    arcpy.MultipartToSinglepart_management(water_clipped, water_single)
    arcpy.FeatureToPoint_management(water_single, water_center, "CENTROID")


@timing_decorator
def snap_merge_before_moving():
    """
    Hva den gjør:
        snapper og merger veier som er like før de blir flyttet
    Hvorfor:
        gjør det letter å beholde sammenhengen i veiene etter flytting
    """
    inside_wdata_fc = data_files["roads_inside"]

    tolerance = 40.0
    # Precompute squared tolerance for faster distance checks
    tol2 = tolerance * tolerance

    # Helper: squared distance between two arcpy.Points
    def _sq_dist(p1, p2):
        dx = p1.X - p2.X
        dy = p1.Y - p2.Y
        return dx * dx + dy * dy

    # Store seen endpoint‐pairs as a list of tuples: ((x1,y1),(x2,y2))
    seen = []

    # Sletter linjer som har nærme endepunkter, for å unngå at det blir dobbelt med linjer etter flytting
    with arcpy.da.UpdateCursor(inside_wdata_fc, ["OID@", "SHAPE@"]) as cursor:
        for _, geom in cursor:
            # Extract endpoints
            pts = get_endpoints_cords(geom)
            if len(pts) < 2:
                # Skip degenerate geometries
                continue
            p_start, p_end = pts[0], pts[1]
            # Check against seen endpoint pairs
            is_duplicate = False
            for (sx, sy), (ex, ey) in seen:
                # Two possible match orders
                d1 = _sq_dist(p_start, arcpy.Point(sx, sy))
                d2 = _sq_dist(p_end, arcpy.Point(ex, ey))
                d3 = _sq_dist(p_start, arcpy.Point(ex, ey))
                d4 = _sq_dist(p_end, arcpy.Point(sx, sy))

                if (d1 <= tol2 and d2 <= tol2) or (d3 <= tol2 and d4 <= tol2):
                    cursor.deleteRow()
                    is_duplicate = True
                    break

            if not is_duplicate:
                # Record this endpoint pair
                seen.append(((p_start.X, p_start.Y), (p_end.X, p_end.Y)))

    backup = build_backup(inside_wdata_fc)
    snap_by_objtype(inside_wdata_fc)
    arcpy.Snap_edit(inside_wdata_fc, [[inside_wdata_fc, "END", "40 Meters"]])
    restore_deleted_lines(inside_wdata_fc, backup)

    merge_all_lines2(inside_wdata_fc, tolerance=5.0)


@timing_decorator
def edit_geom_pre():
    """
    Flytter veier inni buffer litt unna vannet
    """
    print("Moving roads away from water...")
    inside_wdata_fc = data_files["roads_inside"]
    roadlines_moved = data_files["roads_moved"]

    water_center = data_files["water_center"]

    inside_sr = arcpy.Describe(inside_wdata_fc).spatialReference
    temp_fc = inside_wdata_fc + "_temp"

    # Copy features for editing
    arcpy.management.CopyFeatures(inside_wdata_fc, temp_fc)

    # Create output feature class
    out_path, out_name = os.path.split(roadlines_moved)
    arcpy.CreateFeatureclass_management(
        out_path=out_path,
        out_name=out_name,
        geometry_type="POLYLINE",
        template=temp_fc,
        spatial_reference=inside_sr,
    )

    # Generate Near Table
    near_table = "in_memory\\near_table"
    arcpy.analysis.GenerateNearTable(
        in_features=temp_fc,
        near_features=water_center,
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

    fields = ["OID@", "SHAPE@"] + [
        f.name for f in arcpy.ListFields(temp_fc) if f.type not in ("OID", "Geometry")
    ]

    with arcpy.da.SearchCursor(temp_fc, fields) as search, arcpy.da.InsertCursor(
        roadlines_moved, fields[1:]
    ) as insert:

        for row in search:
            oid = row[0]
            geom = row[1]
            shape_length = geom.length
            if not geom or oid not in near_lookup:
                insert.insertRow([geom] + list(row[2:]))
                continue

            if shape_length < 35:
                # Do not move short lines, just copy them
                insert.insertRow([geom] + list(row[2:]))
                continue

            near_x, near_y = near_lookup[oid]
            shifted = move_line_away(geom, near_x, near_y, distance=35)
            insert.insertRow([shifted] + list(row[2:]))


@timing_decorator
def snap_and_merge_pre():
    """
    snapper og kombinerer veier som har blitt flyttet og veier som ikke har blitt flyttet
    """
    print("Snapping and merging roads after moving...")
    dam_fc = data_files["dam_input"]
    roadlines_moved = data_files["roads_moved"]
    outside_fc = data_files["roads_outside"]
    final_fc = data_files["roads_shifted"]

    dam_150m = data_files["dam_150m"]

    # Define snap environment
    snap_env = [[outside_fc, "END", "40 Meters"]]

    # Snap
    arcpy.Snap_edit(roadlines_moved, snap_env)

    snap_env2 = [[roadlines_moved, "END", "50 Meters"]]

    arcpy.Buffer_analysis(dam_fc, dam_150m, "150 Meters")
    arcpy.MakeFeatureLayer_management(outside_fc, "outside_lyr")
    arcpy.SelectLayerByLocation_management(
        in_layer="outside_lyr", overlap_type="INTERSECT", select_features=dam_150m
    )

    arcpy.Snap_edit("outside_lyr", snap_env2)

    # Merge the two sets
    arcpy.Merge_management([roadlines_moved, outside_fc], final_fc)


@timing_decorator
def connect_roads_with_buffers() -> dict[list]:
    """
    Creates a dictionary where the keys are al the buffer oids,
    and the values are lists of lists containing the road geometry and
    information for all the roads connected to this buffer.

    Returns:
        dict[list]: A dictionary with key = buffer_oid, and values are
            lists of the relevant information (oid, shape, ...) of the
            related roads
    """
    print("Connects roads with buffers...")

    roads_fc = data_files["roads_shifted"]
    intermediate_fc = data_files["intermediate"]
    buffer_flat_fc = data_files["dam_60m_flat"]
    buffer_round_fc = data_files["dam_60m"]

    # Starts by changing the relevant roads from potentially multipart to singlepart
    arcpy.management.MakeFeatureLayer(roads_fc, "roads_lyr_round")
    arcpy.management.SelectLayerByLocation(
        in_layer="roads_lyr_round",
        overlap_type="WITHIN_A_DISTANCE",
        search_distance="0 Meters",
        select_features=buffer_round_fc,
    )
    arcpy.management.MultipartToSinglepart(
        "roads_lyr_round", intermediate_fc
    )  # This creates a new layer
    arcpy.management.SelectLayerByLocation(  # Need to add the roads outside the buffer as well
        in_layer="roads_lyr_round", selection_type="SWITCH_SELECTION"
    )
    arcpy.management.Append(
        inputs="roads_lyr_round", target=intermediate_fc, schema_type="NO_TEST"
    )

    # Finds all roads 60m or closer to a dam
    arcpy.management.MakeFeatureLayer(intermediate_fc, "roads_lyr_flat")
    arcpy.management.MakeFeatureLayer(intermediate_fc, "roads_lyr_round_2")

    arcpy.management.SelectLayerByLocation(
        in_layer="roads_lyr_flat",
        selection_type="NEW_SELECTION",
        overlap_type="WITHIN_A_DISTANCE",
        search_distance="0 Meters",
        select_features=buffer_flat_fc,
    )
    arcpy.management.SelectLayerByLocation(
        in_layer="roads_lyr_round_2",
        selection_type="NEW_SELECTION",
        overlap_type="WITHIN_A_DISTANCE",
        search_distance="0 Meters",
        select_features=buffer_round_fc,
    )

    # Collects all the relevant roads
    roads = {}
    with arcpy.da.SearchCursor(
        "roads_lyr_flat", ["OID@", "SHAPE@", "objtype", "vegkategori"]
    ) as cursor:
        # All in the flat buffer
        for oid, geom, obj, category in cursor:
            if oid not in roads:
                roads[oid] = [geom, obj, category]

    roads = add_road(
        "roads_lyr_round_2", roads
    )  # Only add the roads in the round buffer that is connected to a road in the flat buffer

    # Connects roads to buffers (one road can be connected to several buffers)
    buffer_polygons = [
        (row[0], row[1])
        for row in arcpy.da.SearchCursor(buffer_round_fc, ["OID@", "SHAPE@"])
    ]
    buffer_to_roads = defaultdict(list)
    print("Finding nearest buffer for each road...")
    for key in roads:
        for oid, buffer_poly in buffer_polygons:
            dist = roads[key][0].distanceTo(buffer_poly)
            if dist < 1:
                buffer_to_roads[oid].append(
                    [key, roads[key][0], roads[key][1], roads[key][2]]
                )

    print("Roads connected to buffers.")

    return buffer_to_roads


@timing_decorator
def merge_instances(roads: dict[list]) -> defaultdict[list]:
    """
    Merge the selected roads.
    For each road: select the relevant instances.
    For each type and category: merge the relevant instances.

    Args:
        roads (dict[list]): Dictionary containing all the buffer -> road connections

    Returns:
        defaultdict[list]: An updated dictionary with the merged geometry.
            The list do contain the oid for every connected road
    """
    print("Merge connected instances of same type...")

    intermediate_fc = data_files["intermediate"]

    buffer_fc = data_files["dam_60m"]
    buffer_polygons = {
        row[0]: row[1] for row in arcpy.da.SearchCursor(buffer_fc, ["OID@", "SHAPE@"])
    }

    # Global geometry-dictionary
    roads_by_oid = {
        oid: [geom, objt, category]
        for buffer_id in roads
        for oid, geom, objt, category in roads[buffer_id]
    }
    roads_to_buffers = defaultdict(set)
    for buffer_id, road_list in roads.items():
        for oid, _, _, _ in road_list:
            roads_to_buffers[oid].add(buffer_id)

    to_delete = set()
    new_roads = defaultdict(list)

    arcpy.management.MakeFeatureLayer(intermediate_fc, "roads_lyr")

    for buffer_id in roads:
        buffer_geom = buffer_polygons[buffer_id]
        relevant_roads = [
            oid for oid, ids in roads_to_buffers.items() if buffer_id in ids
        ]
        relevant_roads = [
            [oid, roads_by_oid[oid][0], roads_by_oid[oid][1], roads_by_oid[oid][2]]
            for oid in relevant_roads
        ]
        types = {objtype for _, _, objtype, _ in relevant_roads}
        categories = {category for _, _, _, category in relevant_roads}

        if len(relevant_roads) == 0:
            continue

        # Checks if there are bridges in the buffer
        # If so, skip this one
        sql = f"OBJECTID IN ({','.join(str(oid) for oid, _, _, _ in relevant_roads)})"
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view="roads_lyr",
            selection_type="NEW_SELECTION",
            where_clause=sql,
        )
        bridge = False
        with arcpy.da.UpdateCursor("roads_lyr", ["medium"]) as cursor:
            for medium in cursor:
                if medium[0] == "L":
                    bridge = True
                    break
        if bridge:
            continue

        for t in types:
            for c in categories:
                roads_to_edit = [
                    [oid, geom]
                    for oid, geom, objt, category in relevant_roads
                    if objt == t and category == c
                ]

                if len(roads_to_edit) == 0:
                    continue

                sql = f"OBJECTID IN ({','.join(str(oid) for oid, _ in roads_to_edit)})"

                arcpy.management.SelectLayerByAttribute(
                    in_layer_or_view="roads_lyr",
                    selection_type="NEW_SELECTION",
                    where_clause=sql,
                )

                with arcpy.da.UpdateCursor(
                    "roads_lyr", ["OID@", "SHAPE@"]
                ) as update_cursor:
                    for oid, geom in update_cursor:
                        if oid in to_delete:
                            continue
                        if geom is None:
                            update_cursor.deleteRow()
                            del roads_by_oid[oid]
                            del roads_to_buffers[oid]
                            continue
                        # Finds candidate to merge
                        merge_oid = find_merge_candidate(
                            geom,
                            [
                                r
                                for r in roads_to_edit
                                if r[0] != oid and r[0] not in to_delete
                            ],
                            buffer_geom,
                        )
                        if (
                            merge_oid is None
                            or merge_oid == oid
                            or merge_oid in to_delete
                        ):
                            continue
                        merge_geom = roads_by_oid[merge_oid][0]
                        # Combine the two geometries
                        new_geom = merge_lines(geom, merge_geom)
                        if new_geom is None:
                            continue
                        if not isinstance(new_geom, arcpy.Geometry):
                            continue
                        update_cursor.updateRow((oid, new_geom))
                        roads_by_oid[oid] = [new_geom, t, c]
                        # Moves the connected buffers of merge_oid to oid
                        # because this road now does contain these buffers as well
                        if merge_oid in roads_to_buffers:
                            roads_to_buffers[oid].update(roads_to_buffers[merge_oid])
                        # Deletes the small duplicate of the road
                        to_delete.add(merge_oid)
                        if merge_oid in roads_to_buffers:
                            roads_to_buffers.pop(merge_oid, None)
                        if merge_oid in roads_by_oid:
                            roads_by_oid.pop(merge_oid, None)

    if len(to_delete) > 0:
        sql = f"OBJECTID IN ({','.join(str(oid) for oid in to_delete)})"
        arcpy.management.SelectLayerByAttribute("roads_lyr", "NEW_SELECTION", sql)

        with arcpy.da.UpdateCursor("roads_lyr", ["OID@"]) as delete_cursor:
            for row in delete_cursor:
                oid = row[0]
                delete_cursor.deleteRow()
                roads_by_oid.pop(oid, None)
                roads_to_buffers.pop(oid, None)

    new_roads = defaultdict(set)
    for oid, buffer_ids in roads_to_buffers.items():
        for buffer_id in buffer_ids:
            new_roads[buffer_id].add(oid)

    for key in new_roads:
        new_roads[key] = list(new_roads[key])

    print("Instances merged!")

    return new_roads


@timing_decorator
def snap_roads(roads: dict[list]) -> None:
    """
    Snaps roads to the buffer edges.
    Points that are close to each other are snapped to the same point.

    Args:
        roads (dict[list]): Dictionary containing the relationships between buffers and roads
    """
    print("Snap roads to buffer...")

    intermediate_fc = data_files["intermediate"]
    buffer_fc = data_files["dam_60m"]
    water_buffer_fc = data_files["water_55m"]
    buffer_for_paths = data_files["dam_5m"]

    buffer_polygons = [
        (row[0], row[1]) for row in arcpy.da.SearchCursor(buffer_fc, ["OID@", "SHAPE@"])
    ]

    # Fetches all the paths going over dam
    # These should not be snapped
    paths_in_dam = data_files["paths_in_dam"]
    paths_in_dam_valid = data_files["paths_in_dam_valid"]
    arcpy.management.MakeFeatureLayer(
        intermediate_fc, "paths_over_dam", where_clause="objtype = 'Sti'"
    )
    arcpy.analysis.Intersect(
        in_features=["paths_over_dam", buffer_for_paths], out_feature_class=paths_in_dam
    )

    paths_to_avoid = set()
    with arcpy.da.SearchCursor(paths_in_dam, ["OID@", "SHAPE@"]) as cursor:
        for oid, geom in cursor:
            if geom.length > 50:
                paths_to_avoid.add(oid)

    if len(paths_to_avoid) > 0:  # If some...
        # ... fetch the entire geometry and oid for these paths
        sql = f"OBJECTID IN ({','.join(str(oid) for oid in paths_to_avoid)})"
        arcpy.management.MakeFeatureLayer(paths_in_dam, "paths_in_dam_lyr")
        arcpy.management.SelectLayerByAttribute(
            "paths_in_dam_lyr", "NEW_SELECTION", where_clause=sql
        )
        arcpy.management.CopyFeatures("paths_in_dam_lyr", paths_in_dam_valid)
        arcpy.management.SelectLayerByLocation(
            "paths_over_dam", "INTERSECT", paths_in_dam_valid
        )

        arcpy.management.MakeFeatureLayer(intermediate_fc, "roads_lyr")

        paths_to_avoid = set()
        path_geometries = {
            row[0]
            for row in arcpy.da.SearchCursor("paths_over_dam", ["OID@", "SHAPE@"])
        }
        with arcpy.da.UpdateCursor("roads_lyr", ["OID@", "SHAPE@"]) as cursor:
            for oid, geom in cursor:
                if geom is None:
                    cursor.deleteRow()
                    continue
                if oid in path_geometries:
                    paths_to_avoid.add(oid)

    for buf_oid, buffer_poly in buffer_polygons:
        # For all buffer polygons, create the corresponding valid buffer line
        line = r"in_memory\dam_line_final"
        create_single_buffer_line(buffer_poly, water_buffer_fc)
        buffer_lines = [row[0] for row in arcpy.da.SearchCursor(line, ["SHAPE@"])]
        if not buffer_lines:
            # If no line, skip
            continue
        buffer_line = buffer_lines[0]

        # Fetch all roads associated with this buffer
        road_list = roads.get(buf_oid, [])
        if len(road_list) == 0:
            # If no roads, skip
            continue
        oids = ",".join(str(oid) for oid in road_list)
        sql = f"OBJECTID IN ({oids})"
        arcpy.management.SelectLayerByAttribute("roads_lyr", "CLEAR_SELECTION")
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view="roads_lyr",
            selection_type="NEW_SELECTION",
            where_clause=sql,
        )
        relevant_roads = []
        skip = False
        with arcpy.da.SearchCursor("roads_lyr", ["OID@", "SHAPE@", "medium"]) as cursor:
            for oid, geom, medium in cursor:
                if oid in paths_to_avoid:
                    skip = True
                    break
                if medium == "L":
                    skip = True
                    break
                relevant_roads.append((oid, geom))
        # If the road(s) inside the buffer is a bridge, e.i. medium = "L",
        # or the buffer contains paths on top of the buffer,
        # do not snap it
        if skip:
            continue

        # Collects points inside the buffer polygon
        points_to_cluster = []
        for road_oid, line in relevant_roads:
            for part_idx, part in enumerate(line):
                for pt_idx, pt in enumerate(part):
                    if pt is None:
                        # Only valid points accepted
                        continue
                    pt_geom = arcpy.PointGeometry(pt, line.spatialReference)
                    if buffer_poly.contains(pt_geom):
                        # The point is inside the buffer polygon
                        points_to_cluster.append(
                            (pt_geom, (road_oid, part_idx, pt_idx))
                        )

        # Cluster points that are close to each other
        clusters = cluster_points(points_to_cluster, tolerance=1.0)

        # Snap points to the buffer line
        snap_points = {}
        for cluster in clusters:
            ref_pt = cluster[0][0]  # Fetches the first point
            result = buffer_line.queryPointAndDistance(ref_pt)
            snap_pt = result[0]  # Closest point on buffer line
            for (
                _,
                idx,
            ) in (
                cluster
            ):  # ... and adjust the rest of the points in the cluster to the ref_pt
                snap_points[idx] = snap_pt

        with arcpy.da.UpdateCursor("roads_lyr", ["OID@", "SHAPE@"]) as update_cursor:
            # Update each road
            for row in update_cursor:
                oid, geom = row
                changed = False
                new_parts = []
                for part_idx, part in enumerate(geom):
                    # For each part of the road
                    new_part = []
                    for pt_idx, pt in enumerate(part):
                        idx = (oid, part_idx, pt_idx)
                        if idx in snap_points:
                            # If the point should be snapped, snap it
                            new_pt = snap_points[idx]
                            new_part.append(new_pt.firstPoint)
                            changed = True
                        else:
                            new_part.append(pt)
                    new_parts.append(arcpy.Array(new_part))
                if changed:
                    # Update the road geometry if any point was changed
                    new_line = arcpy.Polyline(
                        arcpy.Array(new_parts), geom.spatialReference
                    )
                    geom = new_line
                    update_cursor.updateRow((oid, geom))

    arcpy.management.Integrate(in_features="roads_lyr", cluster_tolerance="5 Meters")

    print("Roads snapped to buffers!")


@timing_decorator
def remove_sharp_angles(roads: dict[list]) -> None:
    """
    Detects sharp edges in the polylines and deletes these points.

    Args:
        roads (dict[list]): Dictionary containing the relationships between buffers and roads
    """
    print("Removes sharp angles...")

    intermediate_fc = data_files["intermediate"]
    cleaned_roads_fc = data_files["output"]

    # Fetch all the road oids
    oids = ",".join(str(oid) for key in roads.keys() for oid in roads[key])
    if len(oids.split(",")) > 0:
        sql = f"OBJECTID IN ({oids})"

        arcpy.management.MakeFeatureLayer(intermediate_fc, "roads_lyr")

        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view="roads_lyr",
            selection_type="NEW_SELECTION",
            where_clause=sql,
        )

        num = 0  # Number of roads with deleted points

        with arcpy.da.UpdateCursor("roads_lyr", ["OID@", "SHAPE@"]) as cursor:
            for row in cursor:
                # Fetch points for each road with valid geometry
                if row[1] == None:
                    cursor.deleteRow()
                    continue
                points = []
                for part in row[1]:
                    for p in part:
                        points.append(p)

                i = 0
                tolerance = 70
                count = len(points)

                while i + 2 < len(points):
                    p1, p2, p3 = points[i : i + 3]
                    # Calculates the angle between the three points
                    # With other words: the angle in the centre point
                    angle = calculate_angle(p1, p2, p3)
                    # If the angle is sharper than the tolerance - delete the point
                    if angle < tolerance or angle > (360 - tolerance):
                        if not_road_intersection(p2, row[0], "roads_lyr"):
                            del points[i + 1]
                        else:
                            i += 1
                    else:
                        i += 1
                # Update the geometry based on the points that remains [points]
                if len(points) < count and len(points) >= 2:
                    new_geom = arcpy.Polyline(arcpy.Array(points))
                    row[1] = new_geom
                    num += 1
                    cursor.updateRow(row)

    arcpy.management.CopyFeatures(intermediate_fc, cleaned_roads_fc)

    print(f"Number of roads with deleted points: {num}")
    print("Sharp angles removed!")


@timing_decorator
def delete_intermediate_files() -> None:
    """
    Deletes the intermediate files used during the process.
    """
    for file in files_to_delete:
        arcpy.management.Delete(data_files[file])
