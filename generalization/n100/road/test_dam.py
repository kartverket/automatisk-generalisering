# Importing packages
from collections import defaultdict
import arcpy
import numpy as np
import math

arcpy.env.overwriteOutput = True

# Importing custom input files modules
from input_data import input_n100

# Importing custom modules
from file_manager.n100.file_manager_roads import Road_N100
from env_setup import environment_setup
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools import custom_arcpy

@timing_decorator
def main():
    
    # Setup
    environment_setup.main()
    arcpy.Delete_management("in_memory")

    # Data preparation
    fetch_data()
    #clip_data()


    if has_dam():
        # Move dam away from lakes
        clip_and_erase_pre()
        snap_merge_before_moving()
        edit_geom_pre()
        snap_and_merge_pre()
      
        # Data preparation
        create_buffer()
        create_buffer_line()
        
        # Snap roads to buffer
        roads = connect_roads_with_buffers()
        roads = merge_instances(roads)
        snap_roads(roads)
        remove_sharp_angles(roads)
    else:
        print("No dam found in the selected municipality. Exiting script.")

@timing_decorator
def fetch_data():
    print("Fetching data...")

    ##################################
    # Choose municipality to work on #
    ##################################
    kommune = "Notodden"

    input = [
        [r"C:\GIS_Files\ag_inputs\road.gdb\VegSti", None, Road_N100.test_dam__relevant_roads__n100_road.value], # Roads
        [input_n100.AnleggsLinje, "objtype = 'Dam'", Road_N100.test_dam__relevant_dam__n100_road.value], # Dam
        [input_n100.AdminFlate, f"NAVN = '{kommune}'", r"in_memory\kommune"], # Area
        [input_n100.ArealdekkeFlate, "OBJTYPE = 'Havflate' OR OBJTYPE = 'Innsjø' OR OBJTYPE = 'InnsjøRegulert'", r"in_memory\relevant_waters"] # Water
    ]
    for data in input:
        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=data[0],
            expression=data[1],
            output_name=data[2],
            selection_type=custom_arcpy.SelectionType.NEW_SELECTION
        )
    print("Data fetched!")

@timing_decorator
def clip_data():
    print("Clipping data to municipality...")
    kommune = r"in_memory\kommune"
    files = [
        [r"in_memory\road_input", Road_N100.test_dam__relevant_roads__n100_road.value], # Roads
        [r"in_memory\dam_input", Road_N100.test_dam__relevant_dam__n100_road.value], # Dam
        [r"in_memory\water_input", r"in_memory\relevant_waters"] # Water
    ]
    for file in files:
        arcpy.analysis.Clip(
            in_features=file[0],
            clip_features=kommune,
            out_feature_class=file[1]
        )
    print("Data clipped!")

@timing_decorator
def has_dam():
    dam_fc = Road_N100.test_dam__relevant_dam__n100_road.value
    count = int(arcpy.management.GetCount(dam_fc).getOutput(0))
    return count > 0

