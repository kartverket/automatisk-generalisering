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
    creating_points_aggregate_polygon()


def create_points_from_polygon(): 

    # Spatial join 

    # Define input and output paths
    
    point_sets = [
    TemporaryFiles.output_collapsed_points_simplified_building.value,
    TemporaryFiles.output_collapsed_points_simplified_polygon,
    TemporaryFiles.output_collapsed_points_simplified_building2.value,
    ]

    output_spatial_joins = []

    polygon_layer = TemporaryFiles.grunnriss_selection_n50.value

    for index, point_set in enumerate(point_sets):
        output_spatial_join = f"spatial_join_points_{index + 1}"
        
        arcpy.analysis.SpatialJoin(
            target_features=point_set,  
            join_features=polygon_layer,  
            out_feature_class=output_spatial_join,
            join_operation="JOIN_ONE_TO_ONE",
            match_option="INTERSECT",
        )

        output_spatial_joins.append(output_spatial_join)

    input_merge = []
    
    polygons = None                                                 #Fyll inn
    points = None                                                   #Fyll inn

    input_merge = [polygons, points] + output_spatial_joins
    output_merge = "merged_features" 

    arcpy.management.Merge(
        inputs=input_merge, 
        output=output_merge)
    



def creating_points_aggregate_polygon(): 


