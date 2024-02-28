# Importing modules
import arcpy
import time

# Importing custom files
from custom_tools import custom_arcpy
from env_setup import environment_setup

# Importing temporary files
from file_manager.n100.file_manager_buildings import Building_N100

# Importing environment
environment_setup.main()

# Importing timing decorator
from custom_tools.timing_decorator import timing_decorator


@timing_decorator("creating_points_from_polygon.py")
def main():
    """
    This function creates points from small grunnriss lost during aggregation, and merges
    them together with collapsed points from the tools simplify building and simplify polygon.
    """
    # Start timing
    start_time = time.time()

    grunnriss_to_point()

    # End timing
    end_time = time.time()

    # Calculate elapsed time
    elapsed_time = end_time - start_time

    # Convert to hours, minutes, and seconds
    hours, remainder = divmod(elapsed_time, 3600)
    minutes, seconds = divmod(remainder, 60)

    # Format as string
    time_str = "{:02} hours, {:02} minutes, {:.2f} seconds".format(
        int(hours), int(minutes), seconds
    )

    print(f"create_points_from_polygon took {time_str} to complete.")


#######################################################################################################################################################


@timing_decorator
def grunnriss_to_point():
    """
    Summary:
        Transforms building polygons that are too small to points

    """

    custom_arcpy.select_location_and_make_feature_layer(
        input_layer=Building_N100.selecting_grunnriss_for_generalization__large_enough_grunnriss__n100.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.aggregate_polygons__fill_hole__n100.value,
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
        Building_N100.simplify_polygons__points__n100.value,
        Building_N100.simplify_buildings_1__points__n100.value,
        Building_N100.simplify_buildings_2__points__n100.value,
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
        Building_N100.merging_invisible_intersecting_points__final__n100.value,
    ]
    # Complete list of inputs for the merge
    merge_inputs = additional_inputs + output_paths

    # Perform the Merge operation
    arcpy.management.Merge(
        inputs=merge_inputs,
        output=Building_N100.grunnriss_to_point__merged_points_created_from_grunnriss__n100.value,
    )
    print("Merge completed")


if __name__ == "__main__":
    main()
