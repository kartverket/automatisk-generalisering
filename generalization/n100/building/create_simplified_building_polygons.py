# Importing modules
import arcpy
from timer import Timer

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
    # Aggregating building polygons

    print("Aggregating building polygons...")
    arcpy.cartography.AggregatePolygons(
        in_features=Building_N100.selecting_grunnriss_for_generalization__large_enough_grunnriss__n100.value,
        out_feature_class=Building_N100.aggregate_polygons__fill_hole__n100.value,
        aggregation_distance="4",
        minimum_area="3200 SquareMeters",
        minimum_hole_size="10000 SquareMeters",
        orthogonality_option="ORTHOGONAL",
        barrier_features=[
            Building_N100.preperation_veg_sti__unsplit_veg_sti__n100.value
        ],
        out_table=f"{Building_N100.aggregate_polygons__fill_hole__n100.value}_table",
        aggregate_field="BYGGTYP_NBR",
    )


# Simplifying building polygons
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

    print("Simplifying building polygons...")

    arcpy.cartography.SimplifyBuilding(
        in_features=Building_N100.aggregate_polygons__fill_hole__n100.value,
        out_feature_class=Building_N100.simplify_buildings_1_simplifying__n100.value,
        simplification_tolerance="75",
        minimum_area="3200 SquareMeters",
        collapsed_point_option="KEEP_COLLAPSED_POINTS",
    )

    # Creating points to permanently store auto generated points from simplified building polygons to a specified path
    auto_generated_points_1 = (
        f"{Building_N100.simplify_buildings_1_simplifying__n100.value}_Pnt"
    )

    arcpy.management.CopyFeatures(
        auto_generated_points_1,
        Building_N100.simplify_buildings_1__points__n100.value,
    )
    arcpy.management.Delete(auto_generated_points_1)


# Simplifying polygons
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
        in_features=Building_N100.simplify_buildings_1_simplifying__n100.value,
        out_feature_class=Building_N100.simplify_polygons__simplifying__n100.value,
        algorithm="WEIGHTED_AREA",
        tolerance="15",
        minimum_area="3200 SquareMeters",
        collapsed_point_option="KEEP_COLLAPSED_POINTS",
    )

    # Creating points to permanently store auto generated points from simplified polygon to a specified path
    auto_generated_points_2 = (
        f"{Building_N100.simplify_polygons__simplifying__n100.value}_Pnt"
    )

    arcpy.management.CopyFeatures(
        auto_generated_points_2,
        Building_N100.simplify_polygons__points__n100.value,
    )
    arcpy.management.Delete(auto_generated_points_2)

    # Simplifying building polygons


# Second round of simplify buildings
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

    arcpy.cartography.SimplifyBuilding(
        in_features=Building_N100.simplify_buildings_1_simplifying__n100.value,
        out_feature_class=Building_N100.simplify_buildings_2_simplifying__n100.value,
        simplification_tolerance="75",
        minimum_area="3200 SquareMeters",
        collapsed_point_option="KEEP_COLLAPSED_POINTS",
    )

    # Creating points to permanently store auto generated points from simplified polygon to a specified path
    auto_generated_points_3 = (
        f"{Building_N100.simplify_buildings_2_simplifying__n100.value}_Pnt"
    )

    arcpy.management.CopyFeatures(
        auto_generated_points_3,
        Building_N100.simplify_buildings_2__points__n100.value,
    )
    arcpy.management.Delete(auto_generated_points_3)


# Spatial join and adding fields to polygons
def join_and_add_fields():
    """
    Summary:
        Performs spatial join between simplified building polygons and original building polygons.
        Adds specific fields and assigns values to the building polygons, which will be useful for later in Resolve Building Conflict

    Details:
        - This function executes a spatial join between the simplified building polygons and the original building polygons.
        - The resulting feature class includes both the geometries and attributes of the input polygons, providing a unified dataset.
        - Multiple fields, including 'angle', 'hierarchy', and 'invisibility', are added to the feature class.
        - Default values of '0' are assigned to these fields
        - A copy of the feature class is then created for subsequent processing.

    Parameters:
        - No specific parameters

    """

    # Spatial join between simplified building polygons and original building polygons
    print("Performing spatial join...")

    arcpy.analysis.SpatialJoin(
        target_features=Building_N100.simplify_buildings_2_simplifying__n100.value,
        join_features=input_n50.Grunnriss,
        out_feature_class=Building_N100.join_and_add_fields__spatial_join_polygons__n100.value,
    )

    # Adding multiple fields
    print("Adding fields...")
    arcpy.management.AddFields(
        in_table=Building_N100.join_and_add_fields__spatial_join_polygons__n100.value,
        field_description=[
            ["angle", "SHORT"],
            ["hierarchy", "SHORT"],
            ["invisibility", "SHORT"],
        ],
    )

    # Assigning values to the fields
    print("Assigning values to fields...")
    arcpy.management.CalculateFields(
        in_table=Building_N100.join_and_add_fields__spatial_join_polygons__n100.value,
        expression_type="PYTHON3",
        fields=[["angle", "0"], ["hierarchy", "0"], ["invisibility", "0"]],
    )

    # Making a copy of the feature class
    print("Making a copy of the feature class...")
    arcpy.management.CopyFeatures(
        Building_N100.join_and_add_fields__spatial_join_polygons__n100.value,
        Building_N100.join_and_add_fields__building_polygons_final__n100.value,
    )


if __name__ == "__main__":
    main()
