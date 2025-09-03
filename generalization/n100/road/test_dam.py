# Importing packages
from collections import defaultdict
import arcpy
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
    clip_data()


    if has_dam():
        # Move dam away from lakes
        clip_and_erase_pre()
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
    kommune = "Bergen"

    input = [
        [Road_N100.data_preparation___calculated_boarder_hierarchy_2___n100_road.value, None, r"in_memory\road_input"], # Roads
        [input_n100.AnleggsLinje, "objtype = 'Dam'", r"in_memory\dam_input"], # Dam
        [input_n100.AdminFlate, f"NAVN = '{kommune}'", r"in_memory\kommune"], # Area
        [input_n100.ArealdekkeFlate, "OBJTYPE = 'Havflate' OR OBJTYPE = 'Innsjø' OR OBJTYPE = 'InnsjøRegulert'", r"in_memory\water_input"] # Water
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
    buffer_fc = r"in_memory\dam_buffer_35m"
    pre_dissolve = r"in_memory\roads_pre_dissolve"
    outside_fc = r"in_memory\roads_outside"
    inside_fc = r"in_memory\roads_inside"
    inside_wdata_fc = r"in_memory\roads_inside_with_data"

    water_clipped = r"in_memory\water_clipped"
    water_center = r"in_memory\water_center"
    buffer_water = r"in_memory\buffer_water"

    try:
        arcpy.Buffer_analysis(Road_N100.test_dam__relevant_dam__n100_road.value, buffer_fc, "45 Meters", dissolve_option="ALL")
        arcpy.Clip_analysis(Road_N100.test_dam__relevant_roads__n100_road.value, buffer_fc, pre_dissolve)
        arcpy.Erase_analysis(Road_N100.test_dam__relevant_roads__n100_road.value, buffer_fc, outside_fc)
        arcpy.Dissolve_management(pre_dissolve, inside_fc, multi_part="SINGLE_PART", unsplit_lines="UNSPLIT_LINES")

       

        arcpy.Buffer_analysis(Road_N100.test_dam__relevant_dam__n100_road.value, buffer_water, "75 Meters", dissolve_option="ALL")
        arcpy.Clip_analysis(r"in_memory\relevant_waters", buffer_water, water_clipped)
        arcpy.FeatureToPoint_management(water_clipped, water_center, "CENTROID")

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

        def get_endpoints(polyline):
            return (
                arcpy.PointGeometry(polyline.firstPoint, polyline.spatialReference),
                arcpy.PointGeometry(polyline.lastPoint, polyline.spatialReference)
            )

        def reverse_geometry(polyline):
            reversed_parts = []
            for part in polyline:
                reversed_parts.append(arcpy.Array(list(reversed(part))))
            return arcpy.Polyline(arcpy.Array(reversed_parts), polyline.spatialReference)

        def merge_lines(line1, line2, tolerance=5.0):
            l1_start, l1_end = get_endpoints(line1)
            l2_start, l2_end = get_endpoints(line2)

            if l1_end.distanceTo(l2_start) < tolerance:
                merged = arcpy.Array()
                for part in line1:
                    for pt in part:
                        merged.add(pt)
                for part in line2:
                    for pt in part:
                        merged.add(pt)
                return arcpy.Polyline(merged, line1.spatialReference)
            elif l1_end.distanceTo(l2_end) < tolerance:
                line2_rev = reverse_geometry(line2)
                return merge_lines(line1, line2_rev, tolerance)
            elif l1_start.distanceTo(l2_end) < tolerance:
                line1_rev = reverse_geometry(line1)
                return merge_lines(line1_rev, line2, tolerance)
            elif l1_start.distanceTo(l2_start) < tolerance:
                return merge_lines(reverse_geometry(line1), reverse_geometry(line2), tolerance)
            else:
                return None

        def merge_all_lines(fc, tolerance=5.0):
            # Collect all lines and their attributes
            lines = []
            fields = [f.name for f in arcpy.ListFields(fc) if f.type not in ("OID", "Geometry")]
            with arcpy.da.SearchCursor(fc, ["OID@", "SHAPE@"] + fields) as cursor:
                for row in cursor:
                    oid = row[0]
                    geom = row[1]
                    attrs = row[2:]
                    lines.append((oid, geom, attrs))

            merged = []
            used = set()
            for i, (oid1, geom1, attrs1) in enumerate(lines):
                if oid1 in used:
                    continue
                merged_geom = geom1
                merged_attrs = attrs1
                for j, (oid2, geom2, attrs2) in enumerate(lines):
                    if i == j or oid2 in used:
                        continue
                    new_geom = merge_lines(merged_geom, geom2, tolerance)
                    if new_geom:
                        merged_geom = new_geom
                        # Keep attrs from the first line (merged_attrs)
                        used.add(oid2)
                merged.append((merged_geom, merged_attrs))
                used.add(oid1)

            # Delete all rows and insert merged lines
            arcpy.DeleteRows_management(fc)
            with arcpy.da.InsertCursor(fc, ["SHAPE@"] + fields) as cursor:
                for geom, attrs in merged:
                    cursor.insertRow([geom] + list(attrs))
        
        merge_all_lines(inside_wdata_fc, tolerance=5.0)

   
        
    except Exception as e:
        arcpy.AddError(f"clip_and_erase_pre failed: {e}")

@timing_decorator
def edit_geom_pre():
    inside_wdata_fc = r"in_memory\roads_inside_with_data"
    moved_name = "roads_moved"
    roadlines_moved = r"in_memory\roads_moved"

    water_center = r"in_memory\water_center"


    arcpy.CopyFeatures_management(inside_wdata_fc, "in_memory\\roadsbeforebeingmoved")

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
            arcpy.AddWarning(f"Processing OID {oid}: {shape_length}m")
            if not geom or oid not in near_lookup:
                arcpy.AddWarning(f"Skipping OID {oid}: missing geometry or near info")
                insert.insertRow([geom] + list(row[2:]))
                continue

            if shape_length < 30:
            # Do not move short lines, just copy them
                arcpy.AddWarning(f"Skipping OID {oid}: line too short ({shape_length}m)")
                insert.insertRow([geom] + list(row[2:]))
                continue
          

            near_x, near_y = near_lookup[oid]
            shifted = move_line_away(geom, near_x, near_y, distance=35)
            insert.insertRow([shifted] + list(row[2:]))
    
    arcpy.CopyFeatures_management(roadlines_moved, "in_memory\\roadsafterbeingmoved")

def move_geometry_away(geom, near_x, near_y, distance):
    sr = geom.spatialReference
    new_parts = arcpy.Array()

    for part in geom:
        part_arr = arcpy.Array()
        for p in part:
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
    roadlines_moved = r"in_memory\roads_moved"
    outside_fc = r"in_memory\roads_outside"
    final_fc = r"in_memory\roads_shifted"

    # Define snap environment
    snap_env = [[outside_fc, "END", "40 Meters"]]

    # Snap 
    arcpy.Snap_edit(roadlines_moved, snap_env)

    # Merge the two sets
    arcpy.Merge_management([roadlines_moved, outside_fc], final_fc)

    arcpy.CopyFeatures_management(final_fc, "in_memory\\roadsafterbeingsnapped")

@timing_decorator
def create_buffer():
    print("Creating buffers...")
    dam_fc = Road_N100.test_dam__relevant_dam__n100_road.value
    water_fc = r"in_memory\relevant_waters"
    buffers = [
        [dam_fc, r"in_memory\dam_buffer_70m_flat", "70 Meters"],
        [dam_fc, r"in_memory\dam_buffer_70m", "70 Meters"],
        [water_fc, r"in_memory\water_buffer_55m", "55 Meters"]
    ]
    for i in range(len(buffers)):
        type = "FLAT" if i == 0 else "ROUND"
        arcpy.analysis.Buffer(
            in_features=buffers[i][0],
            out_feature_class=buffers[i][1],
            buffer_distance_or_field=buffers[i][2],
            line_end_type=type,
            dissolve_option="NONE",
            method="PLANAR"
        )
    print("Buffers created")

@timing_decorator
def create_buffer_line():
    print("Creates dam buffer as line...")
    buffer = r"in_memory\dam_buffer_70m"
    line = Road_N100.test_dam__dam_buffer_70m_line__n100_road.value
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

def add_road(road_lyr, roads):
    added = False
    with arcpy.da.SearchCursor(road_lyr, ["OID@", "SHAPE@", "objtype"]) as cursor:
        for oid, geom, obj in cursor:
            if oid in roads:
                continue
            start, end = get_endpoints(geom)
            for key in roads:
                s, e = get_endpoints(roads[key][0])
                distances = [
                    start.distanceTo(s), start.distanceTo(e),
                    end.distanceTo(s), end.distanceTo(e)
                ]
                if any(d < 2 for d in distances):
                    roads[oid] = [geom, obj]
                    added = True
                    break
            if added:
                break
    if added:
        return add_road(road_lyr, roads)
    return roads

def find_merge_candidate(short_geom, all_roads, buffer, tolerance=2.0):
    # Finds a road geometry with a common endpoint
    start, end = get_endpoints(short_geom)
    for oid, geom in all_roads:
        if geom.equals(short_geom):
            continue
        s, e = get_endpoints(geom)
        endpoint_pairs = [(start, s), (start, e), (end, s), (end, e)]
        for p1, p2 in endpoint_pairs:
            if p1.distanceTo(p2) < tolerance:
                if buffer.contains(p1) and buffer.contains(p2):
                    return oid, geom
    return None, None

def reverse_geometry(polyline):
    reversed_parts = []
    for part in polyline:
        reversed_parts.append(arcpy.Array(list(reversed(part))))
    return arcpy.Polyline(arcpy.Array(reversed_parts), polyline.spatialReference)

def merge_lines(line1, line2, buffer, tolerance=2.0):
    l1_start, l1_end = get_endpoints(line1)
    l2_start, l2_end = get_endpoints(line2)

    def within_buffer(p1, p2):
        return buffer.contains(p1) and buffer.contains(p2)

    # Find the matching endpoints
    if l1_end.distanceTo(l2_start) < tolerance and within_buffer(l1_end, l2_start):
        # Correct order
        merged = arcpy.Array()
        for part in line1:
            for pt in part:
                merged.add(pt)
        for part in line2:
            for pt in part:
                merged.add(pt)
        return arcpy.Polyline(merged, line1.spatialReference)

    elif l1_end.distanceTo(l2_end) < tolerance and within_buffer(l1_end, l2_end):
        # Reverse line2
        line2_rev = reverse_geometry(line2)
        return merge_lines(line1, line2_rev, buffer, tolerance)

    elif l1_start.distanceTo(l2_end) < tolerance and within_buffer(l1_start, l2_end):
        # Reverse line1
        line1_rev = reverse_geometry(line1)
        return merge_lines(line1_rev, line2, buffer, tolerance)

    elif l1_start.distanceTo(l2_start) < tolerance and within_buffer(l1_start, l2_start):
        # Reverse begge
        return merge_lines(reverse_geometry(line1), reverse_geometry(line2), buffer, tolerance)

    else:
        # No match
        return None

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

##################

@timing_decorator
def connect_roads_with_buffers():
    print("Connects roads with buffers...")

    roads_fc = r"in_memory\roads_shifted"
    intermediate_fc = r"in_memory\roads_intermediate"
    buffer_flat_fc = r"in_memory\dam_buffer_70m_flat"
    buffer_round_fc = r"in_memory\dam_buffer_70m"

    arcpy.management.MultipartToSinglepart(roads_fc, intermediate_fc)

    arcpy.management.MakeFeatureLayer(intermediate_fc, "roads_lyr_flat")
    arcpy.management.MakeFeatureLayer(intermediate_fc, "roads_lyr_round")

    arcpy.management.SelectLayerByLocation(
        # Finds all roads 70m or closer to a dam
        in_layer="roads_lyr_flat",
        overlap_type="WITHIN_A_DISTANCE",
        search_distance="0 Meters",
        select_features=buffer_flat_fc
    )
    arcpy.management.SelectLayerByLocation(
        in_layer="roads_lyr_round",
        overlap_type="WITHIN_A_DISTANCE",
        search_distance="0 Meters",
        select_features=buffer_round_fc
    )

    roads = {}

    with arcpy.da.SearchCursor("roads_lyr_flat", ["OID@", "SHAPE@", "objtype"]) as cursor:
        for oid, geom, obj in cursor:
            if oid not in roads:
                roads[oid] = [geom, obj]
    
    roads = add_road("roads_lyr_round", roads)

    buffer_polygons = [(row[0], row[1]) for row in arcpy.da.SearchCursor(buffer_round_fc, ["OID@", "SHAPE@"])]
    buffer_to_roads = defaultdict(list)

    for key in roads:
        min_dist = float("inf")
        nearest_oid = None
        for oid, buffer_poly in buffer_polygons:
            dist = roads[key][0].distanceTo(buffer_poly)
            if dist < min_dist:
                min_dist = dist
                nearest_oid = oid
        buffer_to_roads[nearest_oid].append([key, roads[key][0], roads[key][1]])
    
    print("Roads connected to buffers.")
    
    return buffer_to_roads

@timing_decorator
def merge_instances(roads):
    print("Merge connected instances of same type...")

    intermediate_fc = r"in_memory\roads_intermediate"
    
    buffer_fc = r"in_memory\dam_buffer_70m"
    buffer_polygons = [(row[0], row[1]) for row in arcpy.da.SearchCursor(buffer_fc, ["OID@", "SHAPE@"])]

    to_delete = set()

    new_roads = defaultdict(list)

    for key in roads:
        buffer = [b[1] for b in buffer_polygons if b[0] == key][0]
        types = {obj for _, _, obj in roads[key]}
        
        arcpy.management.MakeFeatureLayer(
            in_features=intermediate_fc,
            out_layer="roads_lyr"
        )

        for t in types:
            all_roads = [[oid, geom] for oid, geom, obj in roads[key] if obj == t]
            oid_list_str = ",".join(str(road[0]) for road in all_roads)
            sql_query = f"OBJECTID IN ({oid_list_str})"

            arcpy.management.SelectLayerByAttribute(
                in_layer_or_view="roads_lyr",
                selection_type="NEW_SELECTION",
                where_clause=sql_query
            )

            with arcpy.da.UpdateCursor("roads_lyr", ["OID@", "SHAPE@"]) as update_cursor:
                for oid, geom in update_cursor:
                    if geom is None:
                        update_cursor.deleteRow()
                    if oid in to_delete:
                        continue
                    # Finds candidate to merge
                    merge_oid, merge_geom = find_merge_candidate(geom, all_roads, buffer)
                    if merge_geom:
                        # Combine the two geometries
                        new_geom = merge_lines(geom, merge_geom, buffer)
                        if new_geom:
                            update_cursor.updateRow((oid, new_geom))
                            all_roads = [
                                [r_oid, new_geom] if r_oid == oid else (r_oid, r_geom)
                                for r_oid, r_geom in all_roads
                                if r_oid != merge_oid
                            ]
                            new_roads[key].append([oid, new_geom])
                            to_delete.add(merge_oid)
                    else:
                        new_roads[key].append([oid, geom])
            
            # Deletes the roads that have been merged into others
            with arcpy.da.UpdateCursor("roads_lyr", ["OID@"]) as delete_cursor:
                for row in delete_cursor:
                    if row[0] in to_delete:
                        delete_cursor.deleteRow()
    
    print("Instances merged!")

    return new_roads

@timing_decorator
def snap_roads(roads):
    print("Snap roads to buffer...")
    
    intermediate_fc = r"in_memory\roads_intermediate"
    buffer_fc = r"in_memory\dam_buffer_70m"
    buffer_lines_fc = Road_N100.test_dam__dam_buffer_70m_line__n100_road.value
    water_buffer_fc = r"in_memory\water_buffer_55m"
    buffer_water_dam_fc = r"in_memory\dam_buffer_without_water"

    arcpy.analysis.Erase(
        # The roads should be snapped to buffer lines
        # at least 55m from water
        in_features=buffer_lines_fc,
        erase_features=water_buffer_fc,
        out_feature_class=buffer_water_dam_fc
    )
    
    buffer_polygons = [(row[0], row[1]) for row in arcpy.da.SearchCursor(buffer_fc, ["OID@", "SHAPE@"])]
    buffer_lines = [(row[0], row[1]) for row in arcpy.da.SearchCursor(buffer_water_dam_fc, ["OID@", "SHAPE@"])]

    oids = ",".join(str(oid) for key in roads.keys() for oid, _ in roads[key])
    sql = f"OBJECTID IN ({oids})"

    arcpy.management.MakeFeatureLayer(intermediate_fc, "roads_lyr")
    
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view="roads_lyr",
        selection_type="NEW_SELECTION",
        where_clause=sql
    )

    for buf_oid, buffer_poly in buffer_polygons:
        # For all buffer polygons, find the corresponding buffer line
        buffer_line = None
        for _, line in buffer_lines:
            dist = line.distanceTo(buffer_poly)
            if dist < 5:
                # It should only be one line per polygon
                buffer_line = line
                break
        if buffer_line is None:
            continue
        
        # Fetch all roads associated with this buffer polygon
        relevant_roads = roads.get(buf_oid, [])
        if not relevant_roads:
            # If no roads, skip
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
            ref_pt = cluster[0][0] # Fetches the first point
            result = buffer_line.queryPointAndDistance(ref_pt)
            snap_pt = result[0]  # Closest point on buffer line
            for _, idx in cluster: # ... and adjust the rest of the points in the cluster to the ref_pt
                snap_points[idx] = snap_pt

        with arcpy.da.UpdateCursor("roads_lyr", ["OID@", "SHAPE@"]) as update_cursor:
            # Update each road
            for row in update_cursor:
                oid, geom = row
                if geom is None:
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

    print("Roads snapped to buffers!")

