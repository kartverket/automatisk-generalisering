# Importing modules
import arcpy
import time

# Importing custom modules
import config
from custom_tools import custom_arcpy
from env_setup import environment_setup
from input_data import input_n50
from input_data import input_n100
from file_manager.n100.file_manager_buildings import Building_N100

# Importing environment
environment_setup.general_setup()


# Main function
def main():
    """
    # Summary:
    Aggregates and simplifies building polygons, minimizing detailed parts of the building.

    # Details:
    - Hospitals are selected based on 'BYGGTYP_NBR' values 970 and 719.
    - Churches are selected based on 'BYGGTYP_NBR' value 671.

    # Parameters
     The tool FindPointClusters have a search distance of 200 meters and minimum points of 2.

    """
    # Start timing
    start_time = time.time()

    simplify_building_polygon()

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

    print(f"create_simplified_building_polygons took {time_str} to complete.")


# Simplify building polygons and create points where buildings are too small
def simplify_building_polygon():
    """
    # Summary:
    Finds hospital and church clusters.
    A cluster is defined as two or more points that are closer together than 200 meters.

    # Details:
    - Hospitals are selected based on 'BYGGTYP_NBR' values 970 and 719.
    - Churches are selected based on 'BYGGTYP_NBR' value 671.

    # Parameters
     The tool FindPointClusters have a search distance of 200 meters and minimum points of 2.

    """
    # Aggregating building polygons

    print("Aggregating building polygons...")
    arcpy.cartography.AggregatePolygons(
        in_features=Building_N100.selecting_grunnriss_for_generalization__large_enough_grunnriss__n100.value,
        out_feature_class=Building_N100.grunnriss_to_point__aggregated_polygon__n100.value,
        aggregation_distance="15 Meters",
        minimum_area="3200 SquareMeters",
        minimum_hole_size="10000 SquareMeters",
        orthogonality_option="ORTHOGONAL",
        barrier_features=[
            Building_N100.preperation_veg_sti__unsplit_veg_sti__n100.value
        ],
        out_table=f"{Building_N100.grunnriss_to_point__aggregated_polygon__n100.value}_table",
        aggregate_field="BYGGTYP_NBR",
    )
    print("Aggregating building polygons completed.")

    # Simplifying building polygons

    print("Simplifying building polygons...")

    arcpy.cartography.SimplifyBuilding(
        in_features=Building_N100.grunnriss_to_point__aggregated_polygon__n100.value,
        out_feature_class=Building_N100.simplify_building_polygons__simplified_building_1__n100.value,
        simplification_tolerance="75",
        minimum_area="3200 SquareMeters",
        collapsed_point_option="KEEP_COLLAPSED_POINTS",
    )
    print("Simplifying building polygons completed.")

    # Creating points to permanently store auto generated points from simplified building polygons to a specified path
    auto_generated_points_1 = f"{Building_N100.simplify_building_polygons__simplified_building_1__n100.value}_Pnt"

    arcpy.management.CopyFeatures(
        auto_generated_points_1,
        Building_N100.grunnriss_to_point__simplified_building_points_simplified_building_1__n100.value,
    )
    arcpy.management.Delete(auto_generated_points_1)

    # Simplifying polygons

    print("Simplifying polygons...")

    arcpy.cartography.SimplifyPolygon(
        in_features=Building_N100.simplify_building_polygons__simplified_building_1__n100.value,
        out_feature_class=Building_N100.simplify_building_polygons__simplified_polygon__n100.value,
        algorithm="WEIGHTED_AREA",
        tolerance="15",
        minimum_area="3200 SquareMeters",
        collapsed_point_option="KEEP_COLLAPSED_POINTS",
    )
    print("Simplifying polygons completed.")

    # Creating points to permanently store auto generated points from simplified polygon to a specified path
    auto_generated_points_2 = f"{Building_N100.simplify_building_polygons__simplified_polygon__n100.value}_Pnt"

    arcpy.management.CopyFeatures(
        auto_generated_points_2,
        Building_N100.grunnriss_to_point__collapsed_points_simplified_polygon__n100.value,
    )
    arcpy.management.Delete(auto_generated_points_2)

    # Simplifying building polygons

    print("Simplifying building polygons...")

    arcpy.cartography.SimplifyBuilding(
        in_features=Building_N100.simplify_building_polygons__simplified_building_1__n100.value,
        out_feature_class=Building_N100.simplify_building_polygons__simplified_building_2__n100.value,
        simplification_tolerance="75",
        minimum_area="3200 SquareMeters",
        collapsed_point_option="KEEP_COLLAPSED_POINTS",
    )
    print("Simplifying building polygons completed.")

    # Creating points to permanently store auto generated points from simplified polygon to a specified path
    auto_generated_points_3 = f"{Building_N100.simplify_building_polygons__simplified_building_2__n100.value}_Pnt"

    arcpy.management.CopyFeatures(
        auto_generated_points_3,
        Building_N100.grunnriss_to_point__simplified_building_points_simplified_building_2__n100.value,
    )
    arcpy.management.Delete(auto_generated_points_3)

    # Spatial join between simplified building polygons and original building polygons

    print("Performing spatial join...")

    arcpy.analysis.SpatialJoin(
        target_features=Building_N100.simplify_building_polygons__simplified_polygon__n100.value,
        join_features=input_n50.Grunnriss,
        out_feature_class=Building_N100.simplify_building_polygons__spatial_joined_polygon__n100.value,
    )
    print("Spatial join completed.")

    # Adding multiple fields

    print("Adding fields...")
    arcpy.management.AddFields(
        in_table=Building_N100.simplify_building_polygons__spatial_joined_polygon__n100.value,
        field_description=[
            ["angle", "SHORT"],
            ["hierarchy", "SHORT"],
            ["invisibility", "SHORT"],
        ],
    )
    print("Adding fields completed.")

    # Assigning values to the fields

    print("Assigning values to fields...")
    arcpy.management.CalculateFields(
        in_table=Building_N100.simplify_building_polygons__spatial_joined_polygon__n100.value,
        expression_type="PYTHON3",
        fields=[["angle", "0"], ["hierarchy", "0"], ["invisibility", "0"]],
    )
    print("Assigning values to fields completed.")

    # Making a copy of the feature class

    print("Making a copy of the feature class...")
    arcpy.management.CopyFeatures(
        Building_N100.simplify_building_polygons__spatial_joined_polygon__n100.value,
        Building_N100.simplify_building_polygons__simplified_grunnriss__n100.value,
    )
    print("Copy completed.")


if __name__ == "__main__":
    main()
