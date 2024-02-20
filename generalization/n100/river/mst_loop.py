import arcpy
import networkx as nx
import os
from itertools import combinations
import math

from env_setup import environment_setup
from custom_tools import custom_arcpy
from file_manager.n100.file_manager_rivers import River_N100
from input_data import input_n50
from custom_tools.file_utilities import FeatureClassCreator


def main():
    setup_arcpy_environment()
    prepare_data()
    create_collapsed_centerline()

    filter_complicated_lakes()

    # create_feature_class()


input_water_polygon = River_N100.centerline_pruning_loop__lake_features__n100.value
input_centerline = River_N100.river_centerline__water_feature_collapsed__n100.value
input_rivers = (
    River_N100.centerline_pruning_loop__rivers_erased_with_lake_features__n100.value
)

water_polygon = River_N100.centerline_pruning_loop__water_features_processed__n100.value
centerline = River_N100.centerline_pruning_loop__collapsed_hydropolygon__n100.value
rivers = River_N100.centerline_pruning_loop__river_inlets_erased__n100.value

complex_lakes = River_N100.centerline_pruning_loop__complex_water_features__n100.value
simple_lakes = River_N100.centerline_pruning_loop__simple_water_features__n100.value
river_inlet_nodes = (
    River_N100.centerline_pruning_loop__river_inlets_points_merged__n100.value
)
complex_centerlines = (
    River_N100.centerline_pruning_loop__complex_centerlines__n100.value
)
simple_centerlines = River_N100.centerline_pruning_loop__simple_centerlines__n100.value


def setup_arcpy_environment():
    environment_setup.general_setup()