@timing_decorator
def clip_and_erase_pre():
    print("Clipping and erasing roads near dam...")
    buffer_fc = r"in_memory\\dam_buffer_35m"
    pre_dissolve = r"in_memory\roads_pre_dissolve"
    outside_fc = r"in_memory\roads_outside"
    inside_fc = r"in_memory\roads_inside"
    inside_wdata_fc = r"in_memory\roads_inside_with_data"

    water_clipped = r"in_memory\water_clipped"
    water_center = r"in_memory\water_center"
    buffer_water = r"in_memory\buffer_water"
    water_single = r"in_memory\water_singleparts"

    
    arcpy.Buffer_analysis(Road_N100.test_dam__relevant_dam__n100_road.value, buffer_fc, "55 Meters", dissolve_option="NONE")
    # 1. Build a layer of only the 'L' roads
    fld = arcpy.AddFieldDelimiters(Road_N100.test_dam__relevant_roads__n100_road.value, "medium")
    arcpy.MakeFeatureLayer_management(
        Road_N100.test_dam__relevant_roads__n100_road.value,
        "roads_L_lyr",
        where_clause=f"{fld} = 'L'"
    )

    # 2. Build a layer of buffers
    arcpy.MakeFeatureLayer_management(buffer_fc, "buffer_lyr")

    # 3. Select buffers intersecting the filtered roads
    arcpy.SelectLayerByLocation_management(
        "buffer_lyr",
        "INTERSECT",
        "roads_L_lyr"
    )

    arcpy.DeleteFeatures_management("buffer_lyr")




    arcpy.Clip_analysis(Road_N100.test_dam__relevant_roads__n100_road.value, buffer_fc, pre_dissolve)
    arcpy.Erase_analysis(Road_N100.test_dam__relevant_roads__n100_road.value, buffer_fc, outside_fc)
    arcpy.Dissolve_management(pre_dissolve, inside_fc, multi_part="SINGLE_PART", unsplit_lines="UNSPLIT_LINES")

    

    arcpy.Buffer_analysis(Road_N100.test_dam__relevant_dam__n100_road.value, buffer_water, "75 Meters", dissolve_option="NONE")
    arcpy.Clip_analysis(r"in_memory\relevant_waters", buffer_water, water_clipped)
    arcpy.MultipartToSinglepart_management(water_clipped, water_single)
    arcpy.FeatureToPoint_management(water_single, water_center, "CENTROID")

    fm = arcpy.FieldMappings()
    for fld in arcpy.ListFields(pre_dissolve):
        if not fld.required:
            fmap = arcpy.FieldMap()
            fmap.addInputField(pre_dissolve, fld.name)
            fmap.mergeRule = "First"
            fm.addFieldMap(fmap)

    arcpy.SpatialJoin_analysis(
        target_features=inside_fc,
        join_features=pre_dissolve,
        out_feature_class=inside_wdata_fc,
        join_operation="JOIN_ONE_TO_ONE",
        join_type="KEEP_COMMON",
        match_option="INTERSECT",
        field_mapping=fm
    )

    arcpy.DeleteField_management(inside_wdata_fc, drop_field=["Join_Count", "TARGET_FID"])

@timing_decorator
def snap_merge_before_moving():
    inside_wdata_fc = r"in_memory\roads_inside_with_data"

    tolerance = 40.0
    # Precompute squared tolerance for faster distance checks
    tol2 = tolerance * tolerance

    # Helper: squared distance between two arcpy.Points
    def _sq_dist(p1, p2):
        dx = p1.X - p2.X
        dy = p1.Y - p2.Y
        return dx*dx + dy*dy

    # Store seen endpoint‐pairs as a list of tuples: ((x1,y1),(x2,y2))
    seen = []

    # Open an update cursor to delete rows
    with arcpy.da.UpdateCursor(inside_wdata_fc, ["OID@", "SHAPE@"]) as cursor:
        for oid, geom in cursor:
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
                d2 = _sq_dist(p_end,   arcpy.Point(ex, ey))
                d3 = _sq_dist(p_start, arcpy.Point(ex, ey))
                d4 = _sq_dist(p_end,   arcpy.Point(sx, sy))
                
                if (d1 <= tol2 and d2 <= tol2) or (d3 <= tol2 and d4 <= tol2):
                    cursor.deleteRow()
                    is_duplicate = True
                    break

            if not is_duplicate:
                # Record this endpoint pair
                seen.append(
                    ((p_start.X, p_start.Y), (p_end.X, p_end.Y))
                )


    backup = build_backup(inside_wdata_fc)
    snap_by_objtype(inside_wdata_fc)
    arcpy.Snap_edit(inside_wdata_fc, [[inside_wdata_fc, "END", "40 Meters"]])
    restore_deleted_lines(inside_wdata_fc, backup)

    merge_all_lines(inside_wdata_fc, tolerance=5.0)

def build_backup(layer):
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
    
        # Delete features with None geometry after snapping
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

