# Importing modules
import arcpy

# Importing custom files
from file_manager.n100.file_manager_buildings import Building_N100
from input_data.input_symbology import SymbologyN100

# Import custom modules
from custom_tools.general_tools import custom_arcpy
from env_setup import environment_setup
from custom_tools.decorators.timing_decorator import timing_decorator


@timing_decorator
def main():
    environment_setup.main()
    selecting_water_polygon_features()
    removing_points_in_water_features()
    selecting_water_features_close_to_building_polygons()
    buffering_water_polygon_features()
    selecting_building_polygons()
    erasing_parts_of_building_polygons_in_water_features()
    merge_polygons()
    merge_points()


@timing_decorator
def selecting_water_polygon_features():
    sql_expression_water_features = f"objtype = 'FerskvannTørrfall' Or objtype = 'Innsjø' Or objtype = 'InnsjøRegulert' Or objtype = 'Havflate' Or objtype = 'ElvBekk'"
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.data_selection___land_cover_n100_input_data___n100_building.value,
        expression=sql_expression_water_features,
        output_name=Building_N100.removing_points_and_erasing_polygons_in_water_features___water_features___n100_building.value,
    )


@timing_decorator
def removing_points_in_water_features():
    # Select points that DO NOT intersect any waterfeatures
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.point_resolve_building_conflicts___building_points_final___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.removing_points_and_erasing_polygons_in_water_features___water_features___n100_building.value,
        output_name=Building_N100.removing_points_and_erasing_polygons_in_water_features___final_points___n100_building.value,
        inverted=True,
    )

    custom_arcpy.apply_symbology(
        input_layer=Building_N100.removing_points_and_erasing_polygons_in_water_features___final_points___n100_building.value,
        in_symbology_layer=SymbologyN100.bygningspunkt.value,
        output_name=Building_N100.removing_points_and_erasing_polygons_in_water_features___final_points___n100_lyrx.value,  # Used in the next file, "removing_overlapping_points.py"
    )


@timing_decorator
def selecting_water_features_close_to_building_polygons():
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.removing_points_and_erasing_polygons_in_water_features___water_features___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        search_distance="100 Meters",
        select_features=Building_N100.point_resolve_building_conflicts___building_polygons_final___n100_building.value,
        output_name=Building_N100.removing_points_and_erasing_polygons_in_water_features___water_features_close_to_building_polygons___n100_building.value,
    )


@timing_decorator
def buffering_water_polygon_features():
    # Buffering the water features with 15 Meters
    arcpy.PairwiseBuffer_analysis(
        in_features=Building_N100.removing_points_and_erasing_polygons_in_water_features___water_features_close_to_building_polygons___n100_building.value,
        out_feature_class=Building_N100.removing_points_and_erasing_polygons_in_water_features___water_features_buffered___n100_building.value,
        buffer_distance_or_field="15 Meters",
        method="PLANAR",
    )


@timing_decorator
def selecting_building_polygons():
    # Selecting polygons intersecting water features
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.point_resolve_building_conflicts___building_polygons_final___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.removing_points_and_erasing_polygons_in_water_features___water_features_buffered___n100_building.value,
        output_name=Building_N100.removing_points_and_erasing_polygons_in_water_features___building_polygons_too_close_to_water_features___n100_building.value,
    )

    # Selecting polygons NOT intersecting from water features (these will not be further processed, but merged at the end of the script)
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.point_resolve_building_conflicts___building_polygons_final___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.removing_points_and_erasing_polygons_in_water_features___water_features_buffered___n100_building.value,
        output_name=Building_N100.removing_points_and_erasing_polygons_in_water_features___building_polygons_NOT_too_close_to_water_features___n100_building.value,
        inverted=True,
    )


@timing_decorator
def erasing_parts_of_building_polygons_in_water_features():
    # Erasing the parts of the building polygons that intersect the water feature buffer
    arcpy.PairwiseErase_analysis(
        in_features=Building_N100.removing_points_and_erasing_polygons_in_water_features___building_polygons_too_close_to_water_features___n100_building.value,
        erase_features=Building_N100.removing_points_and_erasing_polygons_in_water_features___water_features_buffered___n100_building.value,
        out_feature_class=Building_N100.removing_points_and_erasing_polygons_in_water_features___erased_polygons___n100_building.value,
    )


@timing_decorator
def merge_polygons():
    arcpy.management.Merge(
        inputs=[
            Building_N100.removing_points_and_erasing_polygons_in_water_features___building_polygons_NOT_too_close_to_water_features___n100_building.value,
            Building_N100.removing_points_and_erasing_polygons_in_water_features___erased_polygons___n100_building.value,
        ],
        output=Building_N100.removing_points_and_erasing_polygons_in_water_features___final_building_polygons_merged___n100_building.value,
    )


@timing_decorator
def merge_points():
    arcpy.management.Merge(
        inputs=[
            Building_N100.removing_points_and_erasing_polygons_in_water_features___final_points___n100_building.value,
            f"{Building_N100.removing_points_and_erasing_polygons_in_water_features___simplified_polygons___n100_building.value}_Pnt",
        ],
        output=Building_N100.removing_points_and_erasing_polygons_in_water_features___final_points_merged___n100_building.value,
    )


if __name__ == "__main__":
    main()