def prepare_data():
    sql_expression_water_features = "OBJTYPE = 'FerskvannTørrfall' Or OBJTYPE = 'Innsjø' Or OBJTYPE = 'InnsjøRegulert' Or OBJTYPE = 'ElvBekk'"
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n50.ArealdekkeFlate,
        expression=sql_expression_water_features,
        output_name=River_N100.centerline_pruning_loop__lake_features__n100.value,
    )

    arcpy.analysis.PairwiseErase(
        in_features=River_N100.unconnected_river_geometry__river_area_selection__n100.value,
        erase_features=River_N100.centerline_pruning_loop__lake_features__n100.value,
        out_feature_class=River_N100.centerline_pruning_loop__rivers_erased_with_lake_features__n100.value,
    )
    print(
        f"Created {River_N100.river_centerline__rivers_near_waterfeatures_erased__n100.value}"
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

    sql_expression_torrfall = "OBJTYPE = 'FerskvannTørrfall'"

    custom_arcpy.select_attribute_and_make_feature_layer(
        input_layer=River_N100.centerline_pruning_loop__water_features_river_final_selection__n100.value,
        expression=sql_expression_torrfall,
        output_name=f"{River_N100.centerline_pruning_loop__water_features_river_final_selection__n100.value}_torrfall",
    )

    sql_expression_elvbekk = "OBJTYPE = 'ElvBekk'"

    custom_arcpy.select_attribute_and_make_feature_layer(
        input_layer=River_N100.centerline_pruning_loop__water_features_river_final_selection__n100.value,
        expression=sql_expression_elvbekk,
        output_name=f"{River_N100.centerline_pruning_loop__water_features_river_final_selection__n100.value}_elvbekk",
    )

    arcpy.topographic.EliminatePolygon(
        in_features=f"{River_N100.centerline_pruning_loop__water_features_river_final_selection__n100.value}_torrfall",
        surrounding_features=f"{River_N100.centerline_pruning_loop__water_features_river_final_selection__n100.value}_elvbekk",
    )

    sql_expression_small_features = "shape_Area <= 100000"

    custom_arcpy.select_attribute_and_make_feature_layer(
        input_layer=River_N100.centerline_pruning_loop__water_features_river_final_selection__n100.value,
        expression=sql_expression_small_features,
        output_name=f"{River_N100.centerline_pruning_loop__water_features_river_final_selection__n100.value}_small_features",
    )

    arcpy.Eliminate_management(
        in_features=f"{River_N100.centerline_pruning_loop__water_features_river_final_selection__n100.value}_small_features",
        out_feature_class=River_N100.centerline_pruning_loop__water_features_processed__n100.value,
        selection="LENGTH",
    )

    arcpy.PolygonToLine_management(
        in_features=River_N100.centerline_pruning_loop__water_features_processed__n100.value,
        out_feature_class=River_N100.centerline_pruning_loop__polygon_to_line__n100.value,
        neighbor_option="IDENTIFY_NEIGHBORS",
    )

    arcpy.management.AddSpatialJoin(
        target_features=River_N100.centerline_pruning_loop__polygon_to_line__n100.value,
        join_features=River_N100.centerline_pruning_loop__water_features_processed__n100.value,
        join_operation=None,
        join_type="KEEP_ALL",
        match_option="LARGEST_OVERLAP",
        permanent_join="PERMANENT_FIELDS",
    )

    sql_expression_boundaries = "LEFT_FID <> -1 AND RIGHT_FID <> -1"
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


def extract_closed_lines(input_feature_class, output_feature_class):
    """
    Extracts lines that start and end at the same point from the input feature class and
    creates a new feature class containing only these closed lines.

    Parameters:
    input_feature_class (str): The path to the input feature class to check.
    output_feature_class (str): The path to the output feature class for storing closed lines.
    """
    # Create the output feature class with the same spatial reference and fields as the input
    spatial_reference = arcpy.Describe(input_feature_class).spatialReference
    # Check if the output feature class already exists; if so, delete it
    if arcpy.Exists(output_feature_class):
        arcpy.Delete_management(output_feature_class)
    arcpy.CreateFeatureclass_management(
        out_path=os.path.dirname(output_feature_class),
        out_name=os.path.basename(output_feature_class),
        geometry_type="POLYLINE",
        spatial_reference=spatial_reference,
    )

    # Define fields to include (excluding OID and Shape) and add them to the output feature class
    fields_to_copy = [
        field.name
        for field in arcpy.ListFields(input_feature_class)
        if field.type not in ("OID", "Geometry")
    ]
    fields = [
        "SHAPE@XY"
    ] + fields_to_copy  # 'SHAPE@XY' used for simplicity, consider 'SHAPE@' for exact geometry copy
    for field in fields_to_copy:
        arcpy.AddField_management(
            output_feature_class,
            field,
            arcpy.ListFields(input_feature_class, field)[0].type,
        )

    # Process each line in the input feature class
    with arcpy.da.SearchCursor(
        input_feature_class, ["OID@", "SHAPE@"] + fields_to_copy
    ) as search_cursor, arcpy.da.InsertCursor(
        output_feature_class, ["SHAPE@"] + fields_to_copy
    ) as insert_cursor:
        for row in search_cursor:
            polyline = row[1]  # Geometry of the feature
            if polyline.firstPoint.equals(
                polyline.lastPoint
            ):  # Check if the line is closed
                # Prepare the row for insertion
                insert_row = [polyline] + list(row[2:])  # Exclude OID@
                insert_cursor.insertRow(insert_row)
                print(
                    f"Feature ID {row[0]} is closed and has been added to the output feature class."
                )


def create_collapsed_centerline():
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=input_rivers,
        overlap_type=custom_arcpy.OverlapType.BOUNDARY_TOUCHES.value,
        select_features=River_N100.centerline_pruning_loop__water_features_processed__n100.value,
        output_name=River_N100.centerline_pruning_loop__river_inlets__n100.value,
    )

    arcpy.analysis.PairwiseErase(
        in_features=River_N100.centerline_pruning_loop__river_inlets__n100.value,
        erase_features=River_N100.centerline_pruning_loop__water_features_processed__n100.value,
        out_feature_class=River_N100.centerline_pruning_loop__river_inlets_erased__n100.value,
    )
    print(
        f"Created {River_N100.river_centerline__rivers_near_waterfeatures_erased__n100.value}"
    )

    # Copy to rename the file to have less characters in the name since the name needs to fit inside a field in CollapseHydroPolygon
    arcpy.management.CopyFeatures(
        in_features=River_N100.centerline_pruning_loop__water_features_processed__n100.value,
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

    arcpy.management.FeatureVerticesToPoints(
        in_features=River_N100.centerline_pruning_loop__collapsed_hydropolygon__n100.value,
        out_feature_class=River_N100.centerline_pruning_loop__collapsed_hydropolygon_points__n100.value,
        point_location="BOTH_ENDS",
    )

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=River_N100.centerline_pruning_loop__collapsed_hydropolygon_points__n100.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT.value,
        select_features=River_N100.centerline_pruning_loop__water_features_shared_boundaries__n100.value,
        output_name=River_N100.centerline_pruning_loop__collapsed_hydropolygon_points_selected__n100.value,
    )

    arcpy.edit.Snap(
        in_features=River_N100.centerline_pruning_loop__shared_boundaries_midpoint__n100.value,
        snap_environment=[
            [
                River_N100.centerline_pruning_loop__collapsed_hydropolygon_points_selected__n100.value,
                "END",
                "3000 Meters",
            ]
        ],
    )

    extract_closed_lines(
        River_N100.centerline_pruning_loop__collapsed_hydropolygon__n100.value,
        River_N100.centerline_pruning_loop__closed_centerline_lines__n100.value,
    )

    arcpy.management.FeatureVerticesToPoints(
        in_features=River_N100.centerline_pruning_loop__closed_centerline_lines__n100.value,
        out_feature_class=River_N100.centerline_pruning_loop__closed_centerline_point__n100.value,
        point_location="END",
    )


