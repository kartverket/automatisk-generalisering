# Importing modules
import arcpy
import os
import time

# Importing custom modules
import config
from custom_tools import custom_arcpy
from input_data import input_n50
from input_data import input_n100

# Importing file manager
from file_manager.n100.file_manager_buildings import Building_N100

# Importing environment setup
from env_setup import environment_setup

# Environment setup
environment_setup.general_setup()


# Main function
def main():
    """
    This script detects and removes hospital and church clusters.
    A cluster is by our definition points that are closer together than 200 meters.

    """
    # Start timing
    start_time = time.time()

    hospital_church_selections()
    find_and_remove_clusters()

    # End timing
    end_time = time.time()

    # Calculate elapsed time
    elapsed_time = end_time - start_time

    # Convert to hours, minutes, and seconds
    hours, remainder = divmod(elapsed_time, 3600)
    minutes, seconds = divmod(remainder, 60)

    # Format as string
    time_str = "{:02} hours, {:02} minutes, {:.2f} seconds".format(
        int(hours), int(minutes), seconds
    )

    print(f"hospital_church_clusters took {time_str} to complete.")


###################################### Selecting hospital and churches from all building points ################################################


def hospital_church_selections():
    """
    The function selects hospital and churches and makes two separate feature classes for each
    """
    print("Selecting hospitals and churches and creating separate feature classes ...")

    # Input feature class
    input_for_selections = "tester_cluster_2"

    # SQL-expressions
    sql_select_all_hospital = "BYGGTYP_NBR IN (970, 719)"
    sql_select_all_church = "BYGGTYP_NBR = 671"

    # Selecting all hospitals and making feature layer
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_for_selections,
        expression=sql_select_all_hospital,
        output_name=Building_N100.hospital_church_selections__hospital_points__n100.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
        inverted=False,
    )

    # Selecting all churches and making feature layer
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_for_selections,
        expression=sql_select_all_church,
        output_name=Building_N100.hospital_church_selections__church_points__n100.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
        inverted=False,
    )


###################################### Finding clusters and joining fields ################################################