def merge_all_lines(fc, tolerance=5.0):
    # 1. Read all lines
    lines = []
    fields = [f.name for f in arcpy.ListFields(fc)
            if f.type not in ("OID", "Geometry")]
    with arcpy.da.SearchCursor(fc, ["OID@", "SHAPE@"] + fields) as cur:
        for oid, geom, *attrs in cur:
            lines.append({"oid": oid, "shape": geom, "attrs": attrs})

    # 2. Build adjacency based on endpoint proximity
    adj = defaultdict(set)
    for i, ln1 in enumerate(lines):
        eps1 = get_endpoints_cords(ln1["shape"])
        for j, ln2 in enumerate(lines[i+1:], start=i+1):
            eps2 = get_endpoints_cords(ln2["shape"])
            if any(within_tol(p1, p2, tolerance) for p1 in eps1 for p2 in eps2):
                adj[i].add(j)
                adj[j].add(i)

    # 3. Find connected components
    visited = set()
    clusters = []
    for i in range(len(lines)):
        if i in visited:
            continue
        stack = [i]
        comp = []
        while stack:
            curr = stack.pop()
            if curr in visited:
                continue
            visited.add(curr)
            comp.append(curr)
            stack.extend(adj[curr] - visited)
        clusters.append(comp)

    # 4. Union geometries in each cluster
    merged = []
    for comp in clusters:
        shapes = [lines[i]["shape"] for i in comp]
        # start with the first shape, then union the rest
        cumul = shapes[0]
        for s in shapes[1:]:
            cumul = cumul.union(s)
        # pick attributes of the first feature in cluster
        merged.append((cumul, lines[comp[0]]["attrs"]))

    # 5. Overwrite FC with merged results
    arcpy.DeleteRows_management(fc)
    out_fields = ["SHAPE@"] + fields
    with arcpy.da.InsertCursor(fc, out_fields) as cur:
        for geom, attrs in merged:
            cur.insertRow([geom] + attrs)

    print(f"Merged {len(lines)} input lines into {len(merged)} features.")

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
    # Get all unique objtypes
    objtypes = set()
    with arcpy.da.SearchCursor(layer, ["objtype"]) as cursor:
        for row in cursor:
            objtypes.add(row[0])

    for obj in objtypes:
        # Make a feature layer for this objtype
        layer_name = f"roads_moved_{obj}"
        arcpy.management.MakeFeatureLayer(
            layer,
            layer_name,
            f"objtype = '{obj}'"
        )
        # Snap only within this objtype group
        snap_env = [[layer_name, "END", "40 Meters"]]
        arcpy.Snap_edit(layer_name, snap_env)
        
        arcpy.Delete_management(layer_name) 

@timing_decorator
def edit_geom_pre():
    print("Moving roads away from water...")
    inside_wdata_fc = r"in_memory\roads_inside_with_data"
    moved_name = "roads_moved"
    roadlines_moved = r"in_memory\roads_moved"

    water_center = r"in_memory\water_center"

    inside_sr = arcpy.Describe(inside_wdata_fc).spatialReference
    temp_fc = inside_wdata_fc + "_temp"

    # Copy features for editing
    arcpy.CopyFeatures_management(inside_wdata_fc, temp_fc)

    # Create output feature class
    arcpy.CreateFeatureclass_management(
        out_path="in_memory",
        out_name=moved_name,
        geometry_type="POLYLINE",
        template=temp_fc,
        spatial_reference=inside_sr
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
        closest_count=1
    )

    # Build a lookup of NEAR_X, NEAR_Y for each road feature
    near_lookup = {}
    with arcpy.da.SearchCursor(near_table, ["IN_FID", "NEAR_X", "NEAR_Y"]) as cursor:
        for fid, nx, ny in cursor:
            near_lookup[fid] = (nx, ny)

    fields = ["OID@", "SHAPE@"] + [
        f.name for f in arcpy.ListFields(temp_fc)
        if f.type not in ("OID", "Geometry")
    ]

    with arcpy.da.SearchCursor(temp_fc, fields) as search, \
         arcpy.da.InsertCursor(roadlines_moved, fields[1:]) as insert:

        for row in search:
            oid = row[0]
            geom = row[1]
            shape_length = geom.length
            if not geom or oid not in near_lookup:
                insert.insertRow([geom] + list(row[2:]))
                #print(oid, "not moved")
                continue

            if shape_length < 35:
            # Do not move short lines, just copy them
                insert.insertRow([geom] + list(row[2:]))
                continue

            near_x, near_y = near_lookup[oid]
            shifted = move_line_away(geom, near_x, near_y, distance=35)
            insert.insertRow([shifted] + list(row[2:]))

