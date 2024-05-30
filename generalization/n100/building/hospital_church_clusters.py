# Importing modules
import arcpy
import random

# Importing custom modules
from custom_tools.general_tools import custom_arcpy

# Importing file manager
from file_manager.n100.file_manager_buildings import Building_N100

# Importing environment setup
from env_setup import environment_setup


# Importing timing decorator
from custom_tools.decorators.timing_decorator import timing_decorator


# Main function
@timing_decorator
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

    environment_setup.main()
    selecting_all_other_points_that_are_not_hospital_and_church()
    hospital_church_selections()
    find_clusters()
    reducing_clusters()
    hospitals_and_churches_too_close()


def selecting_all_other_points_that_are_not_hospital_and_church():
    # Selecting all hospitals and making feature layer
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.point_propogate_displacement___points_after_propogate_displacement___n100_building.value,
        expression="byggtyp_nbr IN (970, 719, 671)",
        output_name=Building_N100.hospital_church_clusters___all_other_points_that_are_not_hospital_church___n100_building.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
        inverted=True,
    )


@timing_decorator
def hospital_church_selections():
    """
    Summary:
        Selects hospitals and churches from the input point feature class, creating separate feature layers for each category.

    Details:
        - Hospitals are selected based on 'byggtyp_nbr' values 970 and 719.
        - Churches are selected based on 'byggtyp_nbr' value 671.
    """

    # SQL-expressions to select hospitals and churches
    sql_select_all_hospital = "byggtyp_nbr IN (970, 719)"
    sql_select_all_church = "byggtyp_nbr = 671"

    # Selecting all hospitals and making feature layer
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.point_propogate_displacement___points_after_propogate_displacement___n100_building.value,
        expression=sql_select_all_hospital,
        output_name=Building_N100.hospital_church_clusters___hospital_points___n100_building.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )

    # Selecting all churches and making feature layer
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.point_propogate_displacement___points_after_propogate_displacement___n100_building.value,
        expression=sql_select_all_church,
        output_name=Building_N100.hospital_church_clusters___church_points___n100_building.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )


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
        input_points=Building_N100.hospital_church_clusters___hospital_points___n100_building.value,
        out_feature_class=Building_N100.hospital_church_clusters___all_hospital_clusters___n100_building.value,
        clustering_method="DBSCAN",
        minimum_points="2",
        search_distance="250 Meters",
    )

    # Finding church clusters
    arcpy.gapro.FindPointClusters(
        input_points=Building_N100.hospital_church_clusters___church_points___n100_building.value,
        out_feature_class=Building_N100.hospital_church_clusters___all_church_clusters___n100_building.value,
        clustering_method="DBSCAN",
        minimum_points="2",
        search_distance="250 Meters",
    )

    print("Joining fields...")

    # Join CLUSTER_ID to church points OBJECTID
    arcpy.management.JoinField(
        in_data=Building_N100.hospital_church_clusters___hospital_points___n100_building.value,
        in_field="OBJECTID",
        join_table=Building_N100.hospital_church_clusters___all_hospital_clusters___n100_building.value,
        join_field="OBJECTID",
        fields="CLUSTER_ID",
    )

    # Join CLUSTER_ID to church points OBJECTID
    arcpy.management.JoinField(
        in_data=Building_N100.hospital_church_clusters___church_points___n100_building.value,
        in_field="OBJECTID",
        join_table=Building_N100.hospital_church_clusters___all_church_clusters___n100_building.value,
        join_field="OBJECTID",
        fields="CLUSTER_ID",
    )

    expression_cluster = "CLUSTER_ID > 0"
    expression_not_cluster = "CLUSTER_ID < 0"

    # Making feature class of hospital points in a cluster
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.hospital_church_clusters___hospital_points___n100_building.value,
        expression=expression_cluster,
        output_name=Building_N100.hospital_church_clusters___hospital_points_in_cluster___n100_building.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )
    # Making feature class of hospital points NOT in a cluster
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.hospital_church_clusters___hospital_points___n100_building.value,
        expression=expression_not_cluster,
        output_name=Building_N100.hospital_church_clusters___hospital_points_not_in_cluster___n100_building.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )

    # Making feature class of church points in a cluster
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.hospital_church_clusters___church_points___n100_building.value,
        expression=expression_cluster,
        output_name=Building_N100.hospital_church_clusters___church_points_in_cluster___n100_building.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )
    # Making feature class of church points NOT in a cluster
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.hospital_church_clusters___church_points___n100_building.value,
        expression=expression_not_cluster,
        output_name=Building_N100.hospital_church_clusters___church_points_not_in_cluster___n100_building.value,
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
    # Hospital and church points that are NOT in a cluster are already put in the list
    merge_hospitals_and_churches_list = [
        Building_N100.hospital_church_clusters___hospital_points_not_in_cluster___n100_building.value,
        Building_N100.hospital_church_clusters___church_points_not_in_cluster___n100_building.value,
    ]

    # Check if there are any hospital clusters, getting the number
    count_hospital = int(
        arcpy.management.GetCount(
            Building_N100.hospital_church_clusters___hospital_points_in_cluster___n100_building.value
        ).getOutput(0)
    )

    if count_hospital > 0:
        print("Hospital clusters found.")
        print("Minimum Bounding Geometry ...")

        # Finding minimum bounding geometry for hospital clusters
        arcpy.management.MinimumBoundingGeometry(
            in_features=Building_N100.hospital_church_clusters___hospital_points_in_cluster___n100_building.value,
            out_feature_class=Building_N100.hospital_church_clusters___minimum_bounding_geometry_hospital___n100_hospital.value,
            geometry_type="RECTANGLE_BY_AREA",
            group_option="LIST",
            group_field="CLUSTER_ID",
        )

        print("Feature to Point...")

        # Transforming minimum bounding geometry for hospital clusters to center point
        arcpy.management.FeatureToPoint(
            in_features=Building_N100.hospital_church_clusters___minimum_bounding_geometry_hospital___n100_hospital.value,
            out_feature_class=Building_N100.hospital_church_clusters___feature_to_point_hospital___n100_building.value,
        )

        print("Near...")

        # Find hospital point closest to the center point, Near fid is automatically added to hospital points attribute table
        arcpy.analysis.Near(
            in_features=Building_N100.hospital_church_clusters___hospital_points_in_cluster___n100_building.value,
            near_features=Building_N100.hospital_church_clusters___feature_to_point_hospital___n100_building.value,
            search_radius=None,
        )

        # Create a dictionary to store the minimum NEAR_DIST for each CLUSTER_ID
        min_near_dist_dict_hospital = {}

        print("Reducing clusters...")

        # Iterate through the feature class to find the minimum NEAR_DIST for each CLUSTER_ID
        with arcpy.da.SearchCursor(
            Building_N100.hospital_church_clusters___hospital_points_in_cluster___n100_building.value,
            ["CLUSTER_ID", "NEAR_DIST", "OBJECTID"],
        ) as cursor:
            for cluster_id, near_dist, object_id in cursor:
                # Check if the CLUSTER_ID is not in the dictionary, or if the current NEAR_DIST is smaller than the stored one,
                # or if the NEAR_DIST is equal but the OBJECTID is smaller
                if (
                    cluster_id not in min_near_dist_dict_hospital
                    or near_dist < min_near_dist_dict_hospital[cluster_id][0]
                ):
                    # Update the dictionary with the current NEAR_DIST and OBJECTID
                    min_near_dist_dict_hospital[cluster_id] = (near_dist, object_id)
                # If NEAR_DIST is equal and OBJECTID is larger, randomly replace the existing OBJECTID
                elif (
                    near_dist == min_near_dist_dict_hospital[cluster_id][0]
                    and object_id > min_near_dist_dict_hospital[cluster_id][1]
                ):
                    if random.random() < 0.5:  # Randomly choose which OBJECTID to keep
                        min_near_dist_dict_hospital[cluster_id] = (near_dist, object_id)

        # Create a list of OBJECTIDs with the minimum NEAR_DIST for each CLUSTER_ID
        min_near_dist_object_ids_hospital = [
            object_id for _, object_id in min_near_dist_dict_hospital.values()
        ]

        # Make a new layer of hospital cluster points that we want to keep
        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=Building_N100.hospital_church_clusters___hospital_points_in_cluster___n100_building.value,
            expression=f"OBJECTID IN ({','.join(map(str, min_near_dist_object_ids_hospital))})",
            output_name=Building_N100.hospital_church_clusters___chosen_hospitals_from_cluster___n100_building.value,
            selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
            inverted=False,
        )

        # Add selected hospitals to the merge list
        merge_hospitals_and_churches_list.append(
            Building_N100.hospital_church_clusters___chosen_hospitals_from_cluster___n100_building.value
        )

    # Check if there are any hospital clusters, getting the number
    count_church = int(
        arcpy.management.GetCount(
            Building_N100.hospital_church_clusters___church_points_in_cluster___n100_building.value
        ).getOutput(0)
    )

    if count_church > 0:
        print("Church clusters found.")
        print("Minimum Bounding Geometry running...")
        # Finding minimum bounding geometry for church clusters
        arcpy.management.MinimumBoundingGeometry(
            in_features=Building_N100.hospital_church_clusters___church_points_in_cluster___n100_building.value,
            out_feature_class=Building_N100.hospital_church_clusters___minimum_bounding_geometry_church___n100_building.value,
            geometry_type="RECTANGLE_BY_AREA",
            group_option="LIST",
            group_field="CLUSTER_ID",
        )

        print("Feature to Point...")

        # Transforming minimum bounding geometry for church clusters to center point
        arcpy.management.FeatureToPoint(
            in_features=Building_N100.hospital_church_clusters___minimum_bounding_geometry_church___n100_building.value,
            out_feature_class=Building_N100.hospital_church_clusters___feature_to_point_church___n100_building.value,
        )

        print("Near...")

        # Find church point closest to the center point. Near fid is automatically added to church points attribute table
        arcpy.analysis.Near(
            in_features=Building_N100.hospital_church_clusters___church_points_in_cluster___n100_building.value,
            near_features=Building_N100.hospital_church_clusters___feature_to_point_church___n100_building.value,
            search_radius=None,
        )

        # Create a dictionary to store the minimum NEAR_DIST for each CLUSTER_ID
        min_near_dist_dict_church = {}

        # Iterate through the feature class to find the minimum NEAR_DIST for each CLUSTER_ID
        with arcpy.da.SearchCursor(
            Building_N100.hospital_church_clusters___church_points_in_cluster___n100_building.value,
            ["CLUSTER_ID", "NEAR_DIST", "OBJECTID"],
        ) as cursor:
            for cluster_id, near_dist, object_id in cursor:
                # Check if the CLUSTER_ID is not in the dictionary, or if the current NEAR_DIST is smaller than the stored one,
                # or if the NEAR_DIST is equal but the OBJECTID is smaller
                if (
                    cluster_id not in min_near_dist_dict_church
                    or near_dist < min_near_dist_dict_church[cluster_id][0]
                    or (
                        near_dist == min_near_dist_dict_church[cluster_id][0]
                        and object_id < min_near_dist_dict_church[cluster_id][1]
                    )
                ):
                    # Update the dictionary with the current NEAR_DIST and OBJECTID
                    min_near_dist_dict_church[cluster_id] = (near_dist, object_id)
                # If NEAR_DIST is equal and OBJECTID is larger, randomly replace the existing OBJECTID
                elif (
                    near_dist == min_near_dist_dict_church[cluster_id][0]
                    and object_id > min_near_dist_dict_church[cluster_id][1]
                ):
                    if random.random() < 0.5:  # Randomly choose which OBJECTID to keep
                        min_near_dist_dict_church[cluster_id] = (near_dist, object_id)

        # Create a list of OBJECTIDs with the minimum NEAR_DIST for each CLUSTER_ID
        min_near_dist_object_ids_church = [
            object_id for _, object_id in min_near_dist_dict_church.values()
        ]

        # Make a layer of church points in a cluster
        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=Building_N100.hospital_church_clusters___church_points_in_cluster___n100_building.value,
            expression=f"OBJECTID IN ({','.join(map(str, min_near_dist_object_ids_church))})",
            output_name=Building_N100.hospital_church_clusters___chosen_churches_from_cluster___n100_building.value,
            selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
        )

        # Add selected churches to the merge list
        merge_hospitals_and_churches_list.append(
            Building_N100.hospital_church_clusters___chosen_churches_from_cluster___n100_building.value
        )

    # Merge the final hospital and church layers
    arcpy.management.Merge(
        inputs=merge_hospitals_and_churches_list,
        output=Building_N100.hospital_church_clusters___reduced_hospital_and_church_points_merged___n100_building.value,
    )


