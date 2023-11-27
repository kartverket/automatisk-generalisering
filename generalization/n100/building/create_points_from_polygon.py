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
    grunnriss_to_point()


def grunnriss_to_point():
    """
    This function creates points from small grunnriss lost during aggregation, and merges
    them together with collapsed points from the tools simplify building and simplify polygon.

    Input data:

    Output data:

    """

    custom_arcpy.select_location_and_make_feature_layer(
        input_layer=Building_N100.selecting_grunnriss_for_generalization__large_enough_grunnriss__n100.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.grunnriss_to_point__aggregated_polygon__n100.value,
        output_name=Building_N100.grunnriss_to_point__intersect_aggregated_and_original__n100.value,
        inverted=True,
    )

    arcpy.management.FeatureToPoint(
        in_features=Building_N100.grunnriss_to_point__intersect_aggregated_and_original__n100.value,
        out_feature_class=Building_N100.grunnriss_to_point__grunnriss_feature_to_point__n100.value,
    )

    # Base output which the for loop through for output creation
    base_output_path = Building_N100.grunnriss_to_point__spatial_join_points__n100.value

    # List of input features which will be spatially joined
    input_features = [
        Building_N100.grunnriss_to_point__collapsed_points_simplified_polygon__n100.value,
        Building_N100.grunnriss_to_point__simplified_building_points_simplified_building_1__n100.value,
        Building_N100.grunnriss_to_point__simplified_building_points_simplified_building_2__n100.value,
    ]

    #  Feature with the field information which will be used for spatial join
    join_features = (
        Building_N100.selecting_grunnriss_for_generalization__large_enough_grunnriss__n100.value
    )

    # Looping through each Spatial Join operation
    for i, input_feature in enumerate(input_features):
        # Generate dynamic output path by appending iteration index
        output_feature = f"{base_output_path}_{i+1}"

        arcpy.analysis.SpatialJoin(
            target_features=input_feature,
            join_features=join_features,
            out_feature_class=output_feature,
            join_operation="JOIN_ONE_TO_ONE",
            match_option="INTERSECT",
        )
        print(f"Spatial join {i+1} completed with output: {output_feature}")

    # Finding the number of outputs from the Spatial Join step to be used in the Merge
    num_outputs = len(input_features)
    # Generate list of output paths for merge
    output_paths = [f"{base_output_path}_{i+1}" for i in range(num_outputs)]

    # Additional inputs for the merge (if any)
    additional_inputs = [
        Building_N100.selecting_grunnriss_for_generalization__points_created_from_small_grunnriss__n100.value,
        Building_N100.selecting_grunnriss_for_generalization__kirke_points_created_from_grunnriss__n100.value,
        Building_N100.grunnriss_to_point__grunnriss_feature_to_point__n100.value,
    ]
    # Complete list of inputs for the merge
    merge_inputs = additional_inputs + output_paths

    # Perform the Merge operation
    arcpy.management.Merge(
        inputs=merge_inputs,
        output=Building_N100.grunnriss_to_point__merged_points_created_from_grunnriss__n100.value,
    )
    print("Merge completed")


def find_point_clusters():
    # Input layer

    bygningspunkt_pre_symbology = (
        Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value
    )

    # Working layers

    hospital_points = "hospital_points"
    church_points = "church_points"

    # SQL-expressions

    sql_sykehus = "BYGGTYP_NBR IN (970, 719)"
    sql_church = "BYGGTYP_NBR = 671"

    # Selecting all Hospitals and making feature layer

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=bygningspunkt_pre_symbology,
        expression=sql_sykehus,
        output_name=hospital_points,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
        inverted=False,
    )

    # Selecting all Churches and making feature layer

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=bygningspunkt_pre_symbology,
        expression=sql_church,
        output_name=church_points,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
        inverted=False,
    )

    print("Finished making hospital and church layers.")

    # Finding hospital and church clusters

    hospital_clusters = "hospital_clusters"
    church_clusters = "church_clusters"

    print("Finding hospital and church clusters...")

    # Hospital

    arcpy.gapro.FindPointClusters(
        input_points=hospital_points,
        out_feature_class=hospital_clusters,
        clustering_method="DBSCAN",
        minimum_points="2",
        search_distance="200 Meters",
    )

    # Church

    arcpy.gapro.FindPointClusters(
        input_points=church_points,
        out_feature_class=church_clusters,
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
