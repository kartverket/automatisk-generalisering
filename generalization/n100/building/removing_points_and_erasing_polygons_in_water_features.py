# Importing modules
import arcpy

# Importing custom files
from file_manager.n100.file_manager_buildings import Building_N100
from input_data.input_symbology import SymbologyN100
from constants.n100_constants import N100_Values

# Import custom modules
from custom_tools.general_tools import custom_arcpy
from env_setup import environment_setup
from custom_tools.decorators.timing_decorator import timing_decorator


@timing_decorator
def main():
    """
    What:
        Fixes geometric conflicts between building polygon/point objects and water-features. Allows for
        tourist cabins to intersect water-features.
    How:
        selecting_water_polygon_features:
            Creates water polygon feature which are within a distance of polygon features.

        erasing_parts_of_building_polygons_in_water_features:
            Erases parts of building polygons that intersect with buffered water features.

        transforming_small_polygons_to_points:
            Transforms small building polygons to points, and maintains large enough building polygons

        merge_polygons:
            Merges building polygons that where not too close to water-features with the corrected building polygons.

        removing_points_in_water_features:
            Selects points that do not intersect with any water features, making sure no tourist cabins are lost. Then applies symbology to the remaining points.
    Why:
        There should be no geometric conflicts between building polygon/point objects and water-features, except for tourist huts.
    """

    environment_setup.main()
    selecting_water_polygon_features()
    erasing_parts_of_building_polygons_in_water_features()
    transforming_small_polygons_to_points()
    merge_polygons()
    removing_points_in_water_features()


@timing_decorator
def selecting_water_polygon_features():
    """
    Creates water polygon feature which are within a distance of polygon features.
    """
    sql_expression_water_features = f"objtype = 'FerskvannTørrfall' Or objtype = 'Innsjø' Or objtype = 'InnsjøRegulert' Or objtype = 'Havflate' Or objtype = 'ElvBekk'"
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.data_selection___land_cover_n100_input_data___n100_building.value,
        expression=sql_expression_water_features,
        output_name=Building_N100.removing_points_and_erasing_polygons_in_water_features___water_features___n100_building.value,
    )

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.removing_points_and_erasing_polygons_in_water_features___water_features___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        search_distance="100 Meters",
        select_features=Building_N100.point_resolve_building_conflicts___POLYGON_OUTPUT___n100_building.value,
        output_name=Building_N100.removing_points_and_erasing_polygons_in_water_features___water_features_close_to_building_polygons___n100_building.value,
    )


@timing_decorator
def erasing_parts_of_building_polygons_in_water_features():
    """
    Erases parts of building polygons that intersect with buffered water features.
    """

    # Buffering the water features with 15 Meters
    arcpy.PairwiseBuffer_analysis(
        in_features=Building_N100.removing_points_and_erasing_polygons_in_water_features___water_features_close_to_building_polygons___n100_building.value,
        out_feature_class=Building_N100.removing_points_and_erasing_polygons_in_water_features___water_features_buffered___n100_building.value,
        buffer_distance_or_field="15 Meters",
        method="PLANAR",
    )

    # Selecting polygons intersecting water features
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.point_resolve_building_conflicts___POLYGON_OUTPUT___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.removing_points_and_erasing_polygons_in_water_features___water_features_buffered___n100_building.value,
        output_name=Building_N100.removing_points_and_erasing_polygons_in_water_features___building_polygons_too_close_to_water_features___n100_building.value,
    )

    # Selecting polygons NOT intersecting from water features (these will not be further processed, but merged at the end of the script)
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.point_resolve_building_conflicts___POLYGON_OUTPUT___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.removing_points_and_erasing_polygons_in_water_features___water_features_buffered___n100_building.value,
        output_name=Building_N100.removing_points_and_erasing_polygons_in_water_features___building_polygons_NOT_too_close_to_water_features___n100_building.value,
        inverted=True,
    )

    # Erasing the parts of the building polygons that intersect the water feature buffer
    arcpy.PairwiseErase_analysis(
        in_features=Building_N100.removing_points_and_erasing_polygons_in_water_features___building_polygons_too_close_to_water_features___n100_building.value,
        erase_features=Building_N100.removing_points_and_erasing_polygons_in_water_features___water_features_buffered___n100_building.value,
        out_feature_class=Building_N100.removing_points_and_erasing_polygons_in_water_features___erased_polygons___n100_building.value,
    )


