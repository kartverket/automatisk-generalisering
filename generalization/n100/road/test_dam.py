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
        snap_roads_to_buffer()
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
    print("Data fetched")

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
    print("Data clipped")

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

    try:
        arcpy.Buffer_analysis(Road_N100.test_dam__relevant_dam__n100_road.value, buffer_fc, "35 Meters", dissolve_option="ALL")
        arcpy.Clip_analysis(Road_N100.test_dam__relevant_roads__n100_road.value, buffer_fc, pre_dissolve)
        arcpy.Erase_analysis(Road_N100.test_dam__relevant_roads__n100_road.value, buffer_fc, outside_fc)
        arcpy.Dissolve_management(pre_dissolve, inside_fc, multi_part="SINGLE_PART", unsplit_lines="UNSPLIT_LINES")

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
    except Exception as e:
        arcpy.AddError(f"clip_and_erase_pre failed: {e}")

@timing_decorator
def edit_geom_pre():
    inside_wdata_fc = r"in_memory\roads_inside_with_data"
    moved_name = "roads_moved"
    roadlines_moved = r"in_memory\roads_moved"

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
        near_features="in_memory\\relevant_waters",
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
            if not geom or oid not in near_lookup:
                arcpy.AddWarning(f"Skipping OID {oid}: missing geometry or near info")
                continue
          

            near_x, near_y = near_lookup[oid]
            shifted = move_geometry_away(geom, near_x, near_y, distance=35)
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
        #[dam_fc, r"in_memory\dam_buffer_60m_flat", "60 Meters"],
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

