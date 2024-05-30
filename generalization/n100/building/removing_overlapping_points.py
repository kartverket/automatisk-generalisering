# Importing modules

# Importing custom files

# Import custom modules
from custom_tools.general_tools import custom_arcpy
from env_setup import environment_setup
from custom_tools.general_tools.file_utilities import compare_feature_classes
from custom_tools.general_tools.polygon_processor import PolygonProcessor
from constants.n100_constants import N100_Symbology

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
    merging_final_points_together()
    remove_points_that_are_overlapping_roads()


@timing_decorator
def copying_previous_file():
    # Copying and assigning new name to layer
    arcpy.management.Copy(
        in_data=Building_N100.removing_points_and_erasing_polygons_in_water_features___final_points_merged___n100_building.value,
        out_data=Building_N100.removing_overlapping_points___all_building_points___n100_building.value,
    )


@timing_decorator
def adding_new_hierarchy_value_to_points():
    # Determining and assigning symbol val
    arcpy.management.CalculateField(
        in_table=Building_N100.removing_overlapping_points___all_building_points___n100_building.value,
        field="hierarchy",
        expression="determineHierarchy(!byggtyp_nbr!)",
        expression_type="PYTHON3",
        code_block=N100_SQLResources.nbr_to_hierarchy_overlapping_points.value,
    )


@timing_decorator
def detecting_graphic_conflicts():
    arcpy.env.referenceScale = "100000"

    # Detecting Graphic Conflicts
    arcpy.cartography.DetectGraphicConflict(
        in_features=Building_N100.removing_points_and_erasing_polygons_in_water_features___final_points___n100_lyrx.value,
        conflict_features=Building_N100.removing_points_and_erasing_polygons_in_water_features___final_points___n100_lyrx.value,
        out_feature_class=Building_N100.removing_overlapping_points___graphic_conflicts_polygon___n100_building.value,
        conflict_distance="20 Meters",
    )


@timing_decorator
def selecting_points_close_to_graphic_conflict_polygons():
    # Find points that are close to the graphic conflict polygons
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.removing_overlapping_points___all_building_points___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.removing_overlapping_points___graphic_conflicts_polygon___n100_building.value,
        output_name=Building_N100.removing_overlapping_points___points_close_to_graphic_conflict_polygons___n100_building.value,
        search_distance="40 Meters",
    )

    # Find points that are close to the graphic conflict polygons
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.removing_overlapping_points___all_building_points___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.removing_overlapping_points___graphic_conflicts_polygon___n100_building.value,
        output_name=Building_N100.removing_overlapping_points___points_NOT_close_to_graphic_conflict_polygons___n100_building.value,
        search_distance="40 Meters",
        inverted=True,
    )


@timing_decorator
def finding_clusters_amongst_the_points():
    # Finding church clusters
    arcpy.gapro.FindPointClusters(
        input_points=Building_N100.removing_overlapping_points___points_close_to_graphic_conflict_polygons___n100_building.value,
        out_feature_class=Building_N100.removing_overlapping_points___point_clusters___n100_building.value,
        clustering_method="DBSCAN",
        minimum_points="2",
        search_distance="80 Meters",
    )


@timing_decorator
def selecting_points_in_a_cluster_and_not_in_a_cluster():
    expression_cluster = "CLUSTER_ID > 0"
    expression_not_cluster = "CLUSTER_ID < 0"

    # Making feature class of points that are in a cluster and will be used for further proscessing
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.removing_overlapping_points___point_clusters___n100_building.value,
        expression=expression_cluster,
        output_name=Building_N100.removing_overlapping_points___points_in_a_cluster___n100_building.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )

    # Making feature class of points that are NOT in a cluster and will be merged at the end
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.removing_overlapping_points___point_clusters___n100_building.value,
        expression=expression_not_cluster,
        output_name=Building_N100.removing_overlapping_points___points_not_in_a_cluster___n100_building.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )

    # Copying the layer because the other one will be modified
    arcpy.management.Copy(
        in_data=Building_N100.removing_overlapping_points___points_in_a_cluster___n100_building.value,
        out_data=Building_N100.removing_overlapping_points___points_in_a_cluster_original___n100_building.value,
    )