@timing_decorator
def transforming_small_polygons_to_points():
    """
    Transforms small building polygons to points, and maintains large enough building polygons
    """
    sql_expression_correct_size_polygons = (
        f"Shape_Area >= {N100_Values.minimum_selection_building_polygon_size_m2.value}"
    )

    sql_expression_too_small_polygons = (
        f"Shape_Area < {N100_Values.minimum_selection_building_polygon_size_m2.value}"
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.removing_points_and_erasing_polygons_in_water_features___erased_polygons___n100_building.value,
        expression=sql_expression_correct_size_polygons,
        output_name=Building_N100.removing_points_and_erasing_polygons_in_water_features___correct_sized_polygons___n100_building.value,
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.removing_points_and_erasing_polygons_in_water_features___erased_polygons___n100_building.value,
        expression=sql_expression_too_small_polygons,
        output_name=Building_N100.removing_points_and_erasing_polygons_in_water_features___too_small_polygons___n100_building.value,
    )

    arcpy.management.FeatureToPoint(
        in_features=Building_N100.removing_points_and_erasing_polygons_in_water_features___too_small_polygons___n100_building.value,
        out_feature_class=Building_N100.removing_points_and_erasing_polygons_in_water_features___polygons_to_points___n100_building.value,
    )


@timing_decorator
def merge_polygons():
    """
    Merges building polygons that where not too close to water-features with the corrected building polygons.
    """
    arcpy.management.Merge(
        inputs=[
            Building_N100.removing_points_and_erasing_polygons_in_water_features___building_polygons_NOT_too_close_to_water_features___n100_building.value,
            Building_N100.removing_points_and_erasing_polygons_in_water_features___correct_sized_polygons___n100_building.value,
        ],
        output=Building_N100.removing_points_and_erasing_polygons_in_water_features___final_building_polygons_merged___n100_building.value,
    )


@timing_decorator
def removing_points_in_water_features():
    """
    Selects points that do not intersect with any water features, making sure no tourist cabins are lost. Then applies symbology to the remaining points.
    """

    arcpy.management.Merge(
        inputs=[
            Building_N100.point_resolve_building_conflicts___POINT_OUTPUT___n100_building.value,
            Building_N100.removing_points_and_erasing_polygons_in_water_features___polygons_to_points___n100_building.value,
        ],
        output=Building_N100.removing_points_and_erasing_polygons_in_water_features___points_polygons_to_points_merged___n100_building.value,
    )

    sql_tourist_cabins = "byggtyp_nbr = 956"

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.removing_points_and_erasing_polygons_in_water_features___points_polygons_to_points_merged___n100_building.value,
        expression=sql_tourist_cabins,
        output_name=Building_N100.removing_points_and_erasing_polygons_in_water_features___tourist_cabins___n100_building.value,
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.removing_points_and_erasing_polygons_in_water_features___points_polygons_to_points_merged___n100_building.value,
        expression=sql_tourist_cabins,
        output_name=Building_N100.removing_points_and_erasing_polygons_in_water_features___not_tourist_cabins___n100_building.value,
        inverted=True,
    )

    # Select points that DO NOT intersect any water-features
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.removing_points_and_erasing_polygons_in_water_features___not_tourist_cabins___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.removing_points_and_erasing_polygons_in_water_features___water_features___n100_building.value,
        output_name=Building_N100.removing_points_and_erasing_polygons_in_water_features___points_that_do_not_intersect_water_features___n100_building.value,
        inverted=True,
    )

    arcpy.management.Merge(
        inputs=[
            Building_N100.removing_points_and_erasing_polygons_in_water_features___tourist_cabins___n100_building.value,
            Building_N100.removing_points_and_erasing_polygons_in_water_features___points_that_do_not_intersect_water_features___n100_building.value,
        ],
        output=Building_N100.removing_points_and_erasing_polygons_in_water_features___merged_points_and_tourist_cabins___n100_building.value,
    )


if __name__ == "__main__":
    main()
