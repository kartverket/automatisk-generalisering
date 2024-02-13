import arcpy
import networkx as nx
import os
from itertools import combinations
import math

from env_setup import environment_setup
from custom_tools import custom_arcpy
from file_manager.n100.file_manager_rivers import River_N100


def main():
    setup_arcpy_environment()
    filter_complicated_lakes()


input_water_polygon = f"{River_N100.unconnected_river_geometry__water_area_features_selected__n100.value}_copy"
input_centerline = (
    f"{River_N100.river_centerline__water_feature_collapsed__n100.value}_copy"
)
input_rivers = River_N100.unconnected_river_geometry__river_area_selection__n100.value


def setup_arcpy_environment():
    environment_setup.general_setup()

    arcpy.management.CopyFeatures(
        in_features=River_N100.unconnected_river_geometry__water_area_features_selected__n100.value,
        out_feature_class=f"{River_N100.unconnected_river_geometry__water_area_features_selected__n100.value}_copy",
    )

    arcpy.management.CopyFeatures(
        in_features=River_N100.river_centerline__water_feature_collapsed__n100.value,
        out_feature_class=f"{River_N100.river_centerline__water_feature_collapsed__n100.value}_copy",
    )

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=River_N100.unconnected_river_geometry__river_area_selection__n100.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT.value,
        select_features=f"{River_N100.unconnected_river_geometry__water_area_features_selected__n100.value}_copy",
        output_name=f"{River_N100.unconnected_river_geometry__river_area_selection__n100.value}_copy",
    )


def filter_complicated_lakes():
    arcpy.management.FeatureVerticesToPoints(
        in_features=input_centerline,
        out_feature_class=River_N100.centerline_pruning_loop__centerline_start_end_vertex__n100.value,
        point_location="BOTH_ENDS",
    )

    arcpy.management.DeleteIdentical(
        in_dataset=River_N100.centerline_pruning_loop__centerline_start_end_vertex__n100.value,
        fields="Shape",
    )

    arcpy.management.FeatureVerticesToPoints(
        in_features=input_centerline,
        out_feature_class=f"{River_N100.centerline_pruning_loop__river_inlet_dangles__n100.value}_not_selected",
        point_location="DANGLE",
    )

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=f"{River_N100.centerline_pruning_loop__river_inlet_dangles__n100.value}_not_selected",
        overlap_type=custom_arcpy.OverlapType.BOUNDARY_TOUCHES.value,
        select_features=input_rivers,
        output_name=River_N100.centerline_pruning_loop__river_inlet_dangles__n100.value,
    )

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=River_N100.centerline_pruning_loop__centerline_start_end_vertex__n100.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT.value,
        select_features=River_N100.centerline_pruning_loop__river_inlet_dangles__n100.value,
        output_name=River_N100.centerline_pruning_loop__centerline_intersection_vertex__n100.value,
        inverted=True,
    )

    intersection_field = "intersection"
    river_inlet_field = "inlets"

    arcpy.AddField_management(
        in_table=River_N100.centerline_pruning_loop__centerline_intersection_vertex__n100.value,
        field_name=intersection_field,
        field_type="LONG",
    )
    arcpy.CalculateField_management(
        in_table=River_N100.centerline_pruning_loop__centerline_intersection_vertex__n100.value,
        field=intersection_field,
        expression=1,
    )

    arcpy.AddField_management(
        in_table=River_N100.centerline_pruning_loop__river_inlet_dangles__n100.value,
        field_name=river_inlet_field,
        field_type="LONG",
    )
    arcpy.CalculateField_management(
        in_table=River_N100.centerline_pruning_loop__river_inlet_dangles__n100.value,
        field=river_inlet_field,
        expression=1,
    )

    target_features = input_water_polygon
    join_features_1 = (
        River_N100.centerline_pruning_loop__centerline_intersection_vertex__n100.value
    )
    join_features_2 = (
        River_N100.centerline_pruning_loop__river_inlet_dangles__n100.value
    )

    # Create a new FieldMappings object and add both the target and join feature classes to it
    field_mappings = arcpy.FieldMappings()
    field_mappings.addTable(target_features)
    field_mappings.addTable(join_features_1)

    # Find the index of the intersection_field in the field mappings
    intersection_field_index = field_mappings.findFieldMapIndex(intersection_field)

    # If the field exists, modify its properties
    if intersection_field_index != -1:
        # Get the specific FieldMap object
        field_map = field_mappings.getFieldMap(intersection_field_index)

        # Get the output field's properties as a Field object
        field = field_map.outputField

        # Optionally, rename the output field to reflect its aggregated nature, e.g., sum_intersection
        field.name = "sum_intersection"
        field.aliasName = "Sum of Intersection"
        field_map.outputField = field

        # Set the merge rule to sum to aggregate the values
        field_map.mergeRule = "Sum"

        # Replace the old field map in the FieldMappings object with the updated one
        field_mappings.replaceFieldMap(intersection_field_index, field_map)

    # Perform the Add Spatial Join with the updated field mappings
    arcpy.analysis.SpatialJoin(
        target_features=target_features,
        join_features=join_features_1,
        out_feature_class=f"{target_features}_add_join_1",
        join_operation="JOIN_ONE_TO_ONE",
        join_type="KEEP_ALL",
        field_mapping=field_mappings,
        match_option="INTERSECT",
    )

    # Prepare for the second join operation
    field_mappings_2 = arcpy.FieldMappings()
    field_mappings_2.addTable(
        f"{target_features}_add_join_1"
    )  # The output of the first join as input
    field_mappings_2.addTable(join_features_2)

    # Find the index of the river_inlet_field in the field mappings
    river_inlet_field_index = field_mappings_2.findFieldMapIndex(river_inlet_field)

    # If the field exists, modify its properties
    if river_inlet_field_index != -1:
        field_map = field_mappings_2.getFieldMap(river_inlet_field_index)
        field = field_map.outputField
        field.name = "sum_inlets"
        field.aliasName = "Sum of Inlets"
        field_map.outputField = field
        field_map.mergeRule = "Sum"
        field_mappings_2.replaceFieldMap(river_inlet_field_index, field_map)

    # Perform the second Add Spatial Join with the updated field mappings for river_inlet_field
    arcpy.analysis.SpatialJoin(
        target_features=f"{target_features}_add_join_1",
        join_features=join_features_2,
        out_feature_class=River_N100.centerline_pruning_loop__water_feature_summarized__n100.value,
        join_operation="JOIN_ONE_TO_ONE",
        join_type="KEEP_ALL",
        field_mapping=field_mappings_2,
        match_option="INTERSECT",
    )

    sql_simple_water_features = "sum_intersection < sum_inlets"
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=River_N100.centerline_pruning_loop__water_feature_summarized__n100.value,
        expression=sql_simple_water_features,
        output_name=River_N100.centerline_pruning_loop__simple_water_features__n100.value,
    )

    sql_complex_water_features = "sum_intersection >= sum_inlets"
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=River_N100.centerline_pruning_loop__water_feature_summarized__n100.value,
        expression=sql_simple_water_features,
        output_name=River_N100.centerline_pruning_loop__complex_water_features__n100.value,
    )


if __name__ == "__main__":
    main()
