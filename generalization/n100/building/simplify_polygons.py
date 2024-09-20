# Importing modules
import arcpy

# Importing custom modules
from env_setup import environment_setup

from file_manager.n100.file_manager_buildings import Building_N100
from custom_tools.general_tools import custom_arcpy
from constants.n100_constants import N100_Values

# Importing timing decorator
from custom_tools.decorators.timing_decorator import timing_decorator


# Main function
@timing_decorator
def main():
    """
    What:
        Simplify building polygons to make them easier to read and fit around other features at a N100 map scale.
    How:
        aggregate_polygons:
            Aggregates small gaps between building polygons of the same type and fills in holes within building polygons.

        simplify_buildings_1:
            Simplifies building polygons to optimize for N100 using SimplifyBuilding. Building polygons that are under the minimum area value will be transformed to points.

        simplify_polygons:
            Simplifies building polygons to optimize for N100 using SimplifyPolygon. Building polygons that are under the minimum area value will be transformed to points.

        simplify_buildings_2:
            Simplifies building polygons to optimize for N100 using SimplifyBuilding. Building polygons that are under the minimum area value will be transformed to points.
            Does the simplify in multiple steps to get better results.

        spatial_join_polygons:
            Performs spatial join between simplified building polygons and original building polygons.
            Adds specific fields and assigns values to the building polygons, which will be useful for later in Resolve Building Conflict
    Why:
        Makes the building polygons easier to read at a N100 map scale, and potentially easier to move compared to other features.
    """

    environment_setup.main()
    aggregate_polygons()
    simplify_buildings_1()
    simplify_polygons()
    simplify_buildings_2()
    spatial_join_polygons()


@timing_decorator
def aggregate_polygons():
    """
    Aggregates small gaps between building polygons of the same type and fills in holes within building polygons.
    """
    # Aggregating building polygons (very minimal aggregation)
    print("Aggregating building polygons...")
    arcpy.cartography.AggregatePolygons(
        in_features=Building_N100.data_preparation___polygons_that_are_large_enough___n100_building.value,
        out_feature_class=Building_N100.simplify_polygons___small_gaps___n100_building.value,
        aggregation_distance=f"{N100_Values.building_polygon_aggregation_distance_m.value} Meters",
        minimum_area=f"{N100_Values.minimum_simplified_building_polygon_size_m2.value} SquareMeters",
        minimum_hole_size="10000 SquareMeters",
        orthogonality_option="ORTHOGONAL",
        barrier_features=[
            Building_N100.data_preparation___unsplit_roads___n100_building.value
        ],
        out_table=f"{Building_N100.simplify_polygons___small_gaps___n100_building.value}_table",
    )

    # Find aggregated polygons that do not intersect with "original polygons" (from data preperation)
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.data_preparation___polygons_that_are_large_enough___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.simplify_polygons___small_gaps___n100_building.value,
        output_name=Building_N100.simplify_polygons___not_intersect_aggregated_and_original_polygon___n100_building.value,
        inverted=True,
    )

    # These are transformed to points because they are too small and have been removed by the aggregate polygons minimum area treshold
    arcpy.management.FeatureToPoint(
        in_features=Building_N100.simplify_polygons___not_intersect_aggregated_and_original_polygon___n100_building.value,
        out_feature_class=Building_N100.simplify_polygons___aggregated_polygons_to_points___n100_building.value,
    )


# First round of simplify buildings
@timing_decorator
def simplify_buildings_1():
    """
    Simplifies building polygons to optimize for N100 using SimplifyBuilding. Building polygons that are under the minimum area value will be transformed to points.
    """

    print("Simplifying building polygons round 1...")

    arcpy.cartography.SimplifyBuilding(
        in_features=Building_N100.simplify_polygons___small_gaps___n100_building.value,
        out_feature_class=Building_N100.simplify_polygons___simplify_building_1___n100_building.value,
        simplification_tolerance=f"{N100_Values.simplify_building_tolerance_m.value} Meters",
        minimum_area=f"{N100_Values.minimum_simplified_building_polygon_size_m2.value} SquareMeters",
        collapsed_point_option="KEEP_COLLAPSED_POINTS",  # Name of points will be the same as output, but with `Pnt` at the end
    )


# Simplifying polygons (runs once)
@timing_decorator
def simplify_polygons():
    """
    Simplifies building polygons to optimize for N100 using SimplifyPolygon. Building polygons that are under the minimum area value will be transformed to points.
    """

    print("Simplifying polygons...")

    arcpy.cartography.SimplifyPolygon(
        in_features=Building_N100.simplify_polygons___simplify_building_1___n100_building.value,
        out_feature_class=Building_N100.simplify_polygons___simplify_polygon___n100_building.value,
        algorithm="WEIGHTED_AREA",
        tolerance=f"{N100_Values.simplify_polygon_tolerance_m.value} Meters",
        minimum_area=f"{N100_Values.minimum_simplified_building_polygon_size_m2.value} SquareMeters",
        collapsed_point_option="KEEP_COLLAPSED_POINTS",  # Name of points will be the same as output, but with `Pnt` at the end
    )


# Second round of simplify buildings
@timing_decorator
def simplify_buildings_2():
    """
    Simplifies building polygons to optimize for N100 using SimplifyBuilding. Building polygons that are under the minimum area value will be transformed to points.
    Does the simplify in multiple steps to get better results.
    """
    print("Simplifying building polygons round 2...")

    arcpy.cartography.SimplifyBuilding(
        in_features=Building_N100.simplify_polygons___simplify_building_1___n100_building.value,
        out_feature_class=Building_N100.simplify_polygons___simplify_building_2___n100_building.value,
        simplification_tolerance=f"{N100_Values.simplify_building_tolerance_m.value} Meters",
        minimum_area=f"{N100_Values.minimum_simplified_building_polygon_size_m2.value} SquareMeters",
        collapsed_point_option="KEEP_COLLAPSED_POINTS",  # Name of points will be the same as output, but with `Pnt` at the end
    )


# Spatial join and adding fields to polygons
@timing_decorator
def spatial_join_polygons():
    """
    Performs spatial join between simplified building polygons and original building polygons.
    Adds specific fields and assigns values to the building polygons, which will be useful for later in Resolve Building Conflict
    """
    # Spatial join between simplified building polygons and original building polygons
    print("Performing spatial join...")

    arcpy.analysis.SpatialJoin(
        target_features=Building_N100.simplify_polygons___simplify_building_2___n100_building.value,
        join_features=Building_N100.data_selection___building_polygon_n50_input_data___n100_building.value,
        out_feature_class=Building_N100.simplify_polygons___spatial_join_polygons___n100_building.value,
    )


if __name__ == "__main__":
    main()
