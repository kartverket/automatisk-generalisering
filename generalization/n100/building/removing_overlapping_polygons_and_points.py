# Importing modules

# Importing custom files

# Import custom modules
from custom_tools.general_tools import custom_arcpy
from env_setup import environment_setup
from custom_tools.general_tools.file_utilities import compare_feature_classes
from custom_tools.general_tools.polygon_processor import PolygonProcessor
from custom_tools.general_tools.line_to_buffer_symbology import LineToBufferSymbology
from constants.n100_constants import N100_Symbology
from input_data.input_symbology import SymbologyN100


# Importing custom files
from file_manager.n100.file_manager_buildings import Building_N100
from constants.n100_constants import N100_SQLResources

# Importing general packages
import arcpy

# Importing timing decorator
from custom_tools.decorators.timing_decorator import timing_decorator


@timing_decorator
def main():
    environment_setup.main()
    copying_previous_file()
    adding_new_hierarchy_value_to_points()
    detecting_graphic_conflicts()
    selecting_points_close_to_graphic_conflict_polygons()
    finding_clusters_amongst_the_points()
    selecting_points_in_a_cluster_and_not_in_a_cluster()
    keep_point_with_highest_hierarchy_for_each_cluster()
    polygons_overlapping_roads_to_points()
    merging_final_points_together()
    remove_points_that_are_overlapping_roads()
    removing_building_polygons_overlapping_church_hospitals()


@timing_decorator
def copying_previous_file():
    """
    Summary:
        Copies an existing feature class and assigns it a new name.
    """

    # Copying and assigning new name to layer
    arcpy.management.Copy(
        in_data=Building_N100.removing_points_and_erasing_polygons_in_water_features___merged_points_and_tourist_cabins___n100_building.value,
        out_data=Building_N100.removing_overlapping_polygons_and_points___all_building_points___n100_building.value,
    )

    try:
        # Check if the "CLUSTER_ID" field exists
        if arcpy.ListFields(
            Building_N100.removing_overlapping_polygons_and_points___all_building_points___n100_building.value,
            "CLUSTER_ID",
        ):
            # Delete the "CLUSTER_ID" field if it exists
            arcpy.management.DeleteField(
                Building_N100.removing_overlapping_polygons_and_points___all_building_points___n100_building.value,
                "CLUSTER_ID",
            )
            print("Field 'CLUSTER_ID' deleted successfully.")
        else:
            print("Field 'CLUSTER_ID' does not exist.")
    except arcpy.ExecuteError as e:
        # Handle any other arcpy execution errors if needed
        print(f"An error occurred deleting fields: {e}")


@timing_decorator
def adding_new_hierarchy_value_to_points():
    """
    Summary:
        Calculates and assigns a new hierarchy value to building points based on their nbr code
    """
    # Determining and assigning symbol val
    arcpy.management.CalculateField(
        in_table=Building_N100.removing_overlapping_polygons_and_points___all_building_points___n100_building.value,
        field="hierarchy",
        expression="determineHierarchy(!byggtyp_nbr!)",
        expression_type="PYTHON3",
        code_block=N100_SQLResources.nbr_to_hierarchy_overlapping_points.value,
    )

    code_block_update_symbol_val = (
        "def update_symbol_val(symbol_val):\n"
        "    if symbol_val == -99:\n"
        "        return 8\n"
        "    return symbol_val"
    )

    arcpy.CalculateField_management(
        in_table=Building_N100.removing_overlapping_polygons_and_points___all_building_points___n100_building.value,
        field="symbol_val",
        expression="update_symbol_val(!symbol_val!)",
        expression_type="PYTHON3",
        code_block=code_block_update_symbol_val,
    )


@timing_decorator
def detecting_graphic_conflicts():
    """
    Summary:
        Detects graphic conflicts within a given set of features based on a 20 meter conflict distance.
    """
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.removing_overlapping_polygons_and_points___all_building_points___n100_building.value,
        in_symbology_layer=SymbologyN100.building_point.value,
        output_name=Building_N100.removing_overlapping_polygons_and_points___all_building_points___n100_building_lyrx.value,
    )

    arcpy.env.referenceScale = "100000"

    # Detecting Graphic Conflicts
    arcpy.cartography.DetectGraphicConflict(
        in_features=Building_N100.removing_overlapping_polygons_and_points___all_building_points___n100_building_lyrx.value,
        conflict_features=Building_N100.removing_overlapping_polygons_and_points___all_building_points___n100_building_lyrx.value,
        out_feature_class=Building_N100.removing_overlapping_polygons_and_points___graphic_conflicts_polygon___n100_building.value,
        conflict_distance="20 Meters",
    )


