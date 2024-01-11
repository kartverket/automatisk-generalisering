# Importing modules
import numpy as np
import arcpy
import os

# Importing custom modules
import config
from input_data import input_n100
from custom_tools import custom_arcpy

# Importing environment settings
from env_setup import environment_setup

environment_setup.general_setup()

# Importing file manager
from file_manager.n100.file_manager_buildings import Building_N100


def main():
    propagate_displacement_building_polygons()
    creating_road_buffer()
    resolve_building_conflict_building_polygon()
    erasing_building_polygons_with_buffer()
    small_building_polygons_to_point()


def propagate_displacement_building_polygons():
    """
    replace with docstring
    """

    # Copying layer so changes are made to the original
    arcpy.management.Copy(
        in_data=Building_N100.simplify_building_polygons__simplified_grunnriss__n100.value,
        out_data=Building_N100.propagate_displacement__building_polygon_pre_propogate_displacement__n100.value,
    )

    # Running propogate displacement for building polygons
    arcpy.cartography.PropagateDisplacement(
        in_features=Building_N100.propagate_displacement__building_polygon_pre_propogate_displacement__n100.value,
        displacement_features=config.displacement_feature,
        adjustment_style="SOLID",
    )

    # Copying and assigning new name to layer
    arcpy.management.Copy(
        in_data=Building_N100.propagate_displacement__building_polygon_pre_propogate_displacement__n100.value,
        out_data=Building_N100.propagate_displacement__building_polygon_after_propogate_displacement__n100.value,
    )


def creating_road_buffer():
    """
    replace with docstring
    """
    # Dictionary with SQL queries and their corresponding buffer widths
    sql_queries = {
        "MOTORVEGTYPE = 'Motorveg'": 42.5,
        """ 
        SUBTYPEKODE = 3 
        Or MOTORVEGTYPE = 'Motortrafikkveg' 
        Or (SUBTYPEKODE = 2 And MOTORVEGTYPE = 'Motortrafikkveg') 
        Or (SUBTYPEKODE = 2 And MOTORVEGTYPE = 'Ikke motorveg') 
        Or (SUBTYPEKODE = 4 And MOTORVEGTYPE = 'Ikke motorveg') 
        """: 22.5,
        """
        SUBTYPEKODE = 1
        Or SUBTYPEKODE = 5
        Or SUBTYPEKODE = 6
        Or SUBTYPEKODE = 9
        """: 20,
        """
        SUBTYPEKODE = 7
        Or SUBTYPEKODE = 8
        Or SUBTYPEKODE = 10
        Or SUBTYPEKODE =11
        """: 7.5,
    }

    different_road_types = "different_road_types"
    road_buffer = "road_buffer"

    # List to store the road buffer outputs
    road_buffer_output_names = []

    # Counter for naming the individual road type selections
    counter = 1

    # Loop through the dictionary (Key: SQL query and Value: width) to create buffers around the different roads
    for sql_query, original_width in sql_queries.items():
        selection_output_name = f"{different_road_types}_selection_{counter}"
        buffer_width = original_width + 15
        buffer_output_name = f"{road_buffer}_{buffer_width}m_{counter}"

        # Selecting road types and making new feature layer based on SQL query
        custom_arcpy.select_attribute_and_make_feature_layer(
            input_layer=Building_N100.preperation_veg_sti__unsplit_veg_sti__n100.value,
            expression=sql_query,
            output_name=selection_output_name,
        )

        # Making a buffer around each road type with specified width + 15 meters
        arcpy.analysis.PairwiseBuffer(
            in_features=selection_output_name,
            out_feature_class=buffer_output_name,
            buffer_distance_or_field=f"{buffer_width} Meters",
        )

        # Add buffer output names to list
        road_buffer_output_names.append(buffer_output_name)
        # Increase the counter by 1
        counter += 1

    # Merge all buffers into a single feature class
    arcpy.management.Merge(
        inputs=road_buffer_output_names,
        output="all_road_buffers_with_gap_merged",
    )


def resolve_building_conflict_building_polygon():
    arcpy.env.referenceScale = "100000"

    # Applying symbology to building polygons
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.propagate_displacement_building_polygon__after_propogate_displacement__n100.value,
        in_symbology_layer=config.symbology_n100_grunnriss,
        output_name=Building_N100.resolve_building_conflicts_building_polygon__,
    )
    # Applying symbology to roads
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.propagate_displacement_building_polygon__after_propogate_displacement__n100.value,
        in_symbology_layer=config.symbology_n100_grunnriss,
        output_name=Building_N100.resolve_building_conflicts__building_points_RBC_result_1__n100_lyrx.value,
    )

    # Applying symbology to begrensningskurve (limiting curve)
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.propagate_displacement__building_polygon_after_propogate_displacement__n100.value,
        in_symbology_layer=config.symbology_n100_grunnriss,
        output_name=Building_N100.resolve_building_conflicts__building_points_RBC_result_1__n100_lyrx.value,
    )

    # Resolve Building Polygon with buffer and begrensningskurve as barriers
    arcpy.cartography.ResolveBuildingConflicts(
        in_buildings=Building_N100.resolve_building_conflicts__building_points_RBC_result_1__n100_lyrx.value,
        invisibility_field="invisibility",
        in_barriers=[
            input_n100.VegSti,
            Building_N100.preparation_preparation_begrensningskurve__selected_waterfeatures_from_begrensningskurve__n100.value,
        ],
        building_gap="15 meters",
        minimum_size="1 meters",
        hierarchy_field="hierarchy",
    )


def erasing_building_polygons_with_buffer():
    # Erasing building polygons with buffer
    arcpy.analysis.Erase(in_features=x, erase_features=x, out_feature_class=x)


def small_building_polygons_to_point():
    return 0


if __name__ == "__main__":
    main()
