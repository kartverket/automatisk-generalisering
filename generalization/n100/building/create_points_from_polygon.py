import arcpy

# Importing custom files relative to the root path
import config
from custom_tools import custom_arcpy
from env_setup import environment_setup
from input_data import input_n50
from input_data import input_n100

# Importing 

from file_manager.n100.file_manager_buildings import TemporaryFiles

# Importing environment
environment_setup.setup(workspace=config.n100_building_workspace)


# Main function
def main(): 
    create_points_from_polygon()


def create_points_from_polygon(): 

    # Custom: Select By Attribute and Make Feature Layer 

    select_location_make_feature_layer_aggregated_polygon = TemporaryFiles.select_location_make_feature_layer_aggregated_polygon.value

    custom_arcpy.select_location_and_make_feature_layer(
        input_layer=TemporaryFiles.grunnriss_selection_n50.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=TemporaryFiles.output_aggregate_polygon,
        output_name=select_location_make_feature_layer_aggregated_polygon,
        invert_spatial_relationship=True)
    
    feature_to_point = TemporaryFiles.feature_to_point.value
    
    # Feature to point 

    arcpy.management.FeatureToPoint(
        in_features=TemporaryFiles.select_location_make_feature_layer_aggregated_polygon.value, 
        out_feature_class=feature_to_point)

    # Spatial join 
    
    point_sets = [
    TemporaryFiles.output_collapsed_points_simplified_building.value,
    TemporaryFiles.output_collapsed_points_simplified_polygon,
    TemporaryFiles.output_collapsed_points_simplified_building2.value,
    ]

    output_spatial_joins = []

    grunnriss_selection_n50 = TemporaryFiles.grunnriss_selection_n50.value

    for index, point_set in enumerate(point_sets):
        output_spatial_join = f"spatial_join_points_{index + 1}"
        
        arcpy.analysis.SpatialJoin(
            target_features=point_set,  
            join_features=grunnriss_selection_n50,  
            out_feature_class=output_spatial_join,
            join_operation="JOIN_ONE_TO_ONE",
            match_option="INTERSECT",
        )

        output_spatial_joins.append(output_spatial_join)
    
    grunnriss_sykehus_kirke_points = TemporaryFiles.kirke_sykehus_points_n50.value                                               
    points_from_aggregation = TemporaryFiles.feature_to_point.value                                                

    input_merge = [grunnriss_sykehus_kirke_points, points_from_aggregation] + output_spatial_joins
    
    output_merge = TemporaryFiles.merged.value

    arcpy.management.Merge(
        inputs=input_merge, 
        output=output_merge)
    
    final_merge = TemporaryFiles.final_merge.value
    
    arcpy.management.CopyFeatures(
        in_features=output_merge,               
        out_feature_class=final_merge)
    

  