def move_line_away(geom, near_x, near_y, distance):
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

@timing_decorator
def snap_and_merge_pre():
    print("Snapping and merging roads after moving...")
    roadlines_moved = r"in_memory\roads_moved"
    outside_fc = r"in_memory\roads_outside"
    final_fc = r"in_memory\roads_shifted"

    # Define snap environment
    snap_env = [[outside_fc, "END", "60 Meters"]]

    # Snap 
    arcpy.Snap_edit(roadlines_moved, snap_env)

    snap_env2 = [[roadlines_moved, "END", "60 Meters"]]

    arcpy.Buffer_analysis(Road_N100.test_dam__relevant_dam__n100_road.value, r"in_memory\dam_buffer_150m", "150 Meters")
    arcpy.MakeFeatureLayer_management(outside_fc, "outside_lyr")
    arcpy.SelectLayerByLocation_management(
        in_layer="outside_lyr",
        overlap_type="INTERSECT",
        select_features=r"in_memory\dam_buffer_150m"
    )
    
    arcpy.Snap_edit("outside_lyr", snap_env2)
    

    # Merge the two sets
    arcpy.Merge_management([roadlines_moved, outside_fc], final_fc)
    #arcpy.CopyFeatures_management(final_fc, "C:\\temp\\Roads.gdb\\roadsafterbeingsnapped")

@timing_decorator
def create_buffer():
    print("Creating buffers...")
    dam_fc = Road_N100.test_dam__relevant_dam__n100_road.value
    water_fc = r"in_memory\relevant_waters"

    arcpy.management.MakeFeatureLayer(water_fc, "water_lyr")
    arcpy.management.SelectLayerByLocation(
        in_layer="water_lyr",
        select_features=dam_fc,
        overlap_type="WITHIN_A_DISTANCE",
        search_distance="100 Meters",
        selection_type="NEW_SELECTION"
    )

    buffers = [
        [dam_fc, r"in_memory\dam_buffer_60m_flat", "60 Meters"],
        [dam_fc, r"in_memory\dam_buffer_60m", "60 Meters"],
        ["water_lyr", r"in_memory\water_buffer_55m", "55 Meters"]
    ]
    for i in range(len(buffers)):
        type = "FLAT" if i == 0 else "ROUND"
        arcpy.analysis.Buffer(
            in_features=buffers[i][0],
            out_feature_class=buffers[i][1] + "_buffer",
            buffer_distance_or_field=buffers[i][2],
            line_end_type=type,
            dissolve_option="NONE",
            method="PLANAR"
        )
        arcpy.management.Dissolve(
            in_features=buffers[i][1] + "_buffer",
            out_feature_class=buffers[i][1],
            dissolve_field=[],
            multi_part="SINGLE_PART"
        )
    print("Buffers created")

@timing_decorator
def create_buffer_line():
    print("Creates dam buffer as line...")
    buffer = r"in_memory\dam_buffer_60m"
    line = Road_N100.test_dam__dam_buffer_60m_line__n100_road.value
    arcpy.management.PolygonToLine(
        in_features=buffer,
        out_feature_class=line
    )
    print("Dam buffer as line created")

##################
# Help functions
##################

def get_endpoints(polyline):
        # Returns the start and end points of a polyline
        return (
            arcpy.PointGeometry(polyline.firstPoint, polyline.spatialReference),
            arcpy.PointGeometry(polyline.lastPoint, polyline.spatialReference)
        )

