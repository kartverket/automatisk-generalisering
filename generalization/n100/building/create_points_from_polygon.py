import arcpy

# Importing custom files relative to the root path
import config
from custom_tools import custom_arcpy
from env_setup import environment_setup
from input_data import input_n50
from input_data import input_n100

# Importing temporary files
from file_manager.n100.file_manager_buildings import TemporaryFiles

# Importing environment
environment_setup.general_setup()


# Main function
def main():
    create_points_from_polygon()



# Function that creates one feature class of all points
def create_points_from_polygon():

    """

    Creates a feature class of points by performing the following steps:

    1. Utilizes a custom tool to select features by location and make a feature layer that intersects
    the aggregated and original building polygons.
    2. Converts the selected features to points using the 'Feature To Point' tool.
    3. Conducts a spatial join operation between multiple point layers and the 'grunnriss' layer to retrieve
    attribute values based on their spatial relationships.
    4. Merges 5 point layers into a single feature class using the 'Merge' tool.
    5. Copies the final merged feature class

    """    

    # 1: Custom tool: Select By Location and Make Feature Layer
    intersect_aggregated_and_original = "intersect_aggregated_and_original"
    print(
        "Creating intersected feature layer using Select By Location and Make Feature Layer..."
    )

    custom_arcpy.select_location_and_make_feature_layer(
        input_layer=TemporaryFiles.grunnriss_selection_n50.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=TemporaryFiles.output_aggregate_polygon.value,
        output_name=intersect_aggregated_and_original,
        inverted=True,
    )

    print("Custom tool completed.")

    # 2: Feature to point
    feature_to_point = "feature_to_point"
    print("Converting selected features to points using Feature To Point...")

    arcpy.management.FeatureToPoint(
        in_features=intersect_aggregated_and_original,
        out_feature_class=feature_to_point,
    )

    print("Feature to Point completed.")

    # 3: Spatial join
    simplified_building_points = [
        TemporaryFiles.output_collapsed_points_simplified_building.value,
        TemporaryFiles.output_collapsed_points_simplified_polygon.value,
        TemporaryFiles.output_collapsed_points_simplified_building2.value,
    ]
    print("Performing spatial joins...")

    # List of all point layers that were spatially joined
    output_spatial_joins = []

    for index, point_layer in enumerate(simplified_building_points):
        output_spatial_join = f"spatial_join_points_{index + 1}"

        arcpy.analysis.SpatialJoin(
            target_features=point_layer,
            join_features=TemporaryFiles.grunnriss_selection_n50.value,
            out_feature_class=output_spatial_join,
            join_operation="JOIN_ONE_TO_ONE",
            match_option="INTERSECT",
        )

        output_spatial_joins.append(output_spatial_join)

    print("Spatial joins completed.")

    
    # 4: Preparing for Merge - collecting layers
    small_grunnriss_points = TemporaryFiles.small_grunnriss_points_n50.value
    grunnriss_sykehus_kirke_points = TemporaryFiles.kirke_sykehus_points_n50.value
    points_from_aggregation = feature_to_point
    n50_points = input_n50.BygningsPunkt

    # List of all point layers to be merged
    all_point_layers = [
        small_grunnriss_points,
        grunnriss_sykehus_kirke_points,
        points_from_aggregation,
        n50_points,
    ] + output_spatial_joins

    print("Preparing for merge...")

    output_merge = "merged_points"

    # 5: Merging points together into one feature class - total 6 point layers
    arcpy.management.Merge(inputs=all_point_layers, output=output_merge)

    print("Merge completed.")

    # Copying the layer
    merged_points_final = TemporaryFiles.merged_points_final.value
    print("Copying the merged layer...")

    arcpy.management.CopyFeatures(
        in_features=output_merge, out_feature_class=merged_points_final
    )

    print("Copy completed.")

    # 4: Finding hospital and church clusters

    # Input layer 


