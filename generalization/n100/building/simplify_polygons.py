# Importing modules
import arcpy

# Importing custom modules
from env_setup import environment_setup
from input_data import input_n50
from file_manager.n100.file_manager_buildings import Building_N100
from custom_tools import custom_arcpy

# Importing timing decorator
from custom_tools.timing_decorator import timing_decorator


# Main function
@timing_decorator("simplify_polygons.py")
def main():
    """
    Summary:
        This script aggregates and simplifies building polygons, minimizing detailed parts of the building.

    Details:
        1. `aggregate_building_polygons`:
            Selects hospitals and churches from the input point feature class.

        2. `simplify_buildings`:
            Finds clusters in the hospital and church layers.

        3. `simplify_polygons`:
            Reduces clusters to one point for each cluster.

        3. `joining_and_adding_fields`:
            Reduces clusters to one point for each cluster.
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
    Summary:
        Aggregates small gaps between building polygons of the same type and fills in holes within building polygons.

    Details:
    - the AggregatePolygon tool is used

    Parameters:
    - Aggregation distance is **`4 Meters`**
    - Minimum Area is **`3200 Square Meters`**
    - Minimum Hole Size is **`10 000 Square Meters`**
    """
    # Aggregating building polygons (very minimal aggregation)
    print("Aggregating building polygons...")
    arcpy.cartography.AggregatePolygons(
        in_features=Building_N100.data_preparation___polygons_that_are_large_enough___n100_building.value,
        out_feature_class=Building_N100.simplify_polygons___small_gaps___n100_building.value,
        aggregation_distance="4",
        minimum_area="3200 SquareMeters",
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
    Summary:
        Simplifies building polygons to optimize for a 1:100,000 map scale. Building polygons that are under the minimum area value will be transformed to points.

    Details:
        - The SimplifyBuilding tool is employed to reduce the complexity of building polygons, specifically tailored for the 1:100,000 map scale.
            It is used to decrease the number of vertices in building polygons, aiming to maintain essential features, but removing details
            for a smoother representation at the 1:100,000 scale.

    Parameters:
        - Simplification Tolerance is **`75 Meters`**: Controls the distance at which vertices are removed during the simplification process.
        - Minimum Area is **`3200 Square Meters`**: Specifies the minimum area a simplified building polygon should have.
        - Minimum Hole Size is **`10,000 Square Meters`**: Sets the minimum size for holes within the building polygons to be retained.
    """

    print("Simplifying building polygons round 1...")

    arcpy.cartography.SimplifyBuilding(
        in_features=Building_N100.simplify_polygons___small_gaps___n100_building.value,
        out_feature_class=Building_N100.simplify_polygons___simplify_building_1___n100_building.value,
        simplification_tolerance="75",
        minimum_area="3200 SquareMeters",
        collapsed_point_option="KEEP_COLLAPSED_POINTS",  # Name of points will be the same as output, but with `Pnt` at the end
    )


# Simplifying polygons (runs once)
@timing_decorator
def simplify_polygons():
    """
    Summary:
        Reduces the complexity of building polygons even more to optimize for a 1:100,000 map scale,
        where small details of buildings may be perrceived as background noise.

    Details:
        - This function simplifies the input building polygons even more to enhance visualization at the 1:100,000 map scale.
        It reduces the number of vertices. Auto-generated points from the simplified polygons are also saved separately.

    Parameters:
        - Tolerance is **`15`**: It controls the simplification distance.
        - Minimum Area is **`3200 Square Meters`**: Specifies the minimum area a simplified building polygon should have.
    """

    print("Simplifying polygons...")

    arcpy.cartography.SimplifyPolygon(
        in_features=Building_N100.simplify_polygons___simplify_building_1___n100_building.value,
        out_feature_class=Building_N100.simplify_polygons___simplify_polygon___n100_building.value,
        algorithm="WEIGHTED_AREA",
        tolerance="15",
        minimum_area="3200 SquareMeters",
        collapsed_point_option="KEEP_COLLAPSED_POINTS",  # Name of points will be the same as output, but with `Pnt` at the end
    )


# Second round of simplify buildings
@timing_decorator
def simplify_buildings_2():
    """
    Summary:
        Simplifies building polygons to optimize for a 1:100,000 map scale. Building polygons that are under the minimum area value will be transformed to points.

    Details:
        - The SimplifyBuilding tool is employed to reduce the complexity of building polygons, specifically tailored for the 1:100,000 map scale.
            It is used to decrease the number of vertices in building polygons, aiming to maintain essential features, but removing details
            for a smoother representation at the 1:100,000 scale.

    Parameters:
        - Simplification Tolerance is **`75 Meters`**: Controls the distance at which vertices are removed during the simplification process.
        - Minimum Area is **`3200 Square Meters`**: Specifies the minimum area a simplified building polygon should have.
        - Minimum Hole Size is **`10,000 Square Meters`**: Sets the minimum size for holes within the building polygons to be retained.
    """
    print("Simplifying building polygons round 2...")

    arcpy.cartography.SimplifyBuilding(
        in_features=Building_N100.simplify_polygons___simplify_building_1___n100_building.value,
        out_feature_class=Building_N100.simplify_polygons___simplify_building_2___n100_building.value,
        simplification_tolerance="75",
        minimum_area="3200 SquareMeters",
        collapsed_point_option="KEEP_COLLAPSED_POINTS",  # Name of points will be the same as output, but with `Pnt` at the end
    )


# Spatial join and adding fields to polygons
@timing_decorator
def spatial_join_polygons():
    """
    Summary:
        Performs spatial join between simplified building polygons and original building polygons.
        Adds specific fields and assigns values to the building polygons, which will be useful for later in Resolve Building Conflict
    """
    # Spatial join between simplified building polygons and original building polygons
    print("Performing spatial join...")

    arcpy.analysis.SpatialJoin(
        target_features=Building_N100.simplify_polygons___simplify_building_2___n100_building.value,
        join_features=input_n50.Grunnriss,
        out_feature_class=Building_N100.simplify_polygons___spatial_join_polygons___n100_building.value,
    )


if __name__ == "__main__":
    main()