def filter_complicated_lakes():
    arcpy.management.FeatureVerticesToPoints(
        in_features=River_N100.centerline_pruning_loop__collapsed_hydropolygon__n100.value,
        out_feature_class=River_N100.centerline_pruning_loop__centerline_start_end_vertex__n100.value,
        point_location="BOTH_ENDS",
    )

    arcpy.management.DeleteIdentical(
        in_dataset=River_N100.centerline_pruning_loop__centerline_start_end_vertex__n100.value,
        fields="Shape",
    )

    arcpy.management.FeatureVerticesToPoints(
        in_features=River_N100.centerline_pruning_loop__collapsed_hydropolygon__n100.value,
        out_feature_class=f"{River_N100.centerline_pruning_loop__river_inlet_dangles__n100.value}_not_selected",
        point_location="DANGLE",
    )

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=f"{River_N100.centerline_pruning_loop__river_inlet_dangles__n100.value}_not_selected",
        overlap_type=custom_arcpy.OverlapType.INTERSECT.value,
        select_features=River_N100.centerline_pruning_loop__river_inlets_erased__n100.value,
        output_name=River_N100.centerline_pruning_loop__river_inlet_dangles__n100.value,
    )

    arcpy.management.Merge(
        inputs=[
            River_N100.centerline_pruning_loop__shared_boundaries_midpoint__n100.value,
            River_N100.centerline_pruning_loop__river_inlet_dangles__n100.value,
        ],
        output=River_N100.centerline_pruning_loop__river_inlets_points_merged__n100.value,
    )
    print(
        "NB! Need to create a logic to fix missing inlet nodes between interconnected waterfeature polygons"
    )
    """
    Currently it only makes one node between two water features but some places this would lead to missing node connections
    as more nodes are needed.
    """

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=River_N100.centerline_pruning_loop__centerline_start_end_vertex__n100.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT.value,
        select_features=River_N100.centerline_pruning_loop__river_inlets_points_merged__n100.value,
        output_name=River_N100.centerline_pruning_loop__centerline_intersection_vertex__n100.value,
        inverted=True,
    )

    arcpy.management.Merge(
        inputs=[
            River_N100.centerline_pruning_loop__centerline_intersection_vertex__n100.value,
            River_N100.centerline_pruning_loop__closed_centerline_point__n100.value,
        ],
        output=River_N100.centerline_pruning_loop__intersection_points_merged__n100.value,
    )

    intersection_field = "intersection"
    river_inlet_field = "inlets"

    arcpy.AddField_management(
        in_table=River_N100.centerline_pruning_loop__intersection_points_merged__n100.value,
        field_name=intersection_field,
        field_type="LONG",
    )
    arcpy.CalculateField_management(
        in_table=River_N100.centerline_pruning_loop__intersection_points_merged__n100.value,
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

    target_features = (
        River_N100.centerline_pruning_loop__water_features_processed__n100.value
    )
    join_features_1 = (
        River_N100.centerline_pruning_loop__river_inlets_points_merged__n100.value
    )
    join_features_2 = (
        River_N100.centerline_pruning_loop__intersection_points_merged__n100.value
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

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=centerline,
        overlap_type=custom_arcpy.OverlapType.HAVE_THEIR_CENTER_IN.value,
        select_features=River_N100.centerline_pruning_loop__simple_water_features__n100.value,
        output_name=River_N100.centerline_pruning_loop__simple_centerlines__n100.value,
    )

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=centerline,
        overlap_type=custom_arcpy.OverlapType.HAVE_THEIR_CENTER_IN.value,
        select_features=River_N100.centerline_pruning_loop__complex_water_features__n100.value,
        output_name=River_N100.centerline_pruning_loop__complex_centerlines__n100.value,
    )

    create_lake_centerline_feature = FeatureClassCreator(
        template_fc=input_rivers,
        input_fc=River_N100.centerline_pruning_loop__simple_centerlines__n100.value,
        output_fc=River_N100.centerline_pruning_loop__finnished_centerlines__n100.value,
        object_type="POLYLINE",
        delete_existing=True,
    )
    create_lake_centerline_feature.run()


