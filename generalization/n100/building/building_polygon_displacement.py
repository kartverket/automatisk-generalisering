# Importing modules
import numpy as np
import arcpy
import os

# Importing custom modules
import config
from input_data import input_n100
from custom_tools import custom_arcpy
from custom_tools.polygon_processor import PolygonProcessor
from input_data import input_symbology

# Importing environment settings
from env_setup import environment_setup

environment_setup.general_setup()

# Importing file manager
from file_manager.n100.file_manager_buildings import Building_N100


def main():
    """
    replace with docstring
    """
    # propagate_displacement_building_polygons()
    # features_500_m_from_building_polygons()
    # apply_symbology_to_layers()
    resolve_building_conflict_building_polygon()


def propagate_displacement_building_polygons():
    """
    replace with docstring
    """
    print(
        "REMEMBER TO  SWITCH TO NEW DISPLACEMENT FEATURE AFTER GENERALIZATION OF ROADS"
    )
    print("Propogate displacement ...")
    # Copying layer so no changes are made to the original
    arcpy.management.Copy(
        in_data=Building_N100.join_and_add_fields__building_polygons_final__n100.value,
        out_data=Building_N100.propagate_displacement_building_polygons__building_polygon_pre_propogate_displacement__n100.value,
    )

    # Selecting propogate displacement features 500 meters from building polgyons
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=config.displacement_feature,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.propagate_displacement_building_polygons__building_polygon_pre_propogate_displacement__n100.value,
        output_name=Building_N100.propagate_displacement_building_polygons__displacement_feature_1000_m_from_building_polygon__n100.value,
        search_distance="500 Meters",
    )

    # Running propogate displacement for building polygons
    arcpy.cartography.PropagateDisplacement(
        in_features=Building_N100.propagate_displacement_building_polygons__building_polygon_pre_propogate_displacement__n100.value,
        displacement_features=Building_N100.propagate_displacement_building_polygons__displacement_feature_1000_m_from_building_polygon__n100.value,
        adjustment_style="SOLID",
    )

    # Copying and assigning new name to layer
    arcpy.management.Copy(
        in_data=Building_N100.propagate_displacement_building_polygons__building_polygon_pre_propogate_displacement__n100.value,
        out_data=Building_N100.propagate_displacement_building_polygons__after_propogate_displacement__n100.value,
    )


def features_500_m_from_building_polygons():
    """
    replace with docstring
    """
    print("Selecting features 500 meter from building polygon ...")
    # Selecting begrensningskurve 500 meters from building polygons
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.preparation_begrensningskurve__selected_waterfeatures_from_begrensningskurve__n100.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.propagate_displacement_building_polygons__after_propogate_displacement__n100.value,
        output_name=Building_N100.features_500_m_from_building_polygons__selected_begrensningskurve__n100.value,
        search_distance="500 Meters",
    )

    # Selecting roads 500 meters from building polygons
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.preperation_veg_sti__unsplit_veg_sti__n100.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.propagate_displacement_building_polygons__after_propogate_displacement__n100.value,
        output_name=Building_N100.features_500_m_from_building_polygons__selected_roads__n100.value,
        search_distance="500 Meters",
    )


def apply_symbology_to_layers():
    """
    replace with docstring
    """
    print("Applying symbology ...")
    # Applying symbology to building polygons
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.propagate_displacement_building_polygons__after_propogate_displacement__n100.value,
        in_symbology_layer=input_symbology.SymbologyN100.grunnriss.value,
        output_name=Building_N100.apply_symbology_to_layers__building_polygon__n100__lyrx.value,
    )
    # Applying symbology to roads
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.features_500_m_from_building_polygons__selected_roads__n100.value,
        in_symbology_layer=input_symbology.SymbologyN100.veg_sti.value,
        output_name=Building_N100.apply_symbology_to_layers__roads__n100__lyrx.value,
    )

    # Applying symbology to begrensningskurve (limiting curve)
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.features_500_m_from_building_polygons__selected_begrensningskurve__n100.value,
        in_symbology_layer=input_symbology.SymbologyN100.begrensnings_kurve.value,
        output_name=Building_N100.apply_symbology_to_layers__begrensningskurve__n100__lyrx.value,
    )