# Finding and removing hospital and church clusters
def find_and_remove_clusters():
    """
    This function finds clusters in the hospital and church layers.
    After this,
    """
    print("Finding hospital and church clusters...")

    # Finding hospital clusters
    arcpy.gapro.FindPointClusters(
        input_points=Building_N100.hospital_church_selections__hospital_points__n100.value,
        out_feature_class=Building_N100.find_and_remove_clusters__all_hospital_clusters__n100.value,
        clustering_method="DBSCAN",
        minimum_points="2",
        search_distance="200 Meters",
    )

    # Finding church clusters
    arcpy.gapro.FindPointClusters(
        input_points=Building_N100.hospital_church_selections__church_points__n100.value,
        out_feature_class=Building_N100.find_and_remove_clusters__all_church_clusters__n100.value,
        clustering_method="DBSCAN",
        minimum_points="2",
        search_distance="200 Meters",
    )

    print("Joining fields...")

    # Join CLUSTER_ID to church points OBJECTID
    arcpy.management.JoinField(
        in_data=Building_N100.hospital_church_selections__hospital_points__n100.value,
        in_field="OBJECTID",
        join_table=Building_N100.find_and_remove_clusters__all_hospital_clusters__n100.value,
        join_field="OBJECTID",
        fields="CLUSTER_ID",
    )

    # Join CLUSTER_ID to church points OBJECTID
    arcpy.management.JoinField(
        in_data=Building_N100.hospital_church_selections__church_points__n100.value,
        in_field="OBJECTID",
        join_table=Building_N100.find_and_remove_clusters__all_church_clusters__n100.value,
        join_field="OBJECTID",
        fields="CLUSTER_ID",
    )

    ######################################  Making feature classes from hospital and church points that are in a cluster and not in a cluster ################################################

    expression_cluster = "CLUSTER_ID > 0"
    expression_not_cluster = "CLUSTER_ID < 0"

    # Making feature class of hospital points NOT in a cluster
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.hospital_church_selections__hospital_points__n100.value,
        expression=expression_not_cluster,
        output_name=Building_N100.find_and_remove_clusters_hospital_points_not_in_cluster_n100.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )

    # Making feature class of hospital points in a cluster
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.hospital_church_selections__hospital_points__n100.value,
        expression=expression_cluster,
        output_name=Building_N100.find_and_remove_clusters_hospital_points_in_cluster_n100.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )

    # Making feature class of church points NOT in a cluster
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.hospital_church_selections__church_points__n100.value,
        expression=expression_not_cluster,
        output_name=Building_N100.find_and_remove_clusters_church_points_not_in_cluster_n100.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )

    # Making feature class of church points in a cluster
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.hospital_church_selections__church_points__n100.value,
        expression=expression_cluster,
        output_name=Building_N100.find_and_remove_clusters_church_points_in_cluster_n100.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )

    ###################################### Creating a merge list & adding all hospital and church features not a part of a cluster ################################################

    # List of hospital and church layers to merge at the end
    merge_hospitals_and_churches_list = []

    # Adding hospital and church features that are not in clusters to merge list
    merge_hospitals_and_churches_list.append(
        Building_N100.find_and_remove_clusters_hospital_points_not_in_cluster_n100.value
    )
    merge_hospitals_and_churches_list.append(
        Building_N100.find_and_remove_clusters_church_points_not_in_cluster_n100.value
    )

    ###################################### Reducing hospital clusters to only one point per cluster ################################################

    # Check if there are any features in the feature class
    get_count_hospital = arcpy.management.GetCount(
        Building_N100.find_and_remove_clusters_hospital_points_in_cluster_n100.value
    )
    count_hospital = int(get_count_hospital.getOutput(0))

    if count_hospital > 0:
        print("Hospital clusters found.")
        print("Minimum Bounding Geometry ...")

        # Finding minimum bounding geometry for hospital clusters
        arcpy.management.MinimumBoundingGeometry(
            in_features=Building_N100.find_and_remove_clusters_hospital_points_in_cluster_n100.value,
            out_feature_class=Building_N100.find_and_remove_clusters__minimum_bounding_geometry_hospital__n100.value,
            geometry_type="RECTANGLE_BY_AREA",
            group_option="LIST",
            group_field="CLUSTER_ID",
        )

        print("Feature to Point...")

        # Transforming minimum bounding geometry for hospital clusters to center point
        arcpy.management.FeatureToPoint(
            in_features=Building_N100.find_and_remove_clusters__minimum_bounding_geometry_hospital__n100.value,
            out_feature_class=Building_N100.find_and_remove_clusters__feature_to_point_hospital__n100.value,
        )

        print("Near...")

        # Find hospital point closest to the center point, Near fid is automatically added to hospital points attribute table
        arcpy.analysis.Near(
            in_features=Building_N100.find_and_remove_clusters_hospital_points_in_cluster_n100.value,
            near_features=Building_N100.find_and_remove_clusters__feature_to_point_hospital__n100.value,
            search_radius=None,
        )

        # Create a dictionary to store the minimum NEAR_DIST for each CLUSTER_ID
        min_near_dist_dict_hospital = {}

        print("Reducing clusters...")

        # Iterate through the feature class to find the minimum NEAR_DIST for each CLUSTER_ID
        with arcpy.da.SearchCursor(
            Building_N100.find_and_remove_clusters_hospital_points_in_cluster_n100.value,
            ["CLUSTER_ID", "NEAR_DIST", "OBJECTID"],
        ) as cursor:
            for row in cursor:
                cluster_id, near_dist, object_id = row

                # If the CLUSTER_ID is not in the dictionary or the current NEAR_DIST is smaller than the stored one
                if (
                    cluster_id not in min_near_dist_dict_hospital
                    or near_dist < min_near_dist_dict_hospital[cluster_id][0]
                ):
                    # Update the dictionary with the current NEAR_DIST and OBJECTID
                    min_near_dist_dict_hospital[cluster_id] = (near_dist, object_id)

        # Create a list of OBJECTIDs with the minimum NEAR_DIST for each CLUSTER_ID
        min_near_dist_object_ids_hospital = [
            object_id for _, object_id in min_near_dist_dict_hospital.values()
        ]

        # Making new layer of hospital cluster points that we want to keep
        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=Building_N100.find_and_remove_clusters_hospital_points_in_cluster_n100.value,
            expression=f"OBJECTID IN ({','.join(map(str, min_near_dist_object_ids_hospital))})",
            output_name=Building_N100.find_and_remove_clusters__chosen_hospitals_from_cluster__n100.value,
            selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
            inverted=False,
        )

        # Adding selected hospitals to the merge list
        merge_hospitals_and_churches_list.append(
            Building_N100.find_and_remove_clusters__chosen_hospitals_from_cluster__n100.value
        )

        ###################################### Reducing church clusters to only one point per cluster ################################################

        # Check if there are any church clusters
        get_count_church = arcpy.management.GetCount(
            Building_N100.find_and_remove_clusters_church_points_in_cluster_n100.value
        )
        count_church = int(get_count_church.getOutput(0))

        if count_church > 0:
            print("Church clusters found.")
            print("Minimum Bounding Geometry ...")
            # Finding minimum bounding geometry for church clusters
            arcpy.management.MinimumBoundingGeometry(
                in_features=Building_N100.find_and_remove_clusters_church_points_in_cluster_n100.value,
                out_feature_class=Building_N100.find_and_remove_clusters__minimum_bounding_geometry_church__n100.value,
                geometry_type="RECTANGLE_BY_AREA",
                group_option="LIST",
                group_field="CLUSTER_ID",
            )

            print("Feature to Point...")

            # Transforming minimum bounding geometry for church clusters to center point
            arcpy.management.FeatureToPoint(
                in_features=Building_N100.find_and_remove_clusters__minimum_bounding_geometry_church__n100.value,
                out_feature_class=Building_N100.find_and_remove_clusters__feature_to_point_church__n100.value,
            )

            # Find church point closest to the center point, Near fid is automatically added to church points attribute table
            arcpy.analysis.Near(
                in_features=Building_N100.find_and_remove_clusters_church_points_in_cluster_n100.value,
                near_features=Building_N100.find_and_remove_clusters__feature_to_point_church__n100.value,
                search_radius=None,
            )

            # Create a dictionary to store the minimum NEAR_DIST for each CLUSTER_ID
            min_near_dist_dict_church = {}

            # Iterate through the feature class to find the minimum NEAR_DIST for each CLUSTER_ID
            with arcpy.da.SearchCursor(
                Building_N100.find_and_remove_clusters_church_points_in_cluster_n100.value,
                ["CLUSTER_ID", "NEAR_DIST", "OBJECTID"],
            ) as cursor:
                for row in cursor:
                    cluster_id, near_dist, object_id = row

                    # If the CLUSTER_ID is not in the dictionary or the current NEAR_DIST is smaller than the stored one
                    if (
                        cluster_id not in min_near_dist_dict_church
                        or near_dist < min_near_dist_dict_church[cluster_id][0]
                    ):
                        # Update the dictionary with the current NEAR_DIST and OBJECTID
                        min_near_dist_dict_church[cluster_id] = (near_dist, object_id)

            # Create a list of OBJECTIDs with the minimum NEAR_DIST for each CLUSTER_ID
            min_near_dist_object_ids_church = [
                object_id for _, object_id in min_near_dist_dict_church.values()
            ]

            # Making layer of church points in a cluster
            custom_arcpy.select_attribute_and_make_permanent_feature(
                input_layer=Building_N100.find_and_remove_clusters_church_points_in_cluster_n100.value,
                expression=f"OBJECTID IN ({','.join(map(str, min_near_dist_object_ids_church))})",
                output_name=Building_N100.find_and_remove_clusters__chosen_churches_from_cluster__n100.value,
                selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
                inverted=False,
            )

            # Adding selected churches to the merge list
            merge_hospitals_and_churches_list.append(
                Building_N100.find_and_remove_clusters__chosen_churches_from_cluster__n100.value
            )

    ###################################### Merging all layers in the merge list ################################################

    # Merge the final hospital and church layers
    arcpy.management.Merge(
        inputs=merge_hospitals_and_churches_list,
        output=Building_N100.find_and_remove_clusters__reduced_hospital_and_church_points_2__n100.value,
    )

    print(
        f"Merge between potentially reduced hospital and churches, layer name {os.path.basename(Building_N100.find_and_remove_clusters__reduced_hospital_and_church_points_2__n100.value)} finished."
    )


if __name__ == "__main__":
    main()