def add_road(road_lyr, roads, tolerance=2.0):
    # Build endpoint lookup for existing roads
    endpoint_lookup = defaultdict(list)
    for oid, (geom, _, _) in roads.items():
        start, end = get_endpoints(geom)
        # Use rounded coordinates for fast lookup
        for pt in [start, end]:
            key = (round(pt.centroid.X, 2), round(pt.centroid.Y, 2))
            endpoint_lookup[key].append(oid)

    # Add new roads if they share endpoints with existing roads
    with arcpy.da.SearchCursor(road_lyr, ["OID@", "SHAPE@", "objtype", "vegkategori"]) as cursor:
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
                                new_key = (round(new_pt.centroid.X, 2), round(new_pt.centroid.Y, 2))
                                endpoint_lookup[new_key].append(oid)
                            added = True
                            break
                    if added:
                        break
                if added:
                    break

    return roads

def find_merge_candidate(short_geom, all_roads, buffer, tolerance=2.0):
    # Finds a road geometry with a common endpoint
    start, end = get_endpoints(short_geom)
    for oid, geom in all_roads:
        s, e = get_endpoints(geom)
        endpoint_pairs = [(start, s), (start, e), (end, s), (end, e)]
        for p1, p2 in endpoint_pairs:
            if p1.distanceTo(p2) < tolerance:
                if buffer.contains(p1) and buffer.contains(p2):
                    return oid
    return None

def reverse_geometry(polyline):
    reversed_parts = []
    for part in polyline:
        reversed_parts.append(arcpy.Array(list(reversed(part))))
    return arcpy.Polyline(arcpy.Array(reversed_parts), polyline.spatialReference)

def merge_lines(line1, line2, tolerance=2.0):
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

def create_single_buffer_line(buffer, water):
    line = r"in_memory\dam_line_single"
    final = r"in_memory\dam_line_final"
    arcpy.management.PolygonToLine(buffer, line)
    arcpy.analysis.Erase(line, water, final)

def cluster_points(points, threshold=1.0):
    # Clusters points that are within the threshold
    # distance of each other
    clusters = []
    for pt, idx in points:
        found = False
        for cluster in clusters:
            if any(pt.distanceTo(other[0]) < threshold for other in cluster):
                # The points are close enough to be in the same cluster
                # With other words: snap them to the same coordinate
                cluster.append((pt, idx))
                found = True
                break
        if not found:
            clusters.append([(pt, idx)])
    return clusters

def calculate_centroid(cluster):
    ref = cluster[0][0].spatialReference
    x_sum = sum(pt.firstPoint.X for pt, _ in cluster)
    y_sum = sum(pt.firstPoint.Y for pt, _ in cluster)
    count = len(cluster)
    return arcpy.PointGeometry(arcpy.Point(x_sum / count, y_sum / count), ref)

##################

@timing_decorator
def connect_roads_with_buffers():
    print("Connects roads with buffers...")

    roads_fc = r"in_memory\roads_shifted"
    intermediate_fc = r"in_memory\roads_intermediate"
    buffer_flat_fc = r"in_memory\dam_buffer_60m_flat"
    buffer_round_fc = r"in_memory\dam_buffer_60m"

    arcpy.management.MakeFeatureLayer(roads_fc, "roads_lyr_round")
    arcpy.management.SelectLayerByLocation(
        in_layer="roads_lyr_round",
        overlap_type="WITHIN_A_DISTANCE",
        search_distance="0 Meters",
        select_features=buffer_round_fc
    )
    arcpy.management.MultipartToSinglepart("roads_lyr_round", intermediate_fc)
    arcpy.management.SelectLayerByLocation(
        in_layer="roads_lyr_round",
        selection_type="SWITCH_SELECTION"
    )
    arcpy.management.Append(
        inputs="roads_lyr_round",  # Only selected features will be appended
        target=intermediate_fc,
        schema_type="NO_TEST"
    )

    arcpy.management.MakeFeatureLayer(intermediate_fc, "roads_lyr_flat")
    arcpy.management.MakeFeatureLayer(intermediate_fc, "roads_lyr_round_2")

    arcpy.management.SelectLayerByLocation(
        # Finds all roads 60m or closer to a dam
        in_layer="roads_lyr_flat",
        selection_type="NEW_SELECTION",
        overlap_type="WITHIN_A_DISTANCE",
        search_distance="0 Meters",
        select_features=buffer_flat_fc
    )
    arcpy.management.SelectLayerByLocation(
        in_layer="roads_lyr_round_2",
        selection_type="NEW_SELECTION",
        overlap_type="WITHIN_A_DISTANCE",
        search_distance="0 Meters",
        select_features=buffer_round_fc
    )

    roads = {}
    with arcpy.da.SearchCursor("roads_lyr_flat", ["OID@", "SHAPE@", "objtype", "vegkategori"]) as cursor:
        for oid, geom, obj, category in cursor:
            if oid not in roads:
                roads[oid] = [geom, obj, category]

    roads = add_road("roads_lyr_round_2", roads)

    buffer_polygons = [(row[0], row[1]) for row in arcpy.da.SearchCursor(buffer_round_fc, ["OID@", "SHAPE@"])]
    buffer_to_roads = defaultdict(list)
    print("Finding nearest buffer for each road...")
    for key in roads:
        for oid, buffer_poly in buffer_polygons:
            dist = roads[key][0].distanceTo(buffer_poly)
            if dist < 1:
                buffer_to_roads[oid].append([key, roads[key][0], roads[key][1], roads[key][2]])
    
    print("Roads connected to buffers.")

    return buffer_to_roads