def resolve_building_conflict_building_polygon():

    """
    replace with docstring
    """
    # Polygon prosessor

    input_building_points = (
        Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value
    )
    output_polygon_feature_class = (
        Building_N100.building_point_buffer_displacement__iteration_points_to_square_polygons__n100.value
    )
    building_symbol_dimensions = {
        1: (145, 145),
        2: (145, 145),
        3: (195, 145),
        4: (40, 40),
        5: (80, 80),
        6: (30, 30),
        7: (45, 45),
        8: (45, 45),
        9: (53, 45),
    }
    symbol_field_name = "symbol_val"
    index_field_name = "OBJECTID"

    polygon_process = PolygonProcessor(
        input_building_points,
        output_polygon_feature_class,
        building_symbol_dimensions,
        symbol_field_name,
        index_field_name,
    )
    polygon_process.run()

    # Resolving Building Conflicts for building polygons
    print("Resolving building conflicts ...")
    # Setting scale to 1: 100 000
    arcpy.env.referenceScale = "100000"

    input_barriers = [
        [
            Building_N100.apply_symbology_to_layers__roads__n100__lyrx.value,
            "false",
            "15 Meters",
        ],
        [
            Building_N100.apply_symbology_to_layers__begrensningskurve__n100__lyrx.value,
            "false",
            "15 Meters",
        ],
        [
            Building_N100.apply_symbology_to_layers__begrensningskurve__n100__lyrx.value,  # POLYGON PROSESSOR OUTPUT INN HER
            "false",
            "15 Meters",
        ],
    ]

    # Resolve Building Polygon with roads and begrensningskurve as barriers
    arcpy.cartography.ResolveBuildingConflicts(
        in_buildings=Building_N100.apply_symbology_to_layers__building_polygon__n100__lyrx.value,
        invisibility_field="invisibility",
        in_barriers=input_barriers,
        building_gap="30 meters",
        minimum_size="1 meters",
    )

    # Copying and assigning new name to layer
    arcpy.management.Copy(
        in_data=Building_N100.propagate_displacement_building_polygons__after_propogate_displacement__n100.value,
        out_data=Building_N100.resolve_building_conflict_building_polygon__after_RBC__n100.value,
    )
    print("Finished")


def invisible_building_polygons_to_point():
    """
    replace with docstring
    """
    print("Transforming polygons marked with invisibility 1 to points ...")

    # Making new feature layer of polygons
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.resolve_building_conflict_building_polygon__after_RBC__n100.value,
        expression="invisibility = 1",
        output_name=Building_N100.invisible_building_polygons_to_point__invisible_polygons__n100.value,
    )

    # Polygon to point
    arcpy.management.FeatureToPoint(
        in_features=Building_N100.invisible_building_polygons_to_point__invisible_polygons__n100.value,
        out_feature_class=Building_N100.invisible_building_polygons_to_point__invisible_polygons_to_points__n100.value,
    )

    print("Finished.")


# ROAD BUFFER IN HERE


def intersecting_building_polygons_to_point():

    # Selecting buildings that overlap with road buffer layer
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.preperation_veg_sti__unsplit_veg_sti__n100.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.propagate_displacement_building_polygons__after_propogate_displacement__n100.value,
        output_name=Building_N100.features_500_m_from_building_polygons__selected_roads__n100.value,
        search_distance="500 Meters",
    )

    # Transforming these polygons to points
    arcpy.management.FeatureToPoint(
        in_features=Building_N100.small_building_polygons_to_point__building_polygons_too_small__n100.value,
        out_feature_class=Building_N100.small_building_polygons_to_point__building_points__n100.value,
    )


if __name__ == "__main__":
    main()