@timing_decorator
def hospitals_and_churches_too_close():
    # SQL-expressions to select hospitals and churches
    sql_select_all_hospital = "byggtyp_nbr IN (970, 719)"
    sql_select_all_church = "byggtyp_nbr = 671"

    # Selecting all hospitals and making feature layer
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.hospital_church_clusters___reduced_hospital_and_church_points_merged___n100_building.value,
        expression=sql_select_all_hospital,
        output_name=Building_N100.hospital_church_clusters___selecting_hospital_points_after_cluster_reduction___n100_building.value,
    )

    # Selecting all churches and making feature layer
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.hospital_church_clusters___reduced_hospital_and_church_points_merged___n100_building.value,
        expression=sql_select_all_church,
        output_name=Building_N100.hospital_church_clusters___selecting_church_points_after_cluster_reduction___n100_building.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )

    # Selecting ONLY churches that are MORE THAN 215 Meters away from hospitals
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.hospital_church_clusters___selecting_church_points_after_cluster_reduction___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.hospital_church_clusters___selecting_hospital_points_after_cluster_reduction___n100_building.value,
        output_name=Building_N100.hospital_church_clusters___church_points_NOT_too_close_to_hospitals___n100_building.value,
        search_distance="215 Meters",
        inverted=True,
    )

    # Merge the final hospital and church layers after potentially deleting churches
    arcpy.management.Merge(
        inputs=[
            Building_N100.hospital_church_clusters___selecting_hospital_points_after_cluster_reduction___n100_building.value,
            Building_N100.hospital_church_clusters___church_points_NOT_too_close_to_hospitals___n100_building.value,
            Building_N100.hospital_church_clusters___all_other_points_that_are_not_hospital_church___n100_building.value,
        ],
        output=Building_N100.hospital_church_clusters___final___n100_building.value,
    )

    print("Hospital and church clusters finished.")


if __name__ == "__main__":
    main()