@timing_decorator
def selecting_points_close_to_graphic_conflict_polygons():
    """
    Summary:
        Selects points based on their proximity to graphic conflict polygons.
    """

    polygon_processor = PolygonProcessor(
        input_building_points=Building_N100.removing_overlapping_polygons_and_points___all_building_points___n100_building.value,
        output_polygon_feature_class=Building_N100.removing_overlapping_polygons_and_points___all_building_points_to_squares___n100_building.value,
        building_symbol_dimensions=N100_Symbology.building_symbol_dimensions.value,
        symbol_field_name="symbol_val",
        index_field_name="OBJECTID",
    )
    polygon_processor.run()

    # Find points that are close to the graphic conflict polygons
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.removing_overlapping_polygons_and_points___all_building_points_to_squares___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.removing_overlapping_polygons_and_points___graphic_conflicts_polygon___n100_building.value,
        output_name=Building_N100.removing_overlapping_polygons_and_points___squares_close_to_graphic_conflict_polygons___n100_building.value,
        search_distance="20 Meters",
    )

    # Find points that are close to the graphic conflict polygons
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.removing_overlapping_polygons_and_points___all_building_points_to_squares___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.removing_overlapping_polygons_and_points___graphic_conflicts_polygon___n100_building.value,
        output_name=Building_N100.removing_overlapping_polygons_and_points___squares_not_close_to_graphic_conflict_polygons___n100_building.value,
        search_distance="20 Meters",
        inverted=True,
    )

    arcpy.management.FeatureToPoint(
        in_features=Building_N100.removing_overlapping_polygons_and_points___squares_close_to_graphic_conflict_polygons___n100_building.value,
        out_feature_class=Building_N100.removing_overlapping_polygons_and_points___points_close_to_graphic_conflict_polygons___n100_building.value,
        point_location="INSIDE",
    )

    arcpy.management.FeatureToPoint(
        in_features=Building_N100.removing_overlapping_polygons_and_points___squares_not_close_to_graphic_conflict_polygons___n100_building.value,
        out_feature_class=Building_N100.removing_overlapping_polygons_and_points___points_NOT_close_to_graphic_conflict_polygons___n100_building.value,
        point_location="INSIDE",
    )


@timing_decorator
def finding_clusters_amongst_the_points():
    """
    Summary:
        Identifies clusters among points based on proximity and density.
        Specifically, finds clusters of points that are close to graphic conflict polygons.
    """
    # Finding church clusters
    arcpy.gapro.FindPointClusters(
        input_points=Building_N100.removing_overlapping_polygons_and_points___points_close_to_graphic_conflict_polygons___n100_building.value,
        out_feature_class=Building_N100.removing_overlapping_polygons_and_points___point_clusters___n100_building.value,
        clustering_method="DBSCAN",
        minimum_points="2",
        search_distance="140 Meters",
    )


@timing_decorator
def selecting_points_in_a_cluster_and_not_in_a_cluster():
    """
    Summary:
        Selects and categorizes points based on their cluster status.
        Points are divided into those that are within a cluster and those that are not.
    """
    expression_cluster = "CLUSTER_ID > 0"
    expression_not_cluster = "CLUSTER_ID < 0"

    # Making feature class of points that are in a cluster and will be used for further proscessing
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.removing_overlapping_polygons_and_points___point_clusters___n100_building.value,
        expression=expression_cluster,
        output_name=Building_N100.removing_overlapping_polygons_and_points___points_in_a_cluster___n100_building.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )

    # Making feature class of points that are NOT in a cluster and will be merged at the end
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.removing_overlapping_polygons_and_points___point_clusters___n100_building.value,
        expression=expression_not_cluster,
        output_name=Building_N100.removing_overlapping_polygons_and_points___points_not_in_a_cluster___n100_building.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )

    # Copying the layer because the other one will be modified
    arcpy.management.Copy(
        in_data=Building_N100.removing_overlapping_polygons_and_points___points_in_a_cluster___n100_building.value,
        out_data=Building_N100.removing_overlapping_polygons_and_points___points_in_a_cluster_original___n100_building.value,
    )