@timing_decorator
def merge_instances(roads):
    print("Merge connected instances of same type...")

    intermediate_fc = r"in_memory\roads_intermediate"

    buffer_fc = r"in_memory\dam_buffer_60m"
    buffer_polygons = {row[0]: row[1] for row in arcpy.da.SearchCursor(buffer_fc, ["OID@", "SHAPE@"])}

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
        relevant_roads = [oid for oid, ids in roads_to_buffers.items() if buffer_id in ids]
        relevant_roads = [[oid, roads_by_oid[oid][0], roads_by_oid[oid][1], roads_by_oid[oid][2]] for oid in relevant_roads]
        types = {objtype for _, _, objtype, _ in relevant_roads}
        categories = {category for _, _, _, category in relevant_roads}

        # Checks if there are bridges in the buffer
        # If so, skip this one
        sql = f"OBJECTID IN ({','.join(str(oid) for oid, _, _, _ in relevant_roads)})"
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view="roads_lyr",
            selection_type="NEW_SELECTION",
            where_clause=sql
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
                roads_to_edit = [[oid, geom] for oid, geom, objt, category in relevant_roads if objt == t and category == c]
                
                if not roads_to_edit:
                    continue
                
                sql = f"OBJECTID IN ({','.join(str(oid) for oid, _ in roads_to_edit)})"

                arcpy.management.SelectLayerByAttribute(
                    in_layer_or_view="roads_lyr",
                    selection_type="NEW_SELECTION",
                    where_clause=sql
                )

                with arcpy.da.UpdateCursor("roads_lyr", ["OID@", "SHAPE@"]) as update_cursor:
                    for oid, geom in update_cursor:
                        if oid in to_delete:
                            continue
                        if geom is None:
                            update_cursor.deleteRow()
                            del roads_by_oid[oid]
                            del roads_to_buffers[oid]
                            continue
                        # Finds candidate to merge
                        merge_oid = find_merge_candidate(geom, [r for r in roads_to_edit if r[0] != oid and r[0] not in to_delete], buffer_geom)
                        if merge_oid is None or merge_oid == oid or merge_oid in to_delete:
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
def snap_roads(roads):
    print("Snap roads to buffer...")
    
    intermediate_fc = r"in_memory\roads_intermediate"
    buffer_fc = r"in_memory\dam_buffer_60m"
    water_buffer_fc = r"in_memory\water_buffer_55m"

    buffer_polygons = [(row[0], row[1]) for row in arcpy.da.SearchCursor(buffer_fc, ["OID@", "SHAPE@"])]
    
    arcpy.management.MakeFeatureLayer(intermediate_fc, "roads_lyr")

    for buf_oid, buffer_poly in buffer_polygons:
        # For all buffer polygons, find the corresponding buffer line
        line = r"in_memory\dam_line_final"
        create_single_buffer_line(buffer_poly, water_buffer_fc)
        buffer_lines = [row[0] for row in arcpy.da.SearchCursor(line, ["SHAPE@"])]
        if not buffer_lines:
            continue
        buffer_line = buffer_lines[0]
        
        # Fetch all roads associated with this buffer polygon
        road_list = roads.get(buf_oid, [])
        if not road_list:
            # If no roads, skip
            continue
        oids = ",".join(str(oid) for oid in road_list)
        sql = f"OBJECTID IN ({oids})"
        arcpy.management.SelectLayerByAttribute("roads_lyr", "CLEAR_SELECTION")
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view="roads_lyr",
            selection_type="NEW_SELECTION",
            where_clause=sql
        )
        relevant_roads = []
        bridge = False
        with arcpy.da.SearchCursor("roads_lyr", ["OID@", "SHAPE@", "medium"]) as cursor:
            for oid, geom, medium in cursor:
                if geom == None:
                    continue
                if medium == "L":
                    bridge = True
                    break
                relevant_roads.append((oid, geom))
        
        # If the road(s) inside the buffer is a bridge
        # e.i. medium = "L", do not snap it
        if bridge:
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
                        points_to_cluster.append((pt_geom, (road_oid, part_idx, pt_idx)))

        # Cluster points that are close to each other
        clusters = cluster_points(points_to_cluster, threshold=1.0)

        # Snap points to the buffer line
        snap_points = {}
        for cluster in clusters:
            ref_pt = calculate_centroid(cluster) # cluster[0][0] # Fetches the first point
            result = buffer_line.queryPointAndDistance(ref_pt)
            snap_pt = result[0]  # Closest point on buffer line
            for _, idx in cluster: # ... and adjust the rest of the points in the cluster to the ref_pt
                snap_points[idx] = snap_pt

        with arcpy.da.UpdateCursor("roads_lyr", ["OID@", "SHAPE@"]) as update_cursor:
            # Update each road
            for row in update_cursor:
                oid, geom = row
                if geom is None:
                    update_cursor.deleteRow()
                    continue
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
                    new_line = arcpy.Polyline(arcpy.Array(new_parts), geom.spatialReference)
                    geom = new_line
                    update_cursor.updateRow((oid, geom))
    
    arcpy.management.Integrate(
        in_features="roads_lyr",
        cluster_tolerance="5 Meters"
    )
    
    cleaned_roads_fc = Road_N100.test_dam__cleaned_roads__n100_road.value
    arcpy.management.CopyFeatures(intermediate_fc, cleaned_roads_fc)

    print("Roads snapped to buffers!")

