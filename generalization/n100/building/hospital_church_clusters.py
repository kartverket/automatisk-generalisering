import arcpy

# Importing custom files relative to the root path
import config
from custom_tools import custom_arcpy
from env_setup import environment_setup
from input_data import input_n50
from input_data import input_n100

# Importing temporary files
from file_manager.n100.file_manager_buildings import Building_N100

# Importing environment
environment_setup.general_setup()


# Main function
def main():
    hospital_church_selections()
    find_clusters()


# Selecting hospital and churches from all building points
def hospital_church_selections():
    print("Selecting hospitals and churches and creating separate feature classes ...")

    # Input feature class
    input_for_selections = (
        Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value
    )

    # SQL-expressions

    sql_hospital = "BYGGTYP_NBR IN (970, 719)"
    sql_church = "BYGGTYP_NBR = 671"

    # Selecting all hospitals and making feature layer

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_for_selections,
        expression=sql_hospital,
        output_name=Building_N100.hospital_church_selections__hospital_points__n100,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
        inverted=False,
    )

    # Selecting all churches and making feature layer

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_for_selections,
        expression=sql_church,
        output_name=Building_N100.hospital_church_selections__church_points__n100,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
        inverted=False,
    )

    print("Finished making separate feature classes for hospital and church.")


# Finding hospital and church clusters
def find_clusters():
    print("Finding hospital and church clusters...")

    # Hospital

    arcpy.gapro.FindPointClusters(
        input_points=Building_N100.hospital_church_selections__hospital_points__n100,
        out_feature_class=Building_N100.find_clusters__all_hospital_clusters__n100,
        clustering_method="DBSCAN",
        minimum_points="2",
        search_distance="200 Meters",
    )

    # Church

    arcpy.gapro.FindPointClusters(
        input_points=Building_N100.hospital_church_selections__church_points__n100,
        out_feature_class=Building_N100.find_clusters__all_church_clusters__n100,
        clustering_method="DBSCAN",
        minimum_points="2",
        search_distance="200 Meters",
    )

    # Join CLUSTER_ID field to hospital and church feature classes

    print("Joining fields...")

    # Hospital

    arcpy.management.JoinField(
        in_data=hospital_points,
        in_field="OBJECTID",
        join_table=hospital_clusters,
        join_field="OBJECTID",
        fields="CLUSTER_ID",
    )

    # Church

    arcpy.management.JoinField(
        in_data=church_points,
        in_field="OBJECTID",
        join_table=church_clusters,
        join_field="OBJECTID",
        fields="CLUSTER_ID",
    )

    # Create an empty dictionary to store cluster information
    cluster_info_hospital = {}

    field_name = ["CLUSTER_ID"]

    with arcpy.da.SearchCursor(hospital_points, field_name) as cursor:
        for row in cursor:
            cluster_id = row[0]

            # Skip clusters with a single feature
            if cluster_id < 0:
                continue

            # Update the dictionary to store the cluster information
            if cluster_id in cluster_info_hospital:
                cluster_info_hospital[cluster_id] += 1
            else:
                cluster_info_hospital[cluster_id] = 1

    # Clean up, release the cursor
    del cursor

    # Picking out hospital-clusters of  & picking out hospital-clusters of 3 or more

    hospital_clusters_of_2_list = []
    hospital_clusters_of_3_or_more_list = []

    for cluster_id in cluster_info_hospital:
        # if cluster_info_hospital[cluster_id] == 2:
        # hospital_clusters_of_2_list.append(cluster_id)
        # elif cluster_info_hospital[cluster_id] >= 3:
        # hospital_clusters_of_3_or_more_list.append(cluster_id)
        if cluster_info_hospital[cluster_id] >= 2:
            hospital_clusters_of_3_or_more_list.append(cluster_id)

    # Create an empty dictionary to store cluster information
    cluster_info_church = {}

    # Create a SearchCursor to iterate through the "CLUSTER_ID" field
    with arcpy.da.SearchCursor(church_points, field_name) as cursor:
        for row in cursor:
            cluster_id = row[0]  # Access the "CLUSTER_ID" field

            # Skip clusters with a single feature or cluster_id <= 0
            if cluster_id < 1:
                continue

            # Update the dictionary to store the cluster information
            if cluster_id in cluster_info_church:
                cluster_info_church[cluster_id] += 1

    # Clean up, release the cursor
    del cursor

    # Picking out church-clusters of 2 & picking out church-clusters of 3 or more

    church_clusters_of_2_list = []
    church_clusters_of_3_or_more_list = []

    for cluster_id in cluster_info_church:
        # if cluster_info_church[cluster_id] == 2:
        # church_clusters_of_2_list.append(cluster_id)
        # elif cluster_info_church[cluster_id] >= 3:
        # church_clusters_of_3_or_more_list.append(cluster_id)
        if cluster_info_hospital[cluster_id] >= 2:
            hospital_clusters_of_3_or_more_list.append(cluster_id)

    # List of layers to merge

    merge_list = []

    # Hospital

    if len(hospital_clusters_of_3_or_more_list) > 0:
        print("Selecting hospital clusters of 3 or more points")

        hospital_clusters_of_3_and_more = "hospital_clusters_of_3_and_more"
        expression_hospital = "CLUSTER_ID IN ({})".format(
            ",".join(map(str, hospital_clusters_of_3_or_more_list))
        )

        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=hospital_points,
            expression=expression_hospital,
            output_name=hospital_clusters_of_3_and_more,
            selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
            inverted=False,
        )

        # Check if any features were selected
        if arcpy.management.GetCount(hospital_clusters_of_3_and_more)[0] == "0":
            print("No features match the specified criteria.")

        hospital_clusters_output_minimum_bounding_geometry = (
            "hospital_clusters_output_minimum_bounding_geometry"
        )

        print("Starting Minimum Bounding Geometry for hospital clusters...")

        arcpy.management.MinimumBoundingGeometry(
            in_features=hospital_clusters_of_3_and_more,
            out_feature_class=hospital_clusters_output_minimum_bounding_geometry,
            geometry_type="RECTANGLE_BY_AREA",
            group_option="LIST",
            group_field="CLUSTER_ID",
        )

        hospital_feature_to_point = "hospital_feature_to_point"

        print("Starting feature to point...")

        arcpy.management.FeatureToPoint(
            in_features=hospital_clusters_output_minimum_bounding_geometry,
            out_feature_class=hospital_feature_to_point,
        )

        # Find hospital point closest to feature to point

        print("Near analysis...")

        arcpy.analysis.Near(
            in_features=hospital_feature_to_point,
            near_features=hospital_points,
            search_radius=None,
        )

        field_near_fid = "NEAR_FID"

        near_fid_list = []

        with arcpy.da.SearchCursor(
            hospital_feature_to_point, [field_near_fid]
        ) as cursor:
            for row in cursor:
                near_fid = row[0]
                near_fid_list.append(near_fid)

        # Clean up, release the cursor
        del cursor

        SQL_expression = (
            f"OBJECTID IN ({','.join(map(str, near_fid_list))}) OR CLUSTER_ID < 0"
        )
        selected_hospitals = "selected_hospitals"

        print(f"Making permanent feature {selected_hospitals}...")

        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=hospital_points,
            expression=SQL_expression,
            output_name=selected_hospitals,
            selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
            inverted=False,
        )

        merge_list.append(selected_hospitals)

        # Check if any features were selected
        if arcpy.management.GetCount(selected_hospitals)[0] == "0":
            print("No features match the specified criteria.")

    else:
        print(
            f"No hospital clusters of 3 or more points were found in the dataset {hospital_points}"
        )
        merge_list.append(hospital_points)

    # Church

    if len(church_clusters_of_3_or_more_list) > 0:
        print("Church clusters of 3 or more were found...")

        print("Selecting church clusters of 3 or more points")

        church_clusters_of_3_and_more = "church_clusters_of_3_and_more"

        expression_church = "CLUSTER_ID IN ({})".format(
            ",".join(map(str, church_clusters_of_3_or_more_list))
        )

        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=church_points,
            expression=expression_church,
            output_name=church_clusters_of_3_and_more,
            selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
            inverted=False,
        )

        # Check if any features were selected
        if arcpy.management.GetCount(church_clusters_of_3_and_more)[0] == "0":
            print("No features match the specified criteria.")

        church_clusters_output_minimum_bounding_geometry = (
            "church_clusters_output_minimum_bounding_geometry"
        )

        print("Starting Minimum Bounding Geometry for church clusters...")

        arcpy.management.MinimumBoundingGeometry(
            in_features=church_clusters_of_3_and_more,
            out_feature_class=church_clusters_output_minimum_bounding_geometry,
            geometry_type="RECTANGLE_BY_AREA",
            group_option="LIST",
            group_field="CLUSTER_ID",
        )

        church_feature_to_point = "church_feature_to_point"

        print("Starting feature to point...")

        arcpy.management.FeatureToPoint(
            in_features=church_clusters_output_minimum_bounding_geometry,
            out_feature_class=church_feature_to_point,
        )

        # Find church point closest to feature to point

        print("Near analysis...")

        arcpy.analysis.Near(
            in_features=church_feature_to_point,
            near_features=church_points,
            search_radius=None,
        )

        field_near_fid = "NEAR_FID"

        near_fid_list = []

        with arcpy.da.SearchCursor(church_feature_to_point, [field_near_fid]) as cursor:
            for row in cursor:
                near_fid = row[0]
                near_fid_list.append(near_fid)

        # Clean up, release the cursor
        del cursor

        SQL_expression = (
            f"OBJECTID IN ({','.join(map(str, near_fid_list))}) OR CLUSTER_ID < 0"
        )
        selected_churches = "selected_churches"

        print(f"Making permanent feature {selected_churches}...")

        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=church_points,
            expression=SQL_expression,
            output_name=selected_churches,
            selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
            inverted=False,
        )

        merge_list.append(selected_churches)

        # Check if any features were selected
        if arcpy.management.GetCount(selected_churches)[0] == "0":
            print("No features match the specified criteria.")

    else:
        print(
            f"No church clusters of 3 or more points were found in the dataset {church_points}"
        )
        merge_list.append(church_points)

    # Merge the final hospital and church layers

    arcpy.management.Merge(
        inputs=merge_list,
        output=Building_N100.find_point_clusters__reduced_hospital_church_points__n100.value,
    )

    print(
        f"Merge between potentially reduced hospital and churches, layer name {Building_N100.find_point_clusters__reduced_hospital_church_points__n100.value} finished."
    )
