# Importing packages
from collections import defaultdict
from unittest import result
import arcpy
import math


arcpy.env.overwriteOutput = True

# Importing custom input files modules
from input_data import input_n100

from input_data import input_roads

# Importing custom modules
from file_manager.n100.file_manager_roads import Road_N100
from env_setup import environment_setup
import config
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools import custom_arcpy
from custom_tools.general_tools.partition_iterator import PartitionIterator
from custom_tools.generalization_tools.road.resolve_road_conflicts import (
    ResolveRoadConflicts
)

@timing_decorator
def main():
    
    # Setup
    environment_setup.main()
    arcpy.Delete_management("in_memory")

    # Data preparation
    fetch_data()
    clip_data()


    if has_dam():
        clip_and_erase_pre()
        edit_geom_pre()
        snap_and_merge_pre()
        create_buffer()
        create_buffer_line()
    
        # Hierarchy implementation
        """
        field = "Hierarchy_analysis_dam"
        
        calculating_competing_areas(field)
        calculate_important_roads(field)

        # Editing the roads
        #resolve_road_conflicts(field)
        #"""
        # Editing the roads
        #multiToSingle()
        snap_roads_to_buffer()
    else:
        print("No dam found in the selected municipality. Exiting script.")

@timing_decorator
def fetch_data():
    print("Fetching data...")

    ##################################
    # Choose municipality to work on #
    ##################################
    kommune = "Steinkjer"

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
def create_buffer():
    print("Creating buffers...")
    dam_fc = Road_N100.test_dam__relevant_dam__n100_road.value
    water_fc = r"in_memory\relevant_waters"
    buffers = [
        [dam_fc, r"in_memory\dam_buffer_60m", "60 Meters"],
        [dam_fc, r"in_memory\dam_buffer_70m", "70 Meters"],
        [water_fc, r"in_memory\water_buffer_55m", "55 Meters"]
    ]
    for i in range(len(buffers)):
        arcpy.analysis.Buffer(
            in_features=buffers[i][0],
            out_feature_class=buffers[i][1],
            buffer_distance_or_field=buffers[i][2],
            line_end_type="ROUND",
            dissolve_option="NONE",
            method="PLANAR"
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

@timing_decorator
def calculating_competing_areas(hierarchy):
    print("Calculating competing areas")
    feature_classes = [
        Road_N100.test_dam__relevant_roads__n100_road.value,
        Road_N100.test_dam__relevant_dam__n100_road.value,
        Road_N100.test_dam__buffer_dam_as_line__n100_road.value,
        Road_N100.test_dam__relevant_water__n100_road.value
    ]
    feature_classes_single = [
        Road_N100.test_dam__relevant_roads_single__n100_road.value,
        Road_N100.test_dam__relevant_dam_single__n100_road.value,
        Road_N100.test_dam__buffer_dam_as_line_single__n100_road.value,
        Road_N100.test_dam__relevant_water_single__n100_road.value
    ]
    print("Performing multipart to singlepart...")
    for i in range(len(feature_classes)):
        if arcpy.Exists(feature_classes_single[i]):
            arcpy.management.Delete(feature_classes_single[i])
        arcpy.management.MultipartToSinglepart(
            in_features=feature_classes[i],
            out_feature_class=feature_classes_single[i]
        )
        if hierarchy not in [f.name for f in arcpy.ListFields(feature_classes_single[i])]:
            arcpy.management.AddField(
                in_table=feature_classes_single[i],
                field_name=hierarchy,
                field_type="SHORT"
            )
        arcpy.management.CalculateField(
            in_table=feature_classes_single[i],
            field=hierarchy,
            expression=0,
            expression_type="PYTHON3"
        )
    print("Competing areas calculated")

@timing_decorator
def calculate_important_roads(hierarchy):
    print("Calculating important roads")

    roads_fc = Road_N100.test_dam__relevant_roads_single__n100_road.value
    buffer_dam_fc = Road_N100.test_dam__buffer_dam__n100_road.value
    buffer_h4 = Road_N100.test_dam__200m_buffer_h4__n100_road.value
    
    arcpy.management.MakeFeatureLayer(
        in_features=roads_fc,
        out_layer="relevant_roads_lyr"
    )
    arcpy.management.SelectLayerByLocation(
        in_layer="relevant_roads_lyr",
        overlap_type="INTERSECT",
        select_features=buffer_dam_fc
    )
    arcpy.management.CalculateField(
        in_table="relevant_roads_lyr",
        field=hierarchy,
        expression=4,
        expression_type="PYTHON3"
    )
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view="relevant_roads_lyr",
        selection_type="NEW_SELECTION",
        where_clause=f"{hierarchy} = 4"
    )
    arcpy.analysis.Buffer(
        in_features="relevant_roads_lyr",
        out_feature_class=buffer_h4,
        buffer_distance_or_field="200 Meters",
        dissolve_option="ALL"
    )
    arcpy.management.SelectLayerByLocation(
        in_layer="relevant_roads_lyr",
        selection_type="NEW_SELECTION",
        overlap_type="INTERSECT",
        select_features=buffer_h4
    )
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view="relevant_roads_lyr",
        selection_type="REMOVE_FROM_SELECTION",
        where_clause=f"{hierarchy} = 4"
    )
    arcpy.management.CalculateField(
        in_table="relevant_roads_lyr",
        field=hierarchy,
        expression=2,
        expression_type="PYTHON3"
    )
    print("Important roads calculated")

