# Importing modules
import arcpy
import time

# Importing custom files
from custom_tools import custom_arcpy
from env_setup import environment_setup

# Importing temporary files
from file_manager.n100.file_manager_buildings import Building_N100


# Importing timing decorator
from custom_tools.timing_decorator import timing_decorator


@timing_decorator("creating_points_from_polygon.py")
def main():
    """
    This function creates points from small polygons lost during aggregation, and merges
    them together with collapsed points from the tools simplify building and simplify polygon.
    """
    environment_setup.main()
    building_polygons_to_points()


@timing_decorator
def building_polygons_to_points():

    # List of building points which will be spatially joined with building polygons
    input_points = [
        f"{Building_N100.simplify_polygons___simplify_polygon___n100_building.value}_Pnt",
        f"{Building_N100.simplify_polygons___simplify_building_1___n100_building.value}_Pnt",
        f"{Building_N100.simplify_polygons___simplify_building_2___n100_building.value}_Pnt",
    ]

    # List of spatially joined points
    spatially_joined_points = []

    # Looping through each point layer in the list
    for point_layer in input_points:
        output_feature = f"{point_layer}_spatially_joined"

        arcpy.analysis.SpatialJoin(
            target_features=point_layer,
            join_features=Building_N100.data_preparation___polygons_that_are_large_enough___n100_building.value,
            out_feature_class=output_feature,
            join_operation="JOIN_ONE_TO_ONE",
            match_option="INTERSECT",
        )

        spatially_joined_points.append(output_feature)

    # Additional inputs for the merge
    additional_inputs = [
        Building_N100.data_preparation___points_created_from_small_polygons___n100_building.value,
        Building_N100.simplify_polygons___aggregated_polygons_to_points___n100_building.value,
        Building_N100.polygon_resolve_building_conflicts___final_merged_points___n100_building.value,
        Building_N100.polygon_resolve_building_conflicts___small_building_polygons_to_point___n100_building.value,
    ]
    # Complete list of inputs for the merge
    merge_inputs = spatially_joined_points + additional_inputs

    # Perform the Merge operation
    arcpy.management.Merge(
        inputs=merge_inputs,
        output=Building_N100.polygon_to_point___merged_points_final___n100_building.value,
    )
    print("Merge completed")


if __name__ == "__main__":
    main()