def test():

    # Input layers 
    
    bygningspunkt_pre_symbology = TemporaryFiles.bygningspunkt_pre_symbology.value

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
        inverted=False)
    
    # Selecting all Churches and making feature layer
    
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=bygningspunkt_pre_symbology,
        expression=sql_church,
        output_name=church_points,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
        inverted=False)
    
    # Finding hospital and church clusters

    hospital_clusters = "hospital_clusters"
    church_clusters = "church_clusters"
    
    # Hospital

    arcpy.gapro.FindPointClusters(
        input_points=hospital_points, 
        out_feature_class=hospital_clusters, 
        clustering_method="DBSCAN", 
        minimum_points="2", 
        search_distance="200 Meters")
    
    # Church 

    arcpy.gapro.FindPointClusters(
        input_points=church_points, 
        out_feature_class=church_clusters, 
        clustering_method="DBSCAN", 
        minimum_points="2", 
        search_distance="200 Meters")
    
    """
    
    # Join CLUSTER_ID field to hospital and church feature classes

    # Hospital

    arcpy.management.JoinField(
        in_data=hospital_points, 
        in_field="OBJECTID", 
        join_table=hospital_clusters, 
        join_field="OBJECTID", 
        fields="CLUSTER_ID")
    
    # Church 
    
    arcpy.management.JoinField(
        in_data=church_points, 
        in_field="OBJECTID", 
        join_table=church_clusters, 
        join_field="OBJECTID", 
        fields="CLUSTER_ID")


    # Create an empty dictionary to store cluster information
    cluster_info_hospital = {}

    field_name = ["CLUSTER_ID"]

    with arcpy.da.SearchCursor(hospital_points, field_name) as cursor:
        for row in cursor:
            cluster_id = row[0]  # Access the first (and only) field in the list

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

    # Picking out hospital-clusters of 2
    # Picking out hospital-clusters of 3 or more
        
    hospital_clusters_of_2_list = []
    hospital_clusters_of_3_or_more_list = []

    for cluster_id in cluster_info_hospital:
        if cluster_info_hospital[cluster_id] == 2: 
            hospital_clusters_of_2_list.append(cluster_id)
        elif cluster_info_hospital[cluster_id] >= 3: 
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


    # Picking out church-clusters of 2
    # Picking out church-clusters of 3 or more

    church_clusters_of_2_list = []
    church_clusters_of_3_or_more_list = []
   
    for cluster_id in cluster_info_church: 
        if cluster_info_church[cluster_id] == 2: 
            church_clusters_of_2_list.append(cluster_id)
        elif cluster_info_church[cluster_id] >= 3: 
            church_clusters_of_3_or_more_list.append(cluster_id)


    ######################## Minimum Bounding Geometry tool - for clusters over 2 points #########################
   
    # Hospital 

    hospital_clusters_of_more_than_3 = "hospital_clusters_of_more_than_3"

    custom_arcpy.select_attribute_and_make_feature_layer(
        input_layer=hospital_points,
        expression=f"CLUSTER_ID in {tuple(hospital_clusters_of_3_or_more_list)}",
        output_name=hospital_clusters_of_more_than_3,
        selection_type="NEW_SELECTION",
        inverted=False)
    
    hospital_clusters_output_minimum_bounding_geometry = "hospital_clusters_output_minimum_bounding_geometry"

    arcpy.management.MinimumBoundingGeometry(
        in_features=hospital_clusters_of_more_than_3, 
        out_feature_class=hospital_clusters_output_minimum_bounding_geometry, 
        geometry_type="RECTANGLE_BY_AREA", 
        group_option="LIST",
        group_field="CLUSTER_ID")
    
    hospital_feature_to_point = "hospital_feature_to_point"
    
    arcpy.management.FeatureToPoint(
        in_features=hospital_clusters_output_minimum_bounding_geometry, 
        out_feature_class=hospital_feature_to_point)


    # Find point closest to this point 

    arcpy.analysis.Near(
        in_features=hospital_feature_to_point, # points from polygon 
        near_features=hospital_points, # all hospital points 
        search_radius=None)
    
    field_near_fid = ["NEAR_FID"]
    near_fid_list = []

    with arcpy.da.SearchCursor(hospital_feature_to_point, field_near_fid) as cursor:
        for row in cursor:
            near_fid = row[field_near_fid]
            near_fid_list.append(near_fid)

    SQL_expression = "OBJECTID IN (" + ",".join(map(str, near_fid_list)) + ") OR CLUSTER_ID < 0"
    selected_hospitals = "selected_hospitals"

    custom_arcpy.select_attribute_and_make_feature_layer(
        input_layer=hospital_points,
        expression=SQL_expression,
        output_name=selected_hospitals,
        selection_type="NEW_SELECTION",
        inverted=False)
    



    # Church 

    church_clusters_of_more_than_3 = "church_clusters_of_more_than_3"

    custom_arcpy.select_attribute_and_make_feature_layer(
        input_layer=hospital_points,
        expression=f"CLUSTER_ID in {tuple(church_clusters_of_3_or_more_list)}",
        output_name=church_clusters_of_more_than_3,
        selection_type="NEW_SELECTION",
        inverted=False)
    
    church_clusters_output_minimum_bounding_geometry = "church_clusters_output_minimum_bounding_geometry"

    arcpy.management.MinimumBoundingGeometry(
        in_features=church_clusters_of_more_than_3, 
        out_feature_class=church_clusters_output_minimum_bounding_geometry, 
        geometry_type="RECTANGLE_BY_AREA", 
        group_option="LIST",
        group_field="CLUSTER_ID")
    
    church_feature_to_point = "church_feature_to_point"
    
    arcpy.management.FeatureToPoint(
        in_features=church_clusters_output_minimum_bounding_geometry, 
        out_feature_class=church_feature_to_point)

    # Find point closest to this point 

    arcpy.analysis.Near(
        in_features, 
        near_features, 
        {search_radius}, 
        {location}, 
        {angle}, 
        {method}, 
        {field_names}, 
        {distance_unit})
    



    # Near tool - for clusters with 2 points 
"""
test()