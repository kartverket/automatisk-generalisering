import arcpy
import multiprocessing
from multiprocessing import Pool, Manager
from math import atan2, sin, cos, sqrt
from tqdm import tqdm

import config
from env_setup import environment_setup
from input_data import input_n50
from input_data import input_n100
from custom_tools import custom_arcpy
from file_manager.n100.file_manager_rivers import River_N100


def main():
    setup_arcpy_environment()

    problematic_dangles, all_rivers, water_polygon = processing_preparation()

    # Assume that the 'orig_ob_id' field in 'all_rivers' holds the original OID
    id_field = "orig_ob_id"

    # Container for holding line start and end points
    line_points = []

    # Iterate over each dangle feature
    with arcpy.da.SearchCursor(problematic_dangles, ["SHAPE@", id_field]) as cursor:
        for row in cursor:
            dangle_geom = row[0]  # Geometry object of the dangle
            dangle_oid = row[1]  # OID value from the dangle feature

            # Proceed with excluding the originating line and generating near table
            near_features = exclude_originating_line(all_rivers, dangle_oid, id_field)
            near_table = generate_near_table(
                dangle_geom, near_features
            )  # Adjust this function to accept geometry
            coordinate_pairs = get_xy_coordinates(near_table)
            line_points.extend(coordinate_pairs)
            print(f"Processed dangle {dangle_oid}")
    # After collecting coordinate_pairs and generating new lines
    new_lines = create_lines_from_coordinates(line_points, all_rivers)

    # Now, process these new lines to integrate them with the original river network
    final_river_network = process_new_lines(new_lines, all_rivers)


def setup_arcpy_environment():
    """
    Summary:
        Sets up the ArcPy environment based on predefined settings defined in `general_setup`.
        This function ensures that the ArcPy environment is properly configured for the specific project by utilizing
        the `general_setup` function from the `environment_setup` module.

    Details:
        - It calls the `general_setup` function from the `environment_setup` module to set up the ArcPy environment based on predefined settings.
    """
    environment_setup.general_setup()


def processing_preparation():
    arcpy.management.CopyFeatures(
        in_features=config.river_sprint_feature,
        out_feature_class=River_N100.extending_river_geometry__input_rivers_copy__n100.value,
    )
    arcpy.management.CopyFeatures(
        in_features=River_N100.unconnected_river_geometry__problematic_river_dangles__n100.value,
        out_feature_class=f"{River_N100.unconnected_river_geometry__problematic_river_dangles__n100.value}_copy",
    )

    problematic_dangles = (
        River_N100.unconnected_river_geometry__problematic_river_dangles__n100.value
    )
    all_rivers = (
        River_N100.unconnected_river_geometry__unsplit_river_features__n100.value
    )
    water_polygon = (
        River_N100.unconnected_river_geometry__water_area_features_selected__n100.value
    )

    return problematic_dangles, all_rivers, water_polygon


def exclude_originating_line(all_rivers, dangle_oid, id_field):
    """
    Create a feature layer that excludes the line from which the dangle originates.

    :param all_rivers: The feature class containing all river line features.
    :param dangle_oid: The OID of the dangle point.
    :param id_field: The field name that holds the original OID of the river lines.
    :return: A feature layer that excludes the originating line of the dangle.
    """
    excluded_rivers_layer = "excluded_rivers_layer"
    arcpy.MakeFeatureLayer_management(all_rivers, excluded_rivers_layer)
    arcpy.SelectLayerByAttribute_management(
        excluded_rivers_layer, "NEW_SELECTION", f"{id_field} <> {dangle_oid}"
    )
    return excluded_rivers_layer


def generate_near_table(dangle, near_features):
    """
    Generate a near table for a dangle point to find the nearest feature's closest point.

    :param dangle: A point geometry representing the dangle.
    :param near_features: The feature class to search within.
    :return: The path to the near table generated.
    """
    # Create a temporary in-memory feature class for the dangle point
    dangle_feature_class = f"{River_N100.unconnected_river_geometry__problematic_river_dangles__n100.value}_copy"
    arcpy.CopyFeatures_management(dangle, dangle_feature_class)

    # Set up the near table path
    near_table = "in_memory/near_table"

    # Generate the near table
    arcpy.GenerateNearTable_analysis(
        in_features=dangle_feature_class,
        near_features=near_features,
        out_table=near_table,
        closest="CLOSEST",
        location="LOCATION",
        method="PLANAR",
    )

    # Clean up the temporary dangle point feature class
    arcpy.Delete_management(dangle_feature_class)

    return near_table


def get_xy_coordinates(near_table):
    """
    Extract the XY coordinates from the near table.

    :param near_table: The near table to extract coordinates from.
    :return: A tuple of XY coordinates for the dangle and the nearest feature.
    """
    # Initialize a list to store the coordinate pairs
    coordinate_pairs = []

    # Fetch the results from the near table
    with arcpy.da.SearchCursor(
        near_table, ["FROM_X", "FROM_Y", "NEAR_X", "NEAR_Y"]
    ) as cursor:
        for row in cursor:
            dangle_xy = (row[0], row[1])  # FROM_X and FROM_Y
            nearest_feature_xy = (row[2], row[3])  # NEAR_X and NEAR_Y
            coordinate_pairs.append((dangle_xy, nearest_feature_xy))

    return coordinate_pairs


def create_lines_from_coordinates(line_points, all_rivers):
    """
    Create new line features from the pairs of XY coordinates.

    :param line_points: A list of tuples containing pairs of XY coordinates.
    :return: A list of arcpy.Polyline objects representing the new lines.
    """
    new_lines = []
    spatial_reference = arcpy.Describe(
        all_rivers
    ).spatialReference  # Assuming all_rivers has the desired spatial reference

    for line_start, line_end in line_points:
        # Create arcpy.Point objects from the coordinates
        start_point = arcpy.Point(*line_start)
        end_point = arcpy.Point(*line_end)

        # Create a line from the start point to the end point
        line = arcpy.Polyline(arcpy.Array([start_point, end_point]), spatial_reference)
        new_lines.append(line)

    return new_lines


def process_new_lines(new_lines, all_rivers):
    """
    Merge new line features with original river features and remove duplicates.

    :param new_lines: A list of arcpy.Polyline objects representing new lines to be added.
    :param all_rivers: The feature class containing all river line features.
    :return: The feature class path of the final river network with new lines merged in.
    """
    # Create an in-memory feature class to hold the new lines
    new_lines_feature_class = River_N100.extending_river_geometry__new_lines__n100.value
    arcpy.CopyFeatures_management(new_lines, new_lines_feature_class)

    # Merge the new lines with the existing river features
    merged_rivers = River_N100.extending_river_geometry__merged_lines__n100.value
    arcpy.Merge_management([all_rivers, new_lines_feature_class], merged_rivers)

    # Here you would implement any logic needed to remove duplicate lines
    # For now, let's assume that's done and we just return the merged rivers
    final_rivers = merged_rivers  # Placeholder for actual deduplication logic

    return final_rivers


if __name__ == "__main__":
    main()
