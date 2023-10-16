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





def printer(): 
    print("hei")

printer()



# Main function
def main(): 
    aggregate_polygon()
    #simplify_building()
    #simplify_polygon()
    #simplify_building()


main()


#           *************************    CURRENT WORKFLOW   ****************************



# Aggregating building polygons 

def aggregate_polygon():
    arcpy.cartography.AggregatePolygons(
        in_features=input_n50.Grunnriss,
        out_feature_class="aggregated_polygons", 
        aggregation_distance="15 Meters", 
        minimum_area="3200 SquareMeters", 
        minimum_hole_size="10000 SquareMeters", 
        orthogonality_option="ORTHOGONAL", 
        barrier_features=[input_n100.VegSti, None], 
        out_table="grunnriss_n50_aggregated_tbl", 
        aggregate_field="BYGGTYP_NBR")

""""
    
# Simpliifying building polygons and generating points for polygons that are smaller than the specified minimum size

def simplify_building():

    SimplifyBuilding_model_step1_Pnt = arcpy.cartography.SimplifyBuilding(
    in_features=buildings,
    out_feature_class="simplified_buildings_1"
    simplification_tolerance="75", 
    minimum_area="3200 SquareMeters", 
    collapsed_point_option="KEEP_COLLAPSED_POINTS")

# Simpliifying polygons and generating points for polygons that are smaller than the specified minimum size

def simplify_polygon(buildings):
    Grunnriss_simplify_polygon_m1_Pnt = arcpy.cartography.SimplifyPolygon(
    in_features=buildings,
    out_feature_class="simplified_polygons",
    algorithm="WEIGHTED_AREA",
    simplification_tolerance="15",
    minimum_area="3200 SquareMeters",
    collapsed_point_option="KEEP_COLLAPSED_POINTS")

# Spatial join between simplified building polygons and original building polygons 
       
def spatial_join(): 
    arcpy.analysis.SpatialJoin(target_features="simplified_buildings_1", 
                               join_features, 
                               out_feature_class="spatial_joined_polygon_1")


# Adding multiple fields 

def add_fields(buildings): 
    arcpy.management.AddFields(
        in_table=buildings, 
        field_description=[["angle", "SHORT"], 
                           ["hierarchy", "SHORT"], 
                           ["invisibility", "SHORT"]])
    
# Assigning values to the fields 

def calculate_fields(buildings): 
    arcpy.management.CalculateFields(
        in_features=buildings,
        expression_type="PYTHON3", 
        fields=[["angle", "0"], 
                ["hierarchy", "0"], 
                ["invisibility", "0"]])

# Making a copy of the feature class 

def copy_features():
    arcpy.management.CopyFeatures(in_features, out_feature_class)




#            *************************    PARAMETERIZED FUNCTIONS   ****************************



def simplify_building_parameterized(buildings, out_feature_class, simplification_tolerance, minimum_area, collapsed_point_option):
    SimplifyBuilding_model_step1_Pnt = arcpy.cartography.SimplifyBuilding(
        in_features=buildings,
        out_feature_class=out_feature_class,
        simplification_tolerance=simplification_tolerance,
        minimum_area=minimum_area,
        collapsed_point_option=collapsed_point_option
    )

def simplify_polygon_parameterized(buildings, out_feature_class, algorithm, simplification_tolerance, minimum_area, collapsed_point_option):
    Grunnriss_simplify_polygon_m1_Pnt = arcpy.cartography.SimplifyPolygon(
        in_features=buildings,
        out_feature_class=out_feature_class,
        algorithm=algorithm,
        simplification_tolerance=simplification_tolerance,
        minimum_area=minimum_area,
        collapsed_point_option=collapsed_point_option
    )

    """