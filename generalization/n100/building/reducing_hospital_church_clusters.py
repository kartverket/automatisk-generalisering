# Importing modules
import arcpy
import os

# Importing custom modules
from custom_tools import custom_arcpy

# Importing file manager
from file_manager.n100.file_manager_buildings import Building_N100

# Importing environment setup
from env_setup import environment_setup

# Environment setup
environment_setup.main()

# Importing timing decorator
from custom_tools.timing_decorator import timing_decorator


# Main function
@timing_decorator("reducing_hospital_church_clusters.py")
def main():
    """
    Summary:
        This script detects and reduces hospital and church clusters.

    Details:
        1. `hospital_church_selections`:
            Selects hospitals and churches from the input point feature class.

        2. `find_clusters`:
            Finds clusters in the hospital and church layers.

        3. `reducing_clusters`:
            Reduces clusters to one point for each cluster.
    """

    hospital_church_selections()
    find_clusters()


###################################### Selecting hospital and churches from all building points ################################################


@timing_decorator
def hospital_church_selections():
    """
    Summary:
        Selects hospitals and churches from the input point feature class, creating separate feature layers for each category.

    Details:
        - Hospitals are selected based on 'BYGGTYP_NBR' values 970 and 719.
        - Churches are selected based on 'BYGGTYP_NBR' value 671.
    """

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
@timing_decorator
def find_clusters():
    """
    Summary:
        Finds hospital and church clusters.
        A cluster is defined as two or more points that are closer together than 200 meters.

    Details:
        - Clusters are found for both hospitals and churches using the 'FindPointClusters' tool.
        - The CLUSTER_IDs are joined with the original hospital and church feature classes.
        - Points belonging to a hospital or church cluster are selected as new layers.
        - Points not belonging to a cluster are selected as new layers.

    Parameters:
        - The tool FindPointClusters has a search distance of **'200 Meters'** and a minimum of **'2 Points'**.
    """

    print("Finding hospital and church clusters...")

    # Finding hospital clusters
    arcpy.gapro.FindPointClusters(
        input_points=Building_N100.hospital_church_selections__hospital_points__n100.value,
        out_feature_class=Building_N100.find_clusters__all_hospital_clusters__n100.value,
        clustering_method="DBSCAN",
        minimum_points="2",
        search_distance="200 Meters",
    )

    # Finding church clusters
    arcpy.gapro.FindPointClusters(
        input_points=Building_N100.hospital_church_selections__church_points__n100.value,
        out_feature_class=Building_N100.find_clusters__all_church_clusters__n100.value,
        clustering_method="DBSCAN",
        minimum_points="2",
        search_distance="200 Meters",
    )

    print("Joining fields...")

    # Join CLUSTER_ID to church points OBJECTID
    arcpy.management.JoinField(
        in_data=Building_N100.hospital_church_selections__hospital_points__n100.value,
        in_field="OBJECTID",
        join_table=Building_N100.find_clusters__all_hospital_clusters__n100.value,
        join_field="OBJECTID",
        fields="CLUSTER_ID",
    )

    # Join CLUSTER_ID to church points OBJECTID
    arcpy.management.JoinField(
        in_data=Building_N100.hospital_church_selections__church_points__n100.value,
        in_field="OBJECTID",
        join_table=Building_N100.find_clusters__all_church_clusters__n100.value,
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
        output_name=Building_N100.find_clusters__hospital_points_not_in_cluster__n100.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )

    # Making feature class of hospital points in a cluster
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.hospital_church_selections__hospital_points__n100.value,
        expression=expression_cluster,
        output_name=Building_N100.find_clusters__hospital_points_in_cluster__n100.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )

    # Making feature class of church points NOT in a cluster
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.hospital_church_selections__church_points__n100.value,
        expression=expression_not_cluster,
        output_name=Building_N100.find_clusters__church_points_not_in_cluster__n100.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )

    # Making feature class of church points in a cluster
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.hospital_church_selections__church_points__n100.value,
        expression=expression_cluster,
        output_name=Building_N100.find_clusters__church_points_in_cluster__n100.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )


@timing_decorator
def reducing_clusters():
    """
    Summary:
        Reduces hospital and church clusters by keeping only one point for each detected cluster.

    Details:
        - A minimum bounding polygon is created using the cluster points.
        - The same polygon is transformed into a centerpoint.
        - Only the cluster point nearest to the centerpoint is retained.
        - Hospital and church points not part of a cluster are merged with the selected cluster points.

    Parameters:
        - Minimum Bounding Geometry is created with the geometry type RECTANGLE BY AREA.
    """

    # List of hospital and church layers to merge at the end
    merge_hospitals_and_churches_list = [
        Building_N100.find_clusters__hospital_points_not_in_cluster__n100.value,
        Building_N100.find_clusters__church_points_not_in_cluster__n100.value,
    ]

    # Check if there are any features in the feature class
    get_count_hospital = arcpy.management.GetCount(
        Building_N100.find_clusters__hospital_points_in_cluster__n100.value
    )
    count_hospital = int(get_count_hospital.getOutput(0))

    if count_hospital > 0:
        print("Hospital clusters found.")
        print("Minimum Bounding Geometry ...")

        # Finding minimum bounding geometry for hospital clusters
        arcpy.management.MinimumBoundingGeometry(
            in_features=Building_N100.find_clusters__hospital_points_in_cluster__n100.value,
            out_feature_class=Building_N100.reducing_clusters__minimum_bounding_geometry_hospital__n100.value,
            geometry_type="RECTANGLE_BY_AREA",
            group_option="LIST",
            group_field="CLUSTER_ID",
        )

        print("Feature to Point...")

        # Transforming minimum bounding geometry for hospital clusters to center point
        arcpy.management.FeatureToPoint(
            in_features=Building_N100.reducing_clusters__minimum_bounding_geometry_hospital__n100.value,
            out_feature_class=Building_N100.reducing_clusters__feature_to_point_hospital__n100.value,
        )

        print("Near...")

        # Find hospital point closest to the center point, Near fid is automatically added to hospital points attribute table
        arcpy.analysis.Near(
            in_features=Building_N100.find_clusters__hospital_points_in_cluster__n100.value,
            near_features=Building_N100.reducing_clusters__feature_to_point_hospital__n100.value,
            search_radius=None,
        )

        # Create a dictionary to store the minimum NEAR_DIST for each CLUSTER_ID
        min_near_dist_dict_hospital = {}

        print("Reducing clusters...")

        # Iterate through the feature class to find the minimum NEAR_DIST for each CLUSTER_ID
        with arcpy.da.SearchCursor(
            Building_N100.find_clusters__hospital_points_in_cluster__n100.value,
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
            input_layer=Building_N100.find_clusters__hospital_points_in_cluster__n100.value,
            expression=f"OBJECTID IN ({','.join(map(str, min_near_dist_object_ids_hospital))})",
            output_name=Building_N100.reducing_clusters__chosen_hospitals_from_cluster__n100.value,
            selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
            inverted=False,
        )

        # Adding selected hospitals to the merge list
        merge_hospitals_and_churches_list.append(
            Building_N100.reducing_clusters__chosen_hospitals_from_cluster__n100.value
        )

        ###################################### Reducing church clusters to only one point per cluster ################################################

    # Check if there are any church clusters
    get_count_church = arcpy.management.GetCount(
        Building_N100.find_clusters__hospital_points_in_cluster__n100.value
    )
    count_church = int(get_count_church.getOutput(0))

    if count_church > 0:
        print("Church clusters found.")
        print("Minimum Bounding Geometry ...")
        # Finding minimum bounding geometry for church clusters
        arcpy.management.MinimumBoundingGeometry(
            in_features=Building_N100.find_clusters__hospital_points_in_cluster__n100.value,
            out_feature_class=Building_N100.reducing_clusters__minimum_bounding_geometry_church__n100.value,
            geometry_type="RECTANGLE_BY_AREA",
            group_option="LIST",
            group_field="CLUSTER_ID",
        )

        print("Feature to Point...")

        # Transforming minimum bounding geometry for church clusters to center point
        arcpy.management.FeatureToPoint(
            in_features=Building_N100.reducing_clusters__minimum_bounding_geometry_church__n100.value,
            out_feature_class=Building_N100.reducing_clusters__feature_to_point_church__n100.value,
        )

        # Find church point closest to the center point, Near fid is automatically added to church points attribute table
        arcpy.analysis.Near(
            in_features=Building_N100.find_clusters__church_points_in_cluster__n100.value,
            near_features=Building_N100.reducing_clusters__feature_to_point_church__n100.value,
            search_radius=None,
        )

        # Create a dictionary to store the minimum NEAR_DIST for each CLUSTER_ID
        min_near_dist_dict_church = {}

        # Iterate through the feature class to find the minimum NEAR_DIST for each CLUSTER_ID
        with arcpy.da.SearchCursor(
            Building_N100.find_clusters__hospital_points_not_in_cluster__n100,
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
            input_layer=Building_N100.find_clusters__hospital_points_in_cluster__n100.value,
            expression=f"OBJECTID IN ({','.join(map(str, min_near_dist_object_ids_church))})",
            output_name=Building_N100.reducing_clusters__chosen_churches_from_cluster__n100.value,
            selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
            inverted=False,
        )

        # Adding selected churches to the merge list
        merge_hospitals_and_churches_list.append(
            Building_N100.reducing_clusters__chosen_churches_from_cluster__n100.value
        )

    ###################################### Merging all layers in the merge list ################################################

    # Merge the final hospital and church layers
    arcpy.management.Merge(
        inputs=merge_hospitals_and_churches_list,
        output=Building_N100.reducing_clusters__reduced_hospital_and_church_points_2__n100.value,
    )

    print(
        f"Merge between potentially reduced hospital and churches, layer name {os.path.basename(Building_N100.reducing_clusters__reduced_hospital_and_church_points_2__n100.value)} finished."
    )


if __name__ == "__main__":
    main()