@timing_decorator
def keep_point_with_highest_hierarchy_for_each_cluster():
    """
    Summary:
        Iterates through each cluster and retains the point with the highest hierarchy value within the cluster.
        Deletes all other points in the cluster.
    """
    # Iterate over each cluster
    with arcpy.da.SearchCursor(
        Building_N100.removing_overlapping_polygons_and_points___points_in_a_cluster___n100_building.value,
        ["CLUSTER_ID"],
    ) as cursor:
        for row in cursor:
            cluster_id = row[0]

            # Create a SQL expression to select points belonging to the current cluster
            sql_expression = f"CLUSTER_ID = {cluster_id}"

            # Create a list to store the hierarchy values of points in the cluster
            hierarchy_values = []

            # Use a search cursor to iterate over points in the current cluster
            with arcpy.da.SearchCursor(
                Building_N100.removing_overlapping_polygons_and_points___points_in_a_cluster___n100_building.value,
                ["OBJECTID", "hierarchy"],
                sql_expression,
            ) as point_cursor:
                for point_row in point_cursor:
                    hierarchy_values.append(
                        (point_row[0], point_row[1])
                    )  # Store the OBJECTID and hierarchy value

            # Sort the points based on hierarchy value
            sorted_points = sorted(hierarchy_values, key=lambda x: x[1])

            # Keep the point with the highest hierarchy value
            if sorted_points:
                highest_hierarchy_point = sorted_points[0][0]

                # Use a delete cursor to delete points other than the one with the highest hierarchy value
                with arcpy.da.UpdateCursor(
                    Building_N100.removing_overlapping_polygons_and_points___points_in_a_cluster___n100_building.value,
                    ["OBJECTID"],
                    f"CLUSTER_ID = {cluster_id} AND OBJECTID <> {highest_hierarchy_point}",
                ) as delete_cursor:
                    for delete_row in delete_cursor:
                        delete_cursor.deleteRow()


def polygons_overlapping_roads_to_points():
    """
    Summary:
        Processes polygons that overlap with road buffers and transforms them to points.
        Also identifies and keeps polygons that do not intersect with road buffers.
    """

    road_lines_to_buffer_symbology = LineToBufferSymbology(
        input_road_lines=Building_N100.data_preparation___unsplit_roads___n100_building.value,
        sql_selection_query=N100_SQLResources.road_symbology_size_sql_selection.value,
        output_road_buffer=Building_N100.removing_overlapping_polygons_and_points___road_symbology_no_buffer_addition___n100_building.value,
        write_work_files_to_memory=False,
        keep_work_files=False,
        root_file=Building_N100.removing_overlapping_polygons_and_points___root_file_line_symbology___n100_building.value,
        fixed_buffer_addition=0,
    )
    road_lines_to_buffer_symbology.run()

    # Select polygons that intersect with road buffers
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.removing_points_and_erasing_polygons_in_water_features___final_building_polygons_merged___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.removing_overlapping_polygons_and_points___road_symbology_no_buffer_addition___n100_building.value,
        output_name=Building_N100.removing_overlapping_polygons_and_points___polygons_intersecting_road_buffers___n100_building.value,
    )

    # Convert the selected polygons that intersect with road buffers to points
    arcpy.management.FeatureToPoint(
        in_features=Building_N100.removing_overlapping_polygons_and_points___polygons_intersecting_road_buffers___n100_building.value,
        out_feature_class=Building_N100.removing_overlapping_polygons_and_points___polygons_to_points___n100_building.value,
        point_location="INSIDE",  # Points will be placed inside the polygons
    )

    # Select polygons that do NOT intersect with road buffers
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.removing_points_and_erasing_polygons_in_water_features___final_building_polygons_merged___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.removing_overlapping_polygons_and_points___road_symbology_no_buffer_addition___n100_building.value,
        output_name=Building_N100.removing_overlapping_polygons_and_points___polygons_NOT_intersecting_road_buffers___n100_building.value,
        inverted=True,  # Select polygons not intersecting with road buffers
    )


@timing_decorator
def merging_final_points_together():
    """
    Summary:
        Merges multiple point feature layers into a single final output layer.
    """
    # Merge the final hospital and church layers
    arcpy.management.Merge(
        inputs=[
            Building_N100.removing_overlapping_polygons_and_points___polygons_to_points___n100_building.value,
            Building_N100.removing_overlapping_polygons_and_points___points_NOT_close_to_graphic_conflict_polygons___n100_building.value,
            Building_N100.removing_overlapping_polygons_and_points___points_in_a_cluster___n100_building.value,
            Building_N100.removing_overlapping_polygons_and_points___points_not_in_a_cluster___n100_building.value,
        ],
        output=Building_N100.removing_overlapping_polygons_and_points___merging_final_points___n100_building.value,
    )