##################
# Help functions
##################

def calculate_angle(p1, p2, p3):
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

def not_road_intersection(point, road_oid, roads):
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

@timing_decorator
def remove_sharp_angles(roads):
    print("Removes sharp angles...")

    intermediate_fc = r"in_memory\roads_intermediate"
    cleaned_roads_fc = Road_N100.test_dam__cleaned_roads__n100_road.value
    
    oids = ",".join(str(oid) for key in roads.keys() for oid in roads[key])
    sql = f"OBJECTID IN ({oids})"

    arcpy.management.MakeFeatureLayer(intermediate_fc, "roads_lyr")
    
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view="roads_lyr",
        selection_type="NEW_SELECTION",
        where_clause=sql
    )

    num = 0

    with arcpy.da.UpdateCursor("roads_lyr", ["OID@", "SHAPE@"]) as cursor:
        for row in cursor:
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
                p1, p2, p3 = points[i:i+3]
                # Calculates the angle between the three points
                # With other words: the angle in the centre point
                angle = calculate_angle(p1, p2, p3)
                # If the angle is sharper than the tolerance - delete the point
                if angle < tolerance or angle > (360 - tolerance):
                    if not_road_intersection(p2, row[0], "roads_lyr"):
                        del points[i+1]
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

if __name__=="__main__":
    main()
