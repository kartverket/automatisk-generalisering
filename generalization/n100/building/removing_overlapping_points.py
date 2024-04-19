# Importing modules
import arcpy

# Importing custom files
from file_manager.n100.file_manager_buildings import Building_N100

# Import custom modules
from custom_tools import custom_arcpy
from env_setup import environment_setup
from custom_tools.timing_decorator import timing_decorator


def main():
    environment_setup.main()
    copying_previous_file()
    detecting_graphic_conflicts()
    selecting_points_close_to_graphic_conflict_polygons()
    selecting_points_in_a_cluster_and_not_in_a_cluster()
    finding_clusters_amongst_the_points()
    selecting_points_in_a_cluster_and_not_in_a_cluster()
    keep_point_with_highest_hierarchy_for_each_cluster()
    merging_final_points_together()


@timing_decorator
def copying_previous_file():

    # Copying and assigning new name to layer
    arcpy.management.Copy(
        in_data=Building_N100.removing_points_in_water_features___final_points___n100_building.value,
        out_data=Building_N100.removing_overlapping_points___all_building_points___n100_building.value,
    )


@timing_decorator
def detecting_graphic_conflicts():

    # Detecting Graphic Conflicts
    arcpy.cartography.DetectGraphicConflict(
        in_features=Building_N100.removing_points_in_water_features___final_points___n100_lyrx.value,
        conflict_features=Building_N100.removing_points_in_water_features___final_points___n100_lyrx.value,
        out_feature_class=Building_N100.removing_overlapping_points___after_detecting_graphic_conflicts___n100_building.value,
        conflict_distance="20 Meters",
    )


@timing_decorator
def selecting_points_close_to_graphic_conflict_polygons():

    # Find points that are close to the graphic conflict polygons
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.removing_overlapping_points___all_building_points___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.removing_overlapping_points___after_detecting_graphic_conflicts___n100_building.value,
        output_name=Building_N100.removing_overlapping_points___points_close_to_graphic_conflict_polygons___n100_building.value,
        search_distance="25 Meters",
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
        search_distance="40 Meters",
    )
    # Join CLUSTER_ID to points OBJECTID
    arcpy.management.JoinField(
        in_data=Building_N100.removing_overlapping_points___point_clusters___n100_building.value,
        in_field="OBJECTID",
        join_table=Building_N100.removing_overlapping_points___all_building_points___n100_building.value,
        join_field="OBJECTID",
        fields="CLUSTER_ID",
    )


@timing_decorator
def selecting_points_in_a_cluster_and_not_in_a_cluster():

    expression_cluster = "CLUSTER_ID > 0"
    expression_not_cluster = "CLUSTER_ID < 0"

    # Making feature class of points that are in a cluster and will be used for further proscessing
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.removing_overlapping_points___all_building_points___n100_building.value,
        expression=expression_cluster,
        output_name=Building_N100.removing_overlapping_points___points_in_a_cluster___n100_building.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )
    # Making feature class of points that are NOT in a cluster and will be merged at the end
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.removing_overlapping_points___all_building_points___n100_building.value,
        expression=expression_not_cluster,
        output_name=Building_N100.removing_overlapping_points___points_not_in_a_cluster___n100_building.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
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
            Building_N100.removing_overlapping_points___points_not_in_a_cluster___n100_building.value,
            Building_N100.removing_overlapping_points___points_in_a_cluster___n100_building.value,
        ],
        output=Building_N100.removing_overlapping_points___points_not_in_a_cluster___n100_building.value,
    )


if __name__ == "__main__":
    main()