@timing_decorator
def keep_point_with_highest_hierarchy_for_each_cluster():
    # Iterate over each cluster
    with arcpy.da.SearchCursor(
        Building_N100.removing_overlapping_points___points_in_a_cluster___n100_building.value,
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
                Building_N100.removing_overlapping_points___points_in_a_cluster___n100_building.value,
                ["OBJECTID", "hierarchy"],
                sql_expression,
            ) as point_cursor:
                for point_row in point_cursor:
                    hierarchy_values.append(
                        (point_row[0], point_row[1])
                    )  # Store the OBJECTID and hierarchy value

            # Sort the points based on hierarchy value
            sorted_points = sorted(hierarchy_values, key=lambda x: x[1], reverse=True)

            # Keep the point with the highest hierarchy value
            if sorted_points:
                highest_hierarchy_point = sorted_points[0][0]

                # Use a delete cursor to delete points other than the one with the highest hierarchy value
                with arcpy.da.UpdateCursor(
                    Building_N100.removing_overlapping_points___points_in_a_cluster___n100_building.value,
                    ["OBJECTID"],
                    f"CLUSTER_ID = {cluster_id} AND OBJECTID <> {highest_hierarchy_point}",
                ) as delete_cursor:
                    for delete_row in delete_cursor:
                        delete_cursor.deleteRow()


@timing_decorator
def merging_final_points_together():
    # Merge the final hospital and church layers
    arcpy.management.Merge(
        inputs=[
            Building_N100.removing_overlapping_points___points_NOT_close_to_graphic_conflict_polygons___n100_building.value,
            Building_N100.removing_overlapping_points___points_in_a_cluster___n100_building.value,
            Building_N100.removing_overlapping_points___points_not_in_a_cluster___n100_building.value,
        ],
        output=Building_N100.removing_overlapping_points___merging_final_points___n100_building.value,
    )

    compare_feature_classes(
        Building_N100.removing_overlapping_points___all_building_points___n100_building.value,
        Building_N100.removing_overlapping_points___merging_final_points___n100_building.value,
    )


def remove_points_that_are_overlapping_roads():
    # Selecting all points that are NOT hospital and churches
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.removing_overlapping_points___merging_final_points___n100_building.value,
        expression="byggtyp_nbr IN (970, 719, 671)",
        output_name=Building_N100.removing_overlapping_points___all_points_not_hospital_and_church__n100_building.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
        inverted=True,
    )
    # Selecting only hospital and churches, they are not going into polygon processor etc
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.removing_overlapping_points___merging_final_points___n100_building.value,
        expression="byggtyp_nbr IN (970, 719, 671)",
        output_name=Building_N100.removing_overlapping_points___hospital_and_church_points__n100_building.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )

    # Polygon prosessor to turn points to squares so we can do an intersect with roads
    symbol_field_name = "symbol_val"
    index_field_name = "OBJECTID"

    print("Polygon prosessor...")
    polygon_process = PolygonProcessor(
        Building_N100.removing_overlapping_points___all_points_not_hospital_and_church__n100_building.value,  # input
        Building_N100.removing_overlapping_points___points_to_squares___n100_building.value,  # output
        N100_Symbology.building_symbol_dimensions.value,
        symbol_field_name,
        index_field_name,
    )
    polygon_process.run()

    # Selecting only building squares that DOES NOT intersect with road buffers
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.removing_overlapping_points___points_to_squares___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.polygon_resolve_building_conflicts___merged_road_buffers___n100_building.value,
        output_name=Building_N100.removing_overlapping_points___squares_not_overlapping_roads___n100_building.value,
        inverted=True,
    )

    # Polygon to point to transform squares back to points
    arcpy.management.FeatureToPoint(
        in_features=Building_N100.removing_overlapping_points___squares_not_overlapping_roads___n100_building.value,
        out_feature_class=Building_N100.removing_overlapping_points___squares_back_to_points___n100_building.value,
    )

    # Merge back together with hospital and church points that were selected out earlier
    arcpy.management.Merge(
        inputs=[
            Building_N100.removing_overlapping_points___hospital_and_church_points__n100_building.value,
            Building_N100.removing_overlapping_points___squares_back_to_points___n100_building.value,
        ],
        output=Building_N100.removing_overlapping_points___final___n100_building.value,
    )


if __name__ == "__main__":
    main()