def create_feature_class():
    # create_lake_centerline_feature = FeatureClassCreator(
    #     template_fc=input_rivers,
    #     input_fc=River_N100.centerline_pruning_loop__simple_centerlines__n100.value,
    #     output_fc=River_N100.centerline_pruning_loop__finnished_centerlines__n100.value,
    #     object_type="POLYLINE",
    #     delete_existing=True,
    # )
    # create_lake_centerline_feature.run()

    input_feature_class = (
        River_N100.centerline_pruning_loop__water_features_processed__n100.value
    )

    dissolve_output = f"{input_feature_class}_dissolved"
    arcpy.analysis.PairwiseDissolve(
        in_features=input_feature_class,
        out_feature_class=dissolve_output,
        dissolve_field=["shape_Length", "shape_Area"],
        multi_part="MULTI_PART",
    )

    eliminate_polygon_part_output = f"{input_feature_class}_eliminate_polygon_part"

    arcpy.management.EliminatePolygonPart(
        in_features=dissolve_output,
        out_feature_class=eliminate_polygon_part_output,
        condition="AREA_OR_PERCENT",
        part_area="1000000",
        part_area_percent="99",
        part_option="CONTAINED_ONLY",
    )

    polygon_islands = f"{input_feature_class}_polygon_islands"
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=input_feature_class,
        overlap_type=custom_arcpy.OverlapType.COMPLETELY_WITHIN.value,
        select_features=eliminate_polygon_part_output,
        output_name=polygon_islands,
    )

    arcpy.topographic.EliminatePolygon(
        in_features=polygon_islands,
        surrounding_features=input_feature_class,
    )


if __name__ == "__main__":
    main()
