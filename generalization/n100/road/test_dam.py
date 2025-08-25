# Importing packages
from collections import defaultdict
import arcpy

arcpy.env.overwriteOutput = True

# Importing custom input files modules
from input_data import input_n50
from input_data import input_n100
from input_data import input_other

from input_data import input_roads

# Importing custom modules
from file_manager.n100.file_manager_roads import Road_N100
from env_setup import environment_setup
import env_setup.global_config
import config
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools import custom_arcpy
from custom_tools.general_tools.polygon_processor import PolygonProcessor
from custom_tools.general_tools.line_to_buffer_symbology import LineToBufferSymbology
from input_data.input_symbology import SymbologyN100
from constants.n100_constants import N100_Symbology, N100_SQLResources, N100_Values
from custom_tools.general_tools.partition_iterator import PartitionIterator
from custom_tools.generalization_tools.road.resolve_road_conflicts import (
    ResolveRoadConflicts,
)

@timing_decorator
def main():
    
    # Setup
    environment_setup.main()

    # Data preparation
    fetch_data()
    clip_data()
    buffer_around_dam_as_line()

    # Hierarchy implementation
    """
    field = "Hierarchy_analysis_dam"
    
    calculating_competing_areas(field)
    calculate_important_roads(field)

    # Editing the roads
    #resolve_road_conflicts(field)
    #"""
    # Editing the roads
    multiToSingle()
    snap_roads_to_buffer()

@timing_decorator
def fetch_data():
    print("Fetching data")
    # Roads
    custom_arcpy.select_attribute_and_make_permanent_feature( #"C:\\GIS_Files\\ag_outputs\\n100\\Roads.gdb\\Roads_Shifted",
        input_layer="C:\\GIS_Files\\ag_outputs\\n100\\Roads.gdb\\Roads_Shifted", # Road_N100.data_preparation___calculated_boarder_hierarchy_2___n100_road.value, # input_roads.road_output_1, # input_n100.VegSti,
        expression=None,
        output_name=Road_N100.test_dam__road_input__n100_road.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION
    )
    # Dam
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n100.AnleggsLinje,
        expression="objtype = 'Dam'",
        output_name=Road_N100.test_dam__dam_input__n100_road.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION
    )
    # Area
    kommune = "Steinkjer"
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n100.AdminFlate,
        expression=f"NAVN = '{kommune}'",
        output_name=Road_N100.test_dam__kommune__n100_road.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION
    )
    # Water
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n100.ArealdekkeFlate,
        expression=f"OBJTYPE = 'Havflate' OR OBJTYPE = 'Innsjø' OR OBJTYPE = 'InnsjøRegulert'",
        output_name=Road_N100.test_dam__water_input__n100_road.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION
    )
    print("Data fetched")

@timing_decorator
def clip_data():
    print("Cropping data")
    kommune = Road_N100.test_dam__kommune__n100_road.value
    # Roads
    arcpy.analysis.Clip(
        in_features=Road_N100.test_dam__road_input__n100_road.value,
        clip_features=kommune,
        out_feature_class=Road_N100.test_dam__relevant_roads__n100_road.value
    )
    # Dam
    arcpy.analysis.Clip(
        in_features=Road_N100.test_dam__dam_input__n100_road.value,
        clip_features=kommune,
        out_feature_class=Road_N100.test_dam__relevant_dam__n100_road.value
    )
    # Water
    arcpy.analysis.Clip(
        in_features=Road_N100.test_dam__water_input__n100_road.value,
        clip_features=kommune,
        out_feature_class=Road_N100.test_dam__relevant_water__n100_road.value
    )
    print("Data cropped")

@timing_decorator
def buffer_around_dam_as_line():
    dam_fc = Road_N100.test_dam__relevant_dam__n100_road.value
    buffer_output = Road_N100.test_dam__buffer_dam__n100_road.value
    buffer_line_fc = Road_N100.test_dam__buffer_dam_as_line__n100_road.value
    
    if arcpy.Exists(buffer_output):
        arcpy.management.Delete(buffer_output)

    arcpy.analysis.Buffer(
        in_features=dam_fc,
        out_feature_class=buffer_output,
        buffer_distance_or_field="60 Meters",
        line_end_type="ROUND",
        dissolve_option="NONE",
        method="PLANAR"
    )
    print("Buffer created")
    arcpy.management.PolygonToLine(
        in_features=buffer_output,
        out_feature_class=buffer_line_fc
    )
    if arcpy.Exists(buffer_line_fc):
        print("Buffer converted to line")

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
    print("Multipart to singlepart done")

