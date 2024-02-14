import arcpy
import networkx as nx
import os
from itertools import combinations
import math

from env_setup import environment_setup
from custom_tools import custom_arcpy
from file_manager.n100.file_manager_rivers import River_N100
from input_data import input_n50


def main():
    setup_arcpy_environment()
    prepare_data()
    create_collapsed_centerline()

    filter_complicated_lakes()


input_water_polygon = River_N100.centerline_pruning_loop__lake_features__n100.value
input_centerline = River_N100.river_centerline__water_feature_collapsed__n100.value
input_rivers = River_N100.unconnected_river_geometry__river_area_selection__n100.value

water_polygon = f"{River_N100.unconnected_river_geometry__water_area_features_selected__n100.value}_copy"
centerline = River_N100.centerline_pruning_loop__collapsed_hydropolygon__n100.value
rivers = River_N100.unconnected_river_geometry__river_area_selection__n100.value


def setup_arcpy_environment():
    environment_setup.general_setup()


def prepare_data():
    sql_expression_water_features = "OBJTYPE = 'FerskvannTørrfall' Or OBJTYPE = 'Innsjø' Or OBJTYPE = 'InnsjøRegulert' Or OBJTYPE = 'ElvBekk'"
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n50.ArealdekkeFlate,
        expression=sql_expression_water_features,
        output_name=River_N100.centerline_pruning_loop__lake_features__n100.value,
    )

    arcpy.analysis.PairwiseBuffer(
        in_features=input_rivers,
        out_feature_class=River_N100.centerline_pruning_loop__study_area__n100.value,
        buffer_distance_or_field="5 Kilometers",
        dissolve_option="ALL",
    )
    print("Created study area buffer")

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=input_water_polygon,
        overlap_type=custom_arcpy.OverlapType.INTERSECT.value,
        select_features=River_N100.centerline_pruning_loop__study_area__n100.value,
        output_name=River_N100.centerline_pruning_loop__water_features_study_area__n100.value,
    )

    arcpy.gapro.DissolveBoundaries(
        input_layer=River_N100.centerline_pruning_loop__water_features_study_area__n100.value,
        out_feature_class=River_N100.centerline_pruning_loop__water_features_dissolved__n100.value,
    )

    print("Dissolved water features boundaries")

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=River_N100.centerline_pruning_loop__water_features_dissolved__n100.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT.value,
        select_features=input_rivers,
        output_name=River_N100.centerline_pruning_loop__water_features_dissolved_river_intersect__n100.value,
    )

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=input_water_polygon,
        overlap_type=custom_arcpy.OverlapType.INTERSECT.value,
        select_features=River_N100.centerline_pruning_loop__water_features_dissolved_river_intersect__n100.value,
        output_name=River_N100.centerline_pruning_loop__water_features_river_final_selection__n100.value,
    )

    arcpy.PolygonToLine_management(
        in_features=River_N100.centerline_pruning_loop__water_features_river_final_selection__n100.value,
        out_feature_class=River_N100.centerline_pruning_loop__polygon_to_line__n100.value,
        neighbor_option="IDENTIFY_NEIGHBORS",
    )

    sql_expression_boundaries = "LEFT_FID <> -1 Or RIGHT_FID = -1"
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=River_N100.centerline_pruning_loop__polygon_to_line__n100.value,
        expression=sql_expression_boundaries,
        output_name=River_N100.centerline_pruning_loop__water_features_shared_boundaries__n100.value,
    )

    arcpy.management.FeatureVerticesToPoints(
        in_features=River_N100.centerline_pruning_loop__water_features_shared_boundaries__n100.value,
        out_feature_class=River_N100.centerline_pruning_loop__shared_boundaries_midpoint__n100.value,
        point_location="MID",
    )


def create_collapsed_centerline():
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=input_rivers,
        overlap_type=custom_arcpy.OverlapType.BOUNDARY_TOUCHES.value,
        select_features=River_N100.centerline_pruning_loop__water_features_river_final_selection__n100.value,
        output_name=River_N100.centerline_pruning_loop__river_inlets__n100.value,
    )

    arcpy.analysis.PairwiseErase(
        in_features=River_N100.centerline_pruning_loop__river_inlets__n100.value,
        erase_features=River_N100.centerline_pruning_loop__water_features_river_final_selection__n100.value,
        out_feature_class=River_N100.centerline_pruning_loop__river_inlets_erased__n100.value,
    )
    print(
        f"Created {River_N100.river_centerline__rivers_near_waterfeatures_erased__n100.value}"
    )

    # Copy to rename the file to have less characters in the name since the name needs to fit inside a field in CollapseHydroPolygon
    arcpy.management.CopyFeatures(
        in_features=River_N100.centerline_pruning_loop__water_features_river_final_selection__n100.value,
        out_feature_class=River_N100.short_name__water__n100.value,
    )
    print(f"Created {River_N100.short_name__water__n100.value}")

    arcpy.cartography.CollapseHydroPolygon(
        in_features=River_N100.short_name__water__n100.value,
        out_line_feature_class=River_N100.centerline_pruning_loop__collapsed_hydropolygon__n100.value,
        connecting_features=River_N100.centerline_pruning_loop__river_inlets_erased__n100.value,
        merge_adjacent_input_polygons="MERGE_ADJACENT",
    )
    print(
        f"Created {River_N100.centerline_pruning_loop__collapsed_hydropolygon__n100.value}"
    )

    arcpy.edit.Snap(
        in_features=River_N100.centerline_pruning_loop__shared_boundaries_midpoint__n100.value,
        snap_environment=[
            [
                River_N100.centerline_pruning_loop__collapsed_hydropolygon__n100.value,
                "END",
                "100 Meters",
            ]
        ],
    )