def remove_points_that_are_overlapping_roads():
    """
    Summary:
        Processes and filters points to remove those overlapping with road buffers,
        while preserving hospital and church points.
    """
    # Selecting all points that are NOT hospital and churches or tourist huts
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.removing_overlapping_polygons_and_points___merging_final_points___n100_building.value,
        expression="byggtyp_nbr IN (970, 719, 671, 956)",
        output_name=Building_N100.removing_overlapping_polygons_and_points___all_points_not_hospital_and_church__n100_building.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
        inverted=True,
    )
    # Selecting only hospital and churches or tourist huts, they are not going into polygon processor etc
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.removing_overlapping_polygons_and_points___merging_final_points___n100_building.value,
        expression="byggtyp_nbr IN (970, 719, 671, 956)",
        output_name=Building_N100.removing_overlapping_polygons_and_points___hospital_and_church_points__n100_building.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )

    code_block_update_symbol_val = (
        "def update_symbol_val(symbol_val):\n"
        "    if symbol_val == -99:\n"
        "        return 8\n"
        "    return symbol_val"
    )

    arcpy.CalculateField_management(
        in_table=Building_N100.removing_overlapping_polygons_and_points___all_points_not_hospital_and_church__n100_building.value,
        field="symbol_val",
        expression="update_symbol_val(!symbol_val!)",
        expression_type="PYTHON3",
        code_block=code_block_update_symbol_val,
    )

    polygon_processor = PolygonProcessor(
        input_building_points=Building_N100.removing_overlapping_polygons_and_points___all_points_not_hospital_and_church__n100_building.value,
        output_polygon_feature_class=Building_N100.removing_overlapping_polygons_and_points___points_to_squares___n100_building.value,
        building_symbol_dimensions=N100_Symbology.building_symbol_dimensions.value,
        symbol_field_name="symbol_val",
        index_field_name="OBJECTID",
    )
    polygon_processor.run()

    # Selecting only building squares that DOES NOT intersect with road buffers
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.removing_overlapping_polygons_and_points___points_to_squares___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.removing_overlapping_polygons_and_points___road_symbology_no_buffer_addition___n100_building.value,
        output_name=Building_N100.point_displacement_with_buffer___squares_not_overlapping_roads___n100_building.value,
        inverted=True,
    )

    # Polygon to point to transform squares back to points
    arcpy.management.FeatureToPoint(
        in_features=Building_N100.point_displacement_with_buffer___squares_not_overlapping_roads___n100_building.value,
        out_feature_class=Building_N100.removing_overlapping_polygons_and_points___squares_back_to_points___n100_building.value,
    )

    # Merge back together with hospital and church points that were selected out earlier
    arcpy.management.Merge(
        inputs=[
            Building_N100.removing_overlapping_polygons_and_points___hospital_and_church_points__n100_building.value,
            Building_N100.removing_overlapping_polygons_and_points___squares_back_to_points___n100_building.value,
        ],
        output=Building_N100.removing_overlapping_polygons_and_points___final___n100_building.value,
    )


def removing_building_polygons_overlapping_church_hospitals():
    polygon_processor = PolygonProcessor(
        input_building_points=Building_N100.removing_overlapping_polygons_and_points___hospital_and_church_points__n100_building.value,
        output_polygon_feature_class=Building_N100.removing_overlapping_polygons_and_points___points_to_squares_church_hospitals___n100_building.value,
        building_symbol_dimensions=N100_Symbology.building_symbol_dimensions.value,
        symbol_field_name="symbol_val",
        index_field_name="OBJECTID",
    )
    polygon_processor.run()

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.removing_overlapping_polygons_and_points___polygons_NOT_intersecting_road_buffers___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.removing_overlapping_polygons_and_points___points_to_squares_church_hospitals___n100_building.value,
        output_name=Building_N100.removing_overlapping_polygons_and_points___building_polygons_not_intersecting_church_hospitals____n100_building.value,
        inverted=True,
        search_distance="30 Meters",
    )


if __name__ == "__main__":
    main()
