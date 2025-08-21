# Importing packages
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

    field = "Hierarchy_analysis_dam"
    
    calculating_competing_areas(field)
    calculate_important_roads(field)

    # Editing the roads
    resolve_road_conflicts(field)
    snap_roads()
    smooth_roads()

@timing_decorator
def fetch_data():
    print("Fetching data")
    # Roads
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_roads.road_output_1, #input_n100.VegSti,
        expression="",
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
        expression="OBJTYPE = 'ElvBekk' OR OBJTYPE = 'Havflate' OR OBJTYPE = 'Innsjø' OR OBJTYPE = 'InnsjøRegulert'",
        output_name=Road_N100.test_dam__water_input__n100_road.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION
    )
    print("Data fetched")

@timing_decorator
def clip_data():
    print("Cropping data")
    # Roads
    arcpy.analysis.Clip(
        in_features=Road_N100.test_dam__road_input__n100_road.value,
        clip_features=Road_N100.test_dam__kommune__n100_road.value,
        out_feature_class=Road_N100.test_dam__relevant_roads__n100_road.value
    )
    # Dam
    arcpy.analysis.Clip(
        in_features=Road_N100.test_dam__dam_input__n100_road.value,
        clip_features=Road_N100.test_dam__kommune__n100_road.value,
        out_feature_class=Road_N100.test_dam__relevant_dam__n100_road.value
    )
    print("Data cropped")

@timing_decorator
def buffer_around_dam_as_line():
    arcpy.analysis.Buffer(
        in_features=Road_N100.test_dam__relevant_dam__n100_road.value,
        out_feature_class=Road_N100.test_dam__buffer_dam__n100_road.value,
        buffer_distance_or_field="60 Meters",
        line_end_type="FLAT",
        dissolve_option="NONE",
        method="PLANAR"
    )
    print("Buffer created")
    arcpy.management.PolygonToLine(
        in_features=Road_N100.test_dam__buffer_dam__n100_road.value,
        out_feature_class=Road_N100.test_dam__buffer_dam_as_line__n100_road.value
    )
    print("Buffer converted to line")

@timing_decorator
def calculating_competing_areas(hierarchy):
    print("Calculating competing areas")
    feature_classes = [
        Road_N100.test_dam__relevant_roads__n100_road.value,
        Road_N100.test_dam__relevant_dam__n100_road.value,
        Road_N100.test_dam__buffer_dam_as_line__n100_road.value
    ]
    feature_classes_single = [
        Road_N100.test_dam__relevant_roads_single__n100_road.value,
        Road_N100.test_dam__relevant_dam_single__n100_road.value,
        Road_N100.test_dam__buffer_dam_as_line_single__n100_road.value
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
    arcpy.management.MakeFeatureLayer(
        in_features=Road_N100.test_dam__relevant_roads_single__n100_road.value,
        out_layer="relevant_roads_lyr"
    )
    arcpy.management.SelectLayerByLocation(
        in_layer="relevant_roads_lyr",
        overlap_type="INTERSECT",
        select_features=Road_N100.test_dam__buffer_dam__n100_road.value
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
        out_feature_class=Road_N100.test_dam__200m_buffer_h4__n100_road.value,
        buffer_distance_or_field="200 Meters",
        dissolve_option="ALL"
    )
    arcpy.management.SelectLayerByLocation(
        in_layer="relevant_roads_lyr",
        selection_type="NEW_SELECTION",
        overlap_type="INTERSECT",
        select_features=Road_N100.test_dam__200m_buffer_h4__n100_road.value
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
def snap_roads():
    print("Starts snapping roads")
    arcpy.management.MakeFeatureLayer(
        in_features=Road_N100.test_dam__resolve_road_conflicts__n100_road.value,
        out_layer="relevant_roads_lyr"
    )
    arcpy.management.SelectLayerByLocation(
        in_layer="relevant_roads_lyr",
        overlap_type="INTERSECT",
        select_features=Road_N100.test_dam__buffer_dam__n100_road.value,
        selection_type="NEW_SELECTION"
    )
    arcpy.edit.Snap(
        "relevant_roads_lyr",
        [[
            Road_N100.test_dam__buffer_dam__n100_road.value,
            "VERTEX",
            "100 Meters"
        ]]
    )
    print("Roads snapped")

@timing_decorator
def smooth_roads():
    print("Starts smoothing roads")
    arcpy.cartography.SimplifyLine(
        in_features=Road_N100.test_dam__resolve_road_conflicts__n100_road.value,
        out_feature_class=Road_N100.test_dam__smooth_roads__n100_road.value,
        algorithm="POINT_REMOVE",
        tolerance="10 Meters"
    )
    print("Roads smoothed")

if __name__=="__main__":
    main()
