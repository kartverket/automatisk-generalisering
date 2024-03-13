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
    This function creates points from small grunnriss lost during aggregation, and merges
    them together with collapsed points from the tools simplify building and simplify polygon.
    """
    environment_setup.main()
    grunnriss_to_point()


@timing_decorator
def grunnriss_to_point():
    """
    Summary:
        Transforms building polygons that are too small to points

    """

    custom_arcpy.select_location_and_make_feature_layer(
        input_layer=Building_N100.data_preparation___large_enough_polygon___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.simplify_polygons___small_gaps___n100_building.value,
        output_name=Building_N100.polygon_to_point___intersect_aggregated_and_original___n100_building.value,
        inverted=True,
    )

    arcpy.management.FeatureToPoint(
        in_features=Building_N100.polygon_to_point___intersect_aggregated_and_original___n100_building.value,
        out_feature_class=Building_N100.polygon_to_point___polygons_to_point___n100_building.value,
    )

    # Base output which the for loop through for output creation
    base_output_path = (
        Building_N100.polygon_to_point___spatial_join_points___n100_building.value
    )

    # List of input features which will be spatially joined
    input_features = [
        Building_N100.simplify_polygons___points___n100_building.value,
        Building_N100.simplify_polygons___simplify_building_1_points___n100_building.value,
        Building_N100.simplify_polygons___simplify_building_2_points___n100_building.value,
    ]

    #  Feature with the field information which will be used for spatial join
    join_features = (
        Building_N100.data_preparation___large_enough_polygon___n100_building.value
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

    # Additional inputs for the merge
    additional_inputs = [
        Building_N100.data_preparation___points_created_from_small_polygon___n100_building.value,
        Building_N100.data_preparation___church_points_from_polygon___n100_building.value,
        Building_N100.polygon_to_point___polygons_to_point___n100_building.value,
        Building_N100.polygon_propogate_displacement___final_merged_points___n100_building.value,
        Building_N100.polygon_propogate_displacement___small_building_polygons_to_point___n100_building.value,
    ]
    # Complete list of inputs for the merge
    merge_inputs = additional_inputs + output_paths

    # Perform the Merge operation
    arcpy.management.Merge(
        inputs=merge_inputs,
        output=Building_N100.polygon_to_point___merged_points_final___n100_building.value,
    )
    print("Merge completed")


if __name__ == "__main__":
    main()