@timing_decorator
def resolve_road_conflicts(hierarchy): 
    print("Resolving road conflicts...")

    road = "road"
    dam = "dam"
    buffer = "buffer"
    displacement = "displacement"

    inputs = {
        road: [
            "input",
            Road_N100.test_dam__relevant_roads_single__n100_road.value
        ],
        dam: [
            "context",
            Road_N100.test_dam__relevant_dam_single__n100_road.value
        ],
        buffer: [
            "context",
            Road_N100.test_dam__buffer_dam_as_line_single__n100_road.value
        ]
    }

    outputs = {
        road: [
            "resolved_road_conflicts",
            Road_N100.test_dam__resolve_road_conflicts__n100_road.value
        ],
        displacement: [
            "displacement_feature",
            Road_N100.test_dam__resolve_road_conflicts_displacement_feature__n100_road.value
        ]
    }

    input_data_structure = [
        {
            "unique_alias": road,
            "input_line_feature": (road, "input"),
            "input_lyrx_feature": config.relevante_veier,
            "grouped_lyrx": True,
            "target_layer_name": "test_dam___relevante_veier___n100_road"
        },
        {
            "unique_alias": dam,
            "input_line_feature": (dam, "context"),
            "input_lyrx_feature": config.relevante_demninger,
            "grouped_lyrx": True,
            "target_layer_name": "test_dam___relevante_demninger___n100_road"
        },
        {
            "unique_alias": buffer,
            "input_line_feature": (buffer, "context"),
            "input_lyrx_feature": config.buffer_rundt_demning_som_linjer,
            "grouped_lyrx": True,
            "target_layer_name": "test_dam___buffer_rundt_demning_som_linjer___n100_road"
        }
    ]

    resolve_road_conflicts_config = {
        "class": ResolveRoadConflicts,
        "method": "run",
        "params": {
            "input_list_of_dicts_data_structure": input_data_structure,
            "root_file": Road_N100.test_dam__resolve_road_root__n100_road.value,
            "output_road_feature": (road, "resolved_road_conflicts"),
            "output_displacement_feature": (
                displacement,
                "displacement_feature",
            ),
            "map_scale": "100000",
            "hierarchy_field": hierarchy
        }
    }

    partition_resolve_road_conflicts = PartitionIterator(
        alias_path_data=inputs,
        alias_path_outputs=outputs,
        custom_functions=[resolve_road_conflicts_config],
        root_file_partition_iterator=Road_N100.test_dam__resolve_road_partition_root__n100_road.value,
        dictionary_documentation_path=Road_N100.test_dam__resolve_road_docu__n100_road.value,
        feature_count=25_000,
        run_partition_optimization=True,
        search_distance="500 Meters",
    )

    try:
        partition_resolve_road_conflicts.run()
    except Exception as e:
        print(f"An error occurred during road conflict resolution: {e}")

    print("Road conflicts resolved! 8)")