def filter_complicated_lakes():
    arcpy.management.FeatureVerticesToPoints(
        in_features=centerline,
        out_feature_class=River_N100.centerline_pruning_loop__centerline_start_end_vertex__n100.value,
        point_location="BOTH_ENDS",
    )

    arcpy.management.DeleteIdentical(
        in_dataset=River_N100.centerline_pruning_loop__centerline_start_end_vertex__n100.value,
        fields="Shape",
    )

    arcpy.management.FeatureVerticesToPoints(
        in_features=centerline,
        out_feature_class=f"{River_N100.centerline_pruning_loop__river_inlet_dangles__n100.value}_not_selected",
        point_location="DANGLE",
    )

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=f"{River_N100.centerline_pruning_loop__river_inlet_dangles__n100.value}_not_selected",
        overlap_type=custom_arcpy.OverlapType.BOUNDARY_TOUCHES.value,
        select_features=rivers,
        output_name=River_N100.centerline_pruning_loop__river_inlet_dangles__n100.value,
    )

    arcpy.management.Merge(
        inputs=[
            River_N100.centerline_pruning_loop__shared_boundaries_midpoint__n100.value,
            River_N100.centerline_pruning_loop__river_inlet_dangles__n100.value,
        ],
        output=River_N100.centerline_pruning_loop__river_inlets_points_merged__n100.value,
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
        in_table=River_N100.centerline_pruning_loop__river_inlets_points_merged__n100.value,
        field_name=river_inlet_field,
        field_type="LONG",
    )
    arcpy.CalculateField_management(
        in_table=River_N100.centerline_pruning_loop__river_inlets_points_merged__n100.value,
        field=river_inlet_field,
        expression=1,
    )

    target_features = water_polygon
    join_features_1 = (
        River_N100.centerline_pruning_loop__river_inlets_points_merged__n100.value
    )
    join_features_2 = (
        River_N100.centerline_pruning_loop__centerline_intersection_vertex__n100.value
    )

    # First Spatial Join - Adding river inlet data
    field_mappings = arcpy.FieldMappings()
    field_mappings.addTable(target_features)
    field_mappings.addTable(join_features_1)

    # Setup field mapping for river_inlet_field (assuming sum_inlets is the intended outcome)
    # Note: Corrected to ensure we're modifying the correct field mapping
    inlet_field_index = field_mappings.findFieldMapIndex(river_inlet_field)
    if inlet_field_index != -1:
        field_map = field_mappings.getFieldMap(inlet_field_index)
        field = field_map.outputField
        field.name = "sum_inlets"
        field.aliasName = "Sum of Inlets"
        field_map.outputField = field
        field_map.mergeRule = "Sum"
        field_mappings.replaceFieldMap(inlet_field_index, field_map)

    # Execute the first spatial join
    arcpy.analysis.SpatialJoin(
        target_features=target_features,
        join_features=join_features_1,
        out_feature_class=f"{target_features}_add_join_1",
        join_operation="JOIN_ONE_TO_ONE",
        join_type="KEEP_ALL",
        field_mapping=field_mappings,
        match_option="INTERSECT",
    )

    # Second Spatial Join - Adding intersection data
    field_mappings_2 = arcpy.FieldMappings()
    field_mappings_2.addTable(f"{target_features}_add_join_1")
    field_mappings_2.addTable(join_features_2)

    # Setup field mapping for intersection_field (assuming sum_intersection is the intended outcome)
    # Corrected to focus on intersection_field
    intersection_field_index = field_mappings_2.findFieldMapIndex(intersection_field)
    if intersection_field_index != -1:
        field_map = field_mappings_2.getFieldMap(intersection_field_index)
        field = field_map.outputField
        field.name = "sum_intersection"
        field.aliasName = "Sum of Intersection"
        field_map.outputField = field
        field_map.mergeRule = "Sum"
        field_mappings_2.replaceFieldMap(intersection_field_index, field_map)

    # Execute the second spatial join
    arcpy.analysis.SpatialJoin(
        target_features=f"{target_features}_add_join_1",
        join_features=join_features_2,
        out_feature_class=River_N100.centerline_pruning_loop__water_feature_summarized__n100.value,
        join_operation="JOIN_ONE_TO_ONE",
        join_type="KEEP_ALL",
        field_mapping=field_mappings_2,
        match_option="INTERSECT",
    )

    # Use CalculateField to set null ("sum_intersection" = <NULL>) values to 0
    arcpy.CalculateField_management(
        in_table=River_N100.centerline_pruning_loop__water_feature_summarized__n100.value,
        field="sum_intersection",
        expression="0 if !sum_intersection! is None else !sum_intersection!",
        expression_type="PYTHON3",
    )

    sql_simple_water_features = (
        "(sum_intersection < sum_inlets) OR (sum_intersection = 1 AND sum_inlets = 1)"
    )
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=River_N100.centerline_pruning_loop__water_feature_summarized__n100.value,
        expression=sql_simple_water_features,
        output_name=River_N100.centerline_pruning_loop__simple_water_features__n100.value,
    )

    sql_complex_water_features = "(sum_intersection >= sum_inlets) AND (sum_intersection <> 1 OR sum_inlets <> 1)"
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=River_N100.centerline_pruning_loop__water_feature_summarized__n100.value,
        expression=sql_complex_water_features,
        output_name=River_N100.centerline_pruning_loop__complex_water_features__n100.value,
    )


if __name__ == "__main__":
    main()
