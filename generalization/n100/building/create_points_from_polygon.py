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
environment_setup.setup(workspace=config.n100_building_workspace)


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
    print("Creating intersected feature layer using Select By Location and Make Feature Layer...")

    custom_arcpy.select_location_and_make_feature_layer(
        input_layer=TemporaryFiles.grunnriss_selection_n50.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=TemporaryFiles.output_aggregate_polygon,
        output_name=intersect_aggregated_and_original,
        inverted=True)
    
    print("Custom tool completed.")

    # 2: Feature to point 
    feature_to_point = "feature_to_point"
    print("Converting selected features to points using Feature To Point...")

    arcpy.management.FeatureToPoint(
        in_features=intersect_aggregated_and_original, 
        out_feature_class=feature_to_point)

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
    all_point_layers = [small_grunnriss_points, grunnriss_sykehus_kirke_points, points_from_aggregation, n50_points] + output_spatial_joins
    
    print("Preparing for merge...")

    output_merge = "merged_points"

    # 5: Merging points together into one feature class - total 6 point layers 
    arcpy.management.Merge(
        inputs=all_point_layers, 
        output=output_merge)
    
    print("Merge completed.")

    # Copying the layer 
    merged_points_final = TemporaryFiles.merged_points_final.value
    print("Copying the merged layer...")

    arcpy.management.CopyFeatures(
        in_features=output_merge,               
        out_feature_class=merged_points_final)

    print("Copy completed.")

    

  