@timing_decorator
def multiToSingle():
    feature_classes = [
        "in_memory\\Roads_Shifted",
        Road_N100.test_dam__relevant_dam__n100_road.value,
        Road_N100.test_dam__buffer_dam_as_line__n100_road.value,
        Road_N100.test_dam__relevant_water__n100_road.value
    ]
    feature_classes_single = [
        Road_N100.test_dam__relevant_roads_single__n100_road.value,
        Road_N100.test_dam__relevant_dam_single__n100_road.value,
        Road_N100.test_dam__buffer_dam_as_line_single__n100_road.value,
        Road_N100.test_dam__relevant_water_single__n100_road.value
    ]
    print("Performing multipart to singlepart...")
    for i in range(len(feature_classes)):
        if arcpy.Exists(feature_classes_single[i]):
            arcpy.management.Delete(feature_classes_single[i])
        arcpy.management.MultipartToSinglepart(
            in_features=feature_classes[i],
            out_feature_class=feature_classes_single[i]
        )
    print("Multipart to singlepart done")

@timing_decorator
def snap_roads_to_buffer():
    print("Removing noisy roads...")

    roads_fc = "in_memory\\Roads_Shifted"
    cleaned_roads_fc = Road_N100.test_dam__cleaned_roads__n100_road.value
    buffer_fc = r"in_memory\dam_buffer_70m"
    buffer_lines_fc = Road_N100.test_dam__dam_buffer_60m_line__n100_road.value
    water_buffer_fc = r"in_memory\water_buffer_55m"
    buffer_water_dam_fc = r"in_memory\dam_buffer_without_water"

    arcpy.management.CopyFeatures(roads_fc, cleaned_roads_fc)

    arcpy.management.MakeFeatureLayer(
        in_features=cleaned_roads_fc,
        out_layer="roads_lyr"
    )
    arcpy.management.SelectLayerByLocation(
        # Finds all roads 70m or closer to a dam
        in_layer="roads_lyr",
        overlap_type="INTERSECT",
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
    
    buffer_to_roads = defaultdict(list)

    with arcpy.da.UpdateCursor("roads_lyr", ["OID@", "SHAPE@"]) as road_cursor:
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
            for road in update_cursor:
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
    
    print("Roads modified and cleaned!")




@timing_decorator
def clip_and_erase_pre():
    buffer_fc = "DamBuffer_35m"
    pre_dissolve = "in_memory\\roads_pre_dissolve"
    outside_fc = "in_memory\\roads_outside"
    inside_fc = "in_memory\\roads_inside"
    inside_wdata_fc = "in_memory\\roads_inside_with_data"

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
    inside_wdata_fc = "in_memory\\roads_inside_with_data"
    moved_name     = "RoadLines_Moved"
    roadlines_moved = "in_memory\\RoadLines_Moved"


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
    
    arcpy.CopyFeatures_management(roadlines_moved, "C:\\temp\\Roads.gdb\\roadsafterbeingmoved")



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
    roadlines_moved = "in_memory\\RoadLines_Moved"
    outside_fc = "in_memory\\roads_outside"
    final_fc = "in_memory\\Roads_Shifted"

    # Define snap environment
    snap_env = [[outside_fc, "END", "40 Meters"]]

    # Snap 
    arcpy.Snap_edit(roadlines_moved, snap_env)

    # Merge the two sets
    arcpy.Merge_management([roadlines_moved, outside_fc], final_fc)

    arcpy.CopyFeatures_management(final_fc, "C:\\temp\\Roads.gdb\\roadsafterbeingsnapped")



    








if __name__=="__main__":
    main()
