# Importing custom files relative to the root path
# From custom_tools import custom_arcpy

import config
from env_setup import environment_setup
from input_data import input_n50
from input_data import input_n100

# Importing general packages
import arcpy

# Importing environment
environment_setup.setup(workspace=config.n100_building_workspace)

# Main function
def main(): 
    simplify_building_polygon()
    


def simplify_building_polygon():

    # Aggregating building polygons
    
    output_aggregate_polygon = "aggregated_polygon"

    arcpy.cartography.AggregatePolygons(
        in_features=input_n50.Grunnriss,
        out_feature_class=output_aggregate_polygon, 
        aggregation_distance="15 Meters", 
        minimum_area="3200 SquareMeters", 
        minimum_hole_size="10000 SquareMeters", 
        orthogonality_option="ORTHOGONAL", 
        barrier_features=[input_n100.VegSti], 
        out_table="grunnriss_n50_aggregated_tbl", 
        aggregate_field="BYGGTYP_NBR") 
    

    # Simplifying building polygons
    
    output_simplify_building = "simplified_building"
    
    SimplifyBuilding_model_step1_Pnt = arcpy.cartography.SimplifyBuilding(
        in_features=output_aggregate_polygon,
        out_feature_class=output_simplify_building,
        simplification_tolerance="75", 
        minimum_area="3200 SquareMeters", 
        collapsed_point_option="KEEP_COLLAPSED_POINTS")
    
    
    # Simplifying polygons

    output_simplify_polygon = "simplified_polygon"

    Grunnriss_simplify_polygon_m1_Pnt = arcpy.cartography.SimplifyPolygon(
        in_features=output_simplify_building,
        out_feature_class=output_simplify_polygon,
        algorithm="WEIGHTED_AREA",
        simplification_tolerance="15",
        minimum_area="3200 SquareMeters",
        collapsed_point_option="KEEP_COLLAPSED_POINTS")
    
    # Spatial join between simplified building polygons and original building polygons

    output_spatial_join = "spatial_joined_polygon"

    arcpy.analysis.SpatialJoin(target_features=output_simplify_polygon, 
                               join_features=input_n50.Grunnriss, 
                               out_feature_class=output_spatial_join)
    
    
    # Adding multiple fields
    arcpy.management.AddFields(
        in_table=output_spatial_join, 
        field_description=[["angle", "SHORT"], 
                           ["hierarchy", "SHORT"], 
                           ["invisibility", "SHORT"]])
    
    # Assigning values to the fields
    arcpy.management.CalculateFields(
        in_features=output_spatial_join,
        expression_type="PYTHON3", 
        fields=[["angle", "0"], 
                ["hierarchy", "0"], 
                ["invisibility", "0"]])

    # Making a copy of the feature class
    arcpy.management.CopyFeatures(output_spatial_join, "simplified_grunnriss_n50")

