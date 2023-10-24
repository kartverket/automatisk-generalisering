import arcpy

# Importing custom files relative to the root path
import config
from custom_tools import custom_arcpy
from env_setup import environment_setup
from input_data import input_n50
from input_data import input_n100
from file_manager.n100.file_manager_buildings import TemporaryFiles

# Importing environment
environment_setup.setup(workspace=config.n100_building_workspace)


# Main function
def main():
    simplify_building_polygon()


# Simplify building polygons and create points where buildings are too small


def simplify_building_polygon():
    """
    This function performs a series of geospatial operations, including:

    1. Aggregating building polygons using the `AggregatePolygons` tool.
    2. Simplifying building polygons using the `SimplifyBuilding` tool with a simplification tolerance of 75.
    3. Simplifying polygons using the `SimplifyPolygon` tool with a simplification tolerance of 15.
    4. Performing a spatial join between simplified building polygons and original building polygons.
    5. Adding multiple fields (angle, hierarchy, invisibility) to the spatially joined feature class.
    6. Assigning specific values to the added fields.
    7. Creating a copy of the feature class.

    Note that the function doesn't take any explicit parameters as inputs but relies on predefined input data and parameters.

    """

    # Aggregating building polygons

    print("Aggregating building polygons...")
    output_aggregate_polygon = TemporaryFiles.output_aggregate_polygon.value

    arcpy.cartography.AggregatePolygons(
        in_features=TemporaryFiles.grunnriss_selection_n50.value,
        out_feature_class=output_aggregate_polygon,
        aggregation_distance="15 Meters",
        minimum_area="3200 SquareMeters",
        minimum_hole_size="10000 SquareMeters",
        orthogonality_option="ORTHOGONAL",
        barrier_features=[
            TemporaryFiles.unsplit_veg_sti_n100.value
        ],  # Add more barriers ??
        out_table="grunnriss_n50_aggregated_tbl",
        aggregate_field="BYGGTYP_NBR",
    )
    print("Aggregating building polygons completed.")

    # Simplifying building polygons

    print("Simplifying building polygons...")
    output_simplify_building = "simplified_building"

    arcpy.cartography.SimplifyBuilding(
        in_features=output_aggregate_polygon,
        out_feature_class=output_simplify_building,
        simplification_tolerance="75",
        minimum_area="3200 SquareMeters",
        collapsed_point_option="KEEP_COLLAPSED_POINTS",
    )
    print("Simplifying building polygons completed.")

    # Creating points to permanently store auto generated points from simplified building polygons to a specified path
    auto_generated_points = f"{output_simplify_building}_Pnt"
    output_collapsed_points_simplified_building = TemporaryFiles.output_collapsed_points_simplified_building.value
    arcpy.management.CopyFeatures(auto_generated_points, output_collapsed_points_simplified_building)
    arcpy.management.Delete(auto_generated_points)

    # Simplifying polygons

    print("Simplifying polygons...")
    output_simplify_polygon = "simplified_polygon"

    arcpy.cartography.SimplifyPolygon(
        in_features=output_simplify_building,
        out_feature_class=output_simplify_polygon,
        algorithm="WEIGHTED_AREA",
        tolerance="15",
        minimum_area="3200 SquareMeters",
        collapsed_point_option="KEEP_COLLAPSED_POINTS",
    )
    print("Simplifying polygons completed.")

    # Creating points to permanently store auto generated points from simplified polygon to a specified path
    auto_generated_points2 = f"{output_simplify_polygon}_Pnt"
    output_collapsed_points_simplified_polygon = TemporaryFiles.output_collapsed_points_simplified_polygon.value
    arcpy.management.CopyFeatures(auto_generated_points2, output_collapsed_points_simplified_polygon)
    arcpy.management.Delete(auto_generated_points2)


    # Simplifying building polygons

    print("Simplifying building polygons...")
    output_simplify_building2 = "simplified_building2"

    arcpy.cartography.SimplifyBuilding(
        in_features=output_aggregate_polygon,
        out_feature_class=output_simplify_building2,
        simplification_tolerance="75",
        minimum_area="3200 SquareMeters",
        collapsed_point_option="KEEP_COLLAPSED_POINTS",
    )
    print("Simplifying building polygons completed.")

    # Creating points to permanently store auto generated points from simplified polygon to a specified path
    auto_generated_points3 = f"{output_simplify_building2}_Pnt"
    output_collapsed_points_simplified_building2 = TemporaryFiles.output_collapsed_points_simplified_building2.value
    arcpy.management.CopyFeatures(auto_generated_points3, output_collapsed_points_simplified_building2)
    arcpy.management.Delete(auto_generated_points3)

    # Spatial join between simplified building polygons and original building polygons

    print("Performing spatial join...")
    output_spatial_join = "spatial_joined_polygon"

    arcpy.analysis.SpatialJoin(
        target_features=output_simplify_polygon,
        join_features=input_n50.Grunnriss,
        out_feature_class=output_spatial_join,
    )
    print("Spatial join completed.")

    # Adding multiple fields

    print("Adding fields...")
    arcpy.management.AddFields(
        in_table=output_spatial_join,
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
        in_table=output_spatial_join,
        expression_type="PYTHON3",
        fields=[["angle", "0"], ["hierarchy", "0"], ["invisibility", "0"]],
    )
    print("Assigning values to fields completed.")

    # Making a copy of the feature class

    print("Making a copy of the feature class...")

    spatial_join_output = TemporaryFiles.simplified_grunnriss_n50.value
    arcpy.management.CopyFeatures(output_spatial_join, spatial_join_output)
    print("Copy completed.")