@timing_decorator
def snap_roads_to_buffer():
    print("Snap roads to buffer...")

    roads_fc = r"in_memory\roads_shifted"
    intermediate_fc = r"in_memory\roads_intermediate"
    cleaned_roads_fc = Road_N100.test_dam__cleaned_roads__n100_road.value
    buffer_flat_fc = r"in_memory\dam_buffer_70m_flat"
    buffer_fc = r"in_memory\dam_buffer_70m"
    buffer_lines_fc = Road_N100.test_dam__dam_buffer_70m_line__n100_road.value
    water_buffer_fc = r"in_memory\water_buffer_55m"
    buffer_water_dam_fc = r"in_memory\dam_buffer_without_water"

    arcpy.management.CopyFeatures(roads_fc, intermediate_fc)

    arcpy.management.MultipartToSinglepart(intermediate_fc, cleaned_roads_fc)

    arcpy.management.MakeFeatureLayer(
        in_features=cleaned_roads_fc,
        out_layer="roads_lyr_flat"
    )
    arcpy.management.MakeFeatureLayer(
        in_features=cleaned_roads_fc,
        out_layer="roads_lyr_round"
    )
    arcpy.management.SelectLayerByLocation(
        # Finds all roads 70m or closer to a dam
        in_layer="roads_lyr_flat",
        overlap_type="INTERSECT",
        select_features=buffer_flat_fc
    )
    arcpy.management.SelectLayerByLocation(
        in_layer="roads_lyr_round",
        overlap_type="INTERSECT",
        search_distance="5 Meters",
        select_features=buffer_fc
    )
    arcpy.analysis.Erase(
        # The roads should be snapped to buffer lines
        # at least 55m from water
        in_features=buffer_lines_fc,
        erase_features=water_buffer_fc,
        out_feature_class=buffer_water_dam_fc
    )

    buffer_polygons = [(row[1], row[0]) for row in arcpy.da.SearchCursor(buffer_fc, ["SHAPE@", "OID@"])]
    buffer_lines = [(row[1], row[0]) for row in arcpy.da.SearchCursor(buffer_water_dam_fc, ["SHAPE@", "OID@"])]

    def get_endpoints(polyline):
        # Returns the start and end points of a polyline
        return (
            arcpy.PointGeometry(polyline.firstPoint, polyline.spatialReference),
            arcpy.PointGeometry(polyline.lastPoint, polyline.spatialReference)
        )
    
    def find_merge_candidate(short_geom, all_roads, tolerance=2.0):
        # Finds a road geometry with a common endpoint
        short_start, short_end = get_endpoints(short_geom)
        for oid, geom in all_roads:
            if geom.equals(short_geom):
                continue
            start, end = get_endpoints(geom)
            if short_start.distanceTo(start) < tolerance or short_start.distanceTo(end) < tolerance or \
                short_end.distanceTo(start) < tolerance or short_end.distanceTo(end) < tolerance:
                return oid, geom
        return None, None
    
    def reverse_geometry(polyline):
        reversed_parts = []
        for part in polyline:
            reversed_parts.append(arcpy.Array(list(reversed(part))))
        return arcpy.Polyline(arcpy.Array(reversed_parts), polyline.spatialReference)

    def merge_lines(line1, line2, tolerance=5.0):
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
                for pt in part:
                    merged.add(pt)
            return arcpy.Polyline(merged, line1.spatialReference)

        elif l1_end.distanceTo(l2_end) < tolerance:
            # Reverse line2
            line2_rev = reverse_geometry(line2)
            return merge_lines(line1, line2_rev, tolerance)

        elif l1_start.distanceTo(l2_end) < tolerance:
            # Reverse line1
            line1_rev = reverse_geometry(line1)
            return merge_lines(line1_rev, line2, tolerance)

        elif l1_start.distanceTo(l2_start) < tolerance:
            # Reverse begge
            return merge_lines(reverse_geometry(line1), reverse_geometry(line2), tolerance)

        else:
            # No match
            return None

    # Collects all the relevant roads
    flat_roads = {}
    end_points = set()
    with arcpy.da.SearchCursor("roads_lyr_flat", ["OID@", "SHAPE@"]) as cursor:
        for oid, geom in cursor:
            flat_roads[oid] = geom
            start, end = get_endpoints(geom)
            end_points.add((round(start.centroid.X, 3), round(start.centroid.Y, 3)))
            end_points.add((round(end.centroid.X, 3), round(end.centroid.Y, 3)))


    combined_roads = dict(flat_roads)
    with arcpy.da.UpdateCursor("roads_lyr_round", ["OID@", "SHAPE@"]) as cursor:
        for oid, geom in cursor:
            if oid in combined_roads:
                continue
            start, end = get_endpoints(geom)
            
            start_coords = (round(start.firstPoint.X, 3), round(start.firstPoint.Y, 3))
            end_coords = (round(end.firstPoint.X, 3), round(end.firstPoint.Y, 3))
            
            if start_coords in end_points or end_coords in end_points:
                combined_roads[oid] = geom
                end_points.add(start_coords)
                end_points.add(end_coords)

    combined_oids = list(combined_roads.keys())
    oid_list_str = ",".join(str(oid) for oid in combined_oids)
    sql_query = f"OBJECTID IN ({oid_list_str})"

    arcpy.management.MakeFeatureLayer(
        in_features=cleaned_roads_fc,
        out_layer="roads_lyr"
    )
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view="roads_lyr",
        selection_type="NEW_SELECTION",
        where_clause=sql_query
    )

    all_roads = []
    with arcpy.da.SearchCursor("roads_lyr", ["OID@", "SHAPE@"]) as cursor:
        for row in cursor:
            all_roads.append((row[0], row[1]))

    with arcpy.da.UpdateCursor("roads_lyr", ["OID@", "SHAPE@"]) as update_cursor:
        to_delete = set()
        for idx, road in enumerate(update_cursor):
            oid, geom = road
            if geom is None:
                continue
            
            # If there are any short roads (<100m)
            if geom.length < 100:
                merge_oid, merge_geom = find_merge_candidate(geom, all_roads)
                if merge_geom:
                    # Combine the two geometries
                    new_geom = merge_lines(geom, merge_geom)
                    if new_geom:
                        update_cursor.updateRow((oid, new_geom))
                        all_roads = [
                            (r_oid, new_geom) if r_oid == oid else (r_oid, r_geom)
                            for r_oid, r_geom in all_roads
                            if r_oid != merge_oid
                        ]
                        to_delete.add(merge_oid)
                        print(f"Merged short road {oid} with {merge_oid}.")
    
    # Deletes the roads that have been merged into others
    with arcpy.da.UpdateCursor("roads_lyr", ["OID@"]) as delete_cursor:
        for row in delete_cursor:
            if row[0] in to_delete:
                delete_cursor.deleteRow()
                print(f"Deleted {row[0]} after merge.")

    buffer_to_roads = defaultdict(list)

    with arcpy.da.SearchCursor("roads_lyr", ["OID@", "SHAPE@"]) as road_cursor:
        # Finds all the roads 70m or closer to a dam
        # and assigns them to the nearest buffer polygon
        for road in road_cursor:
            min_dist = float('inf')
            nearest_oid = None
            for oid, buffer_poly in buffer_polygons:
                dist = road[1].distanceTo(buffer_poly)
                if dist < min_dist:
                    min_dist = dist
                    nearest_oid = oid
            buffer_to_roads[nearest_oid].append((road[0], road[1]))

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
    
    for buf_oid, buffer_poly in buffer_polygons:
        # For all buffer polygons, find the corresponding buffer line
        buffer_line = None
        for oid, line in buffer_lines:
            dist = line.distanceTo(buffer_poly)
            if dist < 5:
                # It should only be one line per polygon
                buffer_line = line
                break
        if buffer_line is None:
            continue
        
        # Fetch all roads associated with this buffer polygon
        roads = buffer_to_roads.get(buf_oid, [])
        if not roads:
            # If no roads, skip
            continue

        # Collects points inside the buffer polygon
        points_to_cluster = []
        for road_oid, line in roads:
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
            for idx, road in enumerate(update_cursor):
                if road[1] is None:
                    continue
                changed = False
                new_parts = []
                for part_idx, part in enumerate(road[1]):
                    # For each part of the road
                    new_part = []
                    for pt_idx, pt in enumerate(part):
                        idx = (road[0], part_idx, pt_idx)
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
                    new_line = arcpy.Polyline(arcpy.Array(new_parts), road[1].spatialReference)
                    road[1] = new_line
                    update_cursor.updateRow(road)
    
    arcpy.management.Integrate(
        in_features="roads_lyr",
        cluster_tolerance="10 Meters"
    )

    print("Roads snapped to buffers!")

if __name__=="__main__":
    main()