@timing_decorator
def snap_roads_to_buffer():
    print("Removing noisy roads...")

    dam_fc = Road_N100.test_dam__relevant_dam__n100_road.value
    buffer_fc = Road_N100.test_dam__buffer_dam__n100_road.value

    water_fc = Road_N100.test_dam__relevant_water_single__n100_road.value
    water_buffer_fc = Road_N100.test_dam__buffer_water__n100_road.value
    
    roads_fc = Road_N100.test_dam__relevant_roads_single__n100_road.value # Road_N100.test_dam__resolve_road_conflicts__n100_road.value
    cleaned_roads_fc = Road_N100.test_dam__cleaned_roads__n100_road.value

    buffer_lines_fc = Road_N100.test_dam__buffer_dam_as_line_single__n100_road.value
    buffer_water_dam_fc = Road_N100.test_dam__buffer_dam_minus_water__n100_road.value

    if arcpy.Exists(buffer_fc):
        arcpy.management.Delete(buffer_fc)
    arcpy.analysis.Buffer(
        in_features=dam_fc,
        out_feature_class=buffer_fc,
        buffer_distance_or_field="70 Meters",
        line_end_type="ROUND",
        dissolve_option="NONE",
        method="PLANAR"
    )

    if arcpy.Exists(water_buffer_fc):
        arcpy.management.Delete(water_buffer_fc)
    arcpy.analysis.Buffer(
        in_features=water_fc,
        out_feature_class=water_buffer_fc,
        buffer_distance_or_field="55 Meters",
        line_end_type="ROUND",
        dissolve_option="NONE",
        method="PLANAR"
    )

    arcpy.management.CopyFeatures(roads_fc, cleaned_roads_fc)

    arcpy.management.MakeFeatureLayer(
        in_features=cleaned_roads_fc,
        out_layer="roads_lyr"
    )
    arcpy.management.SelectLayerByLocation(
        in_layer="roads_lyr",
        overlap_type="INTERSECT",
        select_features=buffer_fc
    )
    arcpy.analysis.Erase(
        in_features=buffer_lines_fc,
        erase_features=water_buffer_fc,
        out_feature_class=buffer_water_dam_fc
    )

    buffer_polygons = [(row[1], row[0]) for row in arcpy.da.SearchCursor(buffer_fc, ["SHAPE@", "OID@"])]
    buffer_lines = [(row[1], row[0]) for row in arcpy.da.SearchCursor(buffer_water_dam_fc, ["SHAPE@", "OID@"])]
    
    buffer_to_roads = defaultdict(list)

    with arcpy.da.UpdateCursor("roads_lyr", ["OID@", "SHAPE@"]) as road_cursor:
        for road in road_cursor:
            road_oid = road[0]
            line = road[1]
            min_dist = float('inf')
            nearest_oid = None
            for oid, buffer_poly in buffer_polygons:
                dist = line.distanceTo(buffer_poly)
                if dist < min_dist:
                    min_dist = dist
                    nearest_oid = oid
            buffer_to_roads[nearest_oid].append((road_oid, line))
    
    def cluster_points(points, threshold=1.0):
        clusters = []
        for pt, idx in points:
            found = False
            for cluster in clusters:
                if any(pt.distanceTo(other[0]) < threshold for other in cluster):
                    cluster.append((pt, idx))
                    found = True
                    break
            if not found:
                clusters.append([(pt, idx)])
        return clusters
    
    for buf_oid, buffer_poly in buffer_polygons:
        buffer_line = None
        for oid, line in buffer_lines:
            dist = line.distanceTo(buffer_poly)
            if dist < 5:
                #if oid == buf_oid:
                buffer_line = line
                break
        if buffer_line is None:
            continue

        roads = buffer_to_roads.get(buf_oid, [])
        if not roads:
            continue

        points_to_cluster = []
        for road_oid, line in roads:
            for part_idx, part in enumerate(line):
                for pt_idx, pt in enumerate(part):
                    if pt is None:
                        continue
                    pt_geom = arcpy.PointGeometry(pt, line.spatialReference)
                    if buffer_poly.contains(pt_geom):
                        points_to_cluster.append((pt_geom, (road_oid, part_idx, pt_idx)))

        clusters = cluster_points(points_to_cluster, threshold=1.0)

        snap_points = {}
        for cluster in clusters:
            ref_pt = cluster[0][0]
            m = buffer_line.measureOnLine(ref_pt)
            snap_pt = buffer_line.positionAlongLine(m).firstPoint
            for _, idx in cluster:
                snap_points[idx] = snap_pt

        with arcpy.da.UpdateCursor("roads_lyr", ["OID@", "SHAPE@"]) as update_cursor:
            for road in update_cursor:
                road_oid = road[0]
                line = road[1]
                changed = False
                new_parts = []
                for part_idx, part in enumerate(line):
                    new_part = []
                    for pt_idx, pt in enumerate(part):
                        idx = (road_oid, part_idx, pt_idx)
                        if idx in snap_points:
                            new_pt = snap_points[idx]
                            new_part.append(arcpy.Point(new_pt.X, new_pt.Y))
                            changed = True
                        else:
                            new_part.append(pt)
                    new_parts.append(arcpy.Array(new_part))
                if changed:
                    new_line = arcpy.Polyline(arcpy.Array(new_parts), line.spatialReference)
                    road[1] = new_line
                    update_cursor.updateRow(road)
    
    print("Roads modified and cleaned!")

if __name__=="__main__":
    main()