##################
# Help functions
##################

def calculate_angle(p1, p2, p3):
    # Vektorer fra p2 til p1 og p2 til p3
    v1 = (p1.X - p2.X, p1.Y - p2.Y)
    v2 = (p3.X - p2.X, p3.Y - p2.Y)

    # Skalarprodukt og lengder
    dot = v1[0]*v2[0] + v1[1]*v2[1]
    len1 = math.hypot(*v1)
    len2 = math.hypot(*v2)

    if len1 == 0 or len2 == 0:
        return 180  # Udefinert vinkel, behandler som rett

    # Beregn vinkel i grader
    angle_rad = math.acos(dot / (len1 * len2))
    angle_deg = math.degrees(angle_rad)
    
    return angle_deg

def not_road_intersection(point, road_oid, roads):
    point_geom = arcpy.PointGeometry(point)
    tolerance = 5
    with arcpy.da.SearchCursor(roads, ["OID@", "SHAPE@"]) as search_cursor:
        for oid, shape in search_cursor:
            if oid != road_oid:
                if shape.distanceTo(point_geom) <= tolerance:
                    return False
    return True

##################

def remove_sharp_angles(roads):
    print("Removes sharp angles...")

    intermediate_fc = r"in_memory\roads_intermediate"
    cleaned_roads_fc = Road_N100.test_dam__cleaned_roads__n100_road.value
    
    oids = ",".join(str(oid) for key in roads.keys() for oid, _ in roads[key])
    sql = f"OBJECTID IN ({oids})"

    arcpy.management.MakeFeatureLayer(intermediate_fc, "roads_lyr")
    
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view="roads_lyr",
        selection_type="NEW_SELECTION",
        where_clause=sql
    )

    with arcpy.da.UpdateCursor("roads_lyr", ["OID@", "SHAPE@"]) as cursor:
        for row in cursor:
            points = []
            for part in row[1]:
                for p in part:
                    points.append(p)
            
            i = 0
            tolerance = 70
            filtered_points = points.copy()

            while i + 2 < len(filtered_points):
                p1, p2, p3 = filtered_points[i:i+3]
                # Beregne vinkelen mellom de tre punktene
                # Altså vinkelen i det midterste punktet
                angle = calculate_angle(p1, p2, p3)
                # Hvis vinkelen er spissere enn en tolleranse - slett punktet
                if angle < tolerance or angle > (360 - tolerance):
                    if not_road_intersection(p2, row[0], "roads_lyr"):
                        del filtered_points[i+1]
                else:
                    i += 1
            # Oppdater geometrien basert på punktene som er igjen i [points]
            if len(filtered_points) < len(points) and len(filtered_points) >= 2:
                new_geom = arcpy.Polyline(arcpy.Array(filtered_points))
                row[1] = new_geom
                print("Fjernet")
                cursor.updateRow(row)

    arcpy.management.CopyFeatures(intermediate_fc, cleaned_roads_fc)

    print("Sharp angles removed!")

if __name__=="__main__":
    main()
