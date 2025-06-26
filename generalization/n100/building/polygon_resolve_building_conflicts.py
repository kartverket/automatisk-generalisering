# Importing modules
import arcpy

# Importing custom modules
import config
from custom_tools.general_tools import custom_arcpy
from custom_tools.general_tools.polygon_processor import PolygonProcessor
from custom_tools.general_tools.line_to_buffer_symbology import LineToBufferSymbology
from input_data import input_symbology
from constants.n100_constants import N100_Symbology, N100_SQLResources, N100_Values

# Importing environment settings
from env_setup import environment_setup

# Importing file manager
from file_manager.n100.file_manager_buildings import Building_N100

# Importing timing decorator

from custom_tools.decorators.timing_decorator import timing_decorator


@timing_decorator
def main():
    """
    What:
        This script processes spatial data to resolve conflicts between building polygons and nearby
        barriers such as roads, water bodies, hospitals, and churches.
        It transforms certain building polygons into points based on proximity to barriers and polygon size.

    How:
        The script begins by selecting roads, water features, and railways within 500 meters of building polygons,
        which serve as barriers. It processes hospital and church points into squares and applies the correct
        symbology. Symbology is then applied to the layers, including roads, water barriers, and building polygons.

        Building conflicts are resolved by ensuring appropriate clearances between building polygons and the
        selected barriers, including roads, hospitals, churches, and water features. Invisible building polygons,
        building polygons that intersect roads, and building polygons that are considered too small,
         are converted into points, while the rest of the building polygons are kept as they are.

    Why:
        The goal is to ensure accurate representation of building polygons in a geospatial dataset where
        buildings may conflict with barriers like roads or are too small for cartographic visibility.

    """

    environment_setup.main()
    roads_and_water_barriers_500_m_from_building_polygons()
    hospital_church_points_to_squares()
    apply_symbology_to_layers()
    resolve_building_conflict_building_polygon()
    invisible_building_polygons_to_point()
    intersecting_building_polygons_to_point()
    merging_invisible_intersecting_points()
    check_if_building_polygons_are_big_enough()
    small_building_polygons_to_points()


@timing_decorator
def roads_and_water_barriers_500_m_from_building_polygons():
    """
    Selects roads, water barriers, and railways that are within 500 meters of building polygons.
    """
    print("Selecting features 500 meter from building polygon ...")
    # Selecting begrensningskurve 500 meters from building polygons
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.data_preparation___processed_begrensningskurve___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.polygon_propogate_displacement___building_polygons_after_displacement___n100_building.value,
        output_name=Building_N100.polygon_resolve_building_conflicts___begrensningskurve_500m_from_displaced_polygon___n100_building.value,
        search_distance="500 Meters",
    )

    # Selecting roads 500 meters from building polygons
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.data_preparation___road_symbology_buffers___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.polygon_propogate_displacement___building_polygons_after_displacement___n100_building.value,
        output_name=Building_N100.polygon_resolve_building_conflicts___roads_500m_from_displaced_polygon___n100_building.value,
        search_distance="500 Meters",
    )

    # Selecting railway 500 meters from building polygons
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.data_selection___railroad_tracks_n100_input_data___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.polygon_propogate_displacement___building_polygons_after_displacement___n100_building.value,
        output_name=Building_N100.polygon_resolve_building_conflicts___railroads_500m_from_displaced_polygon___n100_building.value,
        search_distance="500 Meters",
    )
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.data_preparation___power_grid_lines___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.polygon_propogate_displacement___building_polygons_after_displacement___n100_building.value,
        output_name=Building_N100.data_selection___power_grid_lines_500m_selection___n100_building.value,
        search_distance="500 Meters",
    )


@timing_decorator
def hospital_church_points_to_squares():
    """
    Selects hospital and church points, processes them into squares, and applies the appropriate symbology.
    """
    # Selecting hospital and churches from n50
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.data_selection___building_point_n50_input_data___n100_building.value,
        expression="byggtyp_nbr IN (970, 719, 671)",
        output_name=Building_N100.polygon_resolve_building_conflicts___hospital_church_points___n100_building.value,
    )

    # Adding a symbology value field based on NBR values
    arcpy.AddField_management(
        in_table=Building_N100.polygon_resolve_building_conflicts___hospital_church_points___n100_building.value,
        field_name="symbol_val",
        field_type="LONG",
    )

    arcpy.CalculateField_management(
        in_table=Building_N100.polygon_resolve_building_conflicts___hospital_church_points___n100_building.value,
        field="symbol_val",
        expression="determineVal(!byggtyp_nbr!)",
        expression_type="PYTHON3",
        code_block=N100_SQLResources.nbr_symbol_val_code_block.value,
    )

    # Polygon prosessor
    symbol_field_name = "symbol_val"
    index_field_name = "OBJECTID"

    print("Polygon prosessor...")
    polygon_process = PolygonProcessor(
        Building_N100.polygon_resolve_building_conflicts___hospital_church_points___n100_building.value,  # input
        Building_N100.polygon_resolve_building_conflicts___hospital_church_squares___n100_building.value,  # output
        N100_Symbology.building_symbol_dimensions.value,
        symbol_field_name,
        index_field_name,
    )
    polygon_process.run()

    # Applying symbology to polygonprocessed hospital and churches
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.polygon_resolve_building_conflicts___hospital_church_squares___n100_building.value,
        in_symbology_layer=input_symbology.SymbologyN100.building_polygon.value,
        output_name=Building_N100.polygon_resolve_building_conflicts___polygonprocessor_symbology___n100_building_lyrx.value,
    )


@timing_decorator
def apply_symbology_to_layers():
    """
    Applies symbology (lyrx files) to building polygons, roads, and water barriers.
    """
    print("Applying symbology ...")
    # Applying symbology to building polygons
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.polygon_propogate_displacement___building_polygons_after_displacement___n100_building.value,
        in_symbology_layer=input_symbology.SymbologyN100.building_polygon.value,
        output_name=Building_N100.polygon_resolve_building_conflicts___building_polygon___n100_building_lyrx.value,
    )
    # Applying symbology to roads
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.polygon_resolve_building_conflicts___roads_500m_from_displaced_polygon___n100_building.value,
        in_symbology_layer=input_symbology.SymbologyN100.road_buffer.value,
        output_name=Building_N100.polygon_resolve_building_conflicts___roads___n100_building_lyrx.value,
    )

    # Applying symbology to begrensningskurve (limiting curve)
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.polygon_resolve_building_conflicts___begrensningskurve_500m_from_displaced_polygon___n100_building.value,
        in_symbology_layer=input_symbology.SymbologyN100.begrensningskurve_polygon.value,
        output_name=Building_N100.polygon_resolve_building_conflicts___begrensningskurve___n100_building_lyrx.value,
    )

    # Applying symbology to railway
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.polygon_resolve_building_conflicts___railroads_500m_from_displaced_polygon___n100_building.value,
        in_symbology_layer=input_symbology.SymbologyN100.railway.value,
        output_name=Building_N100.polygon_resolve_building_conflicts___railway___n100_building_lyrx.value,
    )

    custom_arcpy.apply_symbology(
        input_layer=Building_N100.data_selection___power_grid_lines_500m_selection___n100_building.value,
        in_symbology_layer=config.symbology_samferdsel,
        output_name=Building_N100.polygon_resolve_building_conflicts___power_grid_lines___n100_building_lyrx.value,
        grouped_lyrx=True,
        target_layer_name="AnleggsLinje_maske_sort",
    )


@timing_decorator
def resolve_building_conflict_building_polygon():
    """
    Resolves conflicts among building polygons considering roads, water features, hospitals, and churches as barriers.
    This function resolves conflicts among building polygons by taking into account various barriers such as roads,
    water features, hospitals, and churches. To incorporate hospital and church points as barriers, these points are first
    transformed into polygons using the dimensions of their symbology.
    """

    # Resolving Building Conflicts for building polygons
    print("Resolving building conflicts ...")
    # Setting scale to 1: 100 000
    arcpy.env.referenceScale = "100000"

    # Barriers: roads, begrensningskurve, hospital and church squares
    input_barriers = [
        [
            Building_N100.polygon_resolve_building_conflicts___roads___n100_building_lyrx.value,
            "false",
            f"{N100_Values.rbc_barrier_clearance_distance_m.value} Meters",  # 30 Meters for all barriers
        ],
        [
            Building_N100.polygon_resolve_building_conflicts___begrensningskurve___n100_building_lyrx.value,
            "false",
            f"{N100_Values.rbc_barrier_clearance_distance_m.value} Meters",
        ],
        [
            Building_N100.polygon_resolve_building_conflicts___polygonprocessor_symbology___n100_building_lyrx.value,
            "false",
            f"{N100_Values.rbc_barrier_clearance_distance_m.value} Meters",
        ],
        [
            Building_N100.data_preparation___railway_stations_to_polygons_symbology___n100_building_lyrx.value,
            "false",
            f"{N100_Values.rbc_barrier_clearance_distance_m.value} Meters",
        ],
        [
            Building_N100.polygon_resolve_building_conflicts___railway___n100_building_lyrx.value,
            "false",
            f"{N100_Values.rbc_barrier_clearance_distance_m.value} Meters",
        ],
        [
            Building_N100.polygon_resolve_building_conflicts___power_grid_lines___n100_building_lyrx.value,
            "false",
            f"{N100_Values.rbc_barrier_clearance_distance_m.value} Meters",
        ],
    ]

    # Resolve Building Conflict with building polygons and barriers
    arcpy.cartography.ResolveBuildingConflicts(
        in_buildings=Building_N100.polygon_resolve_building_conflicts___building_polygon___n100_building_lyrx.value,
        invisibility_field="invisibility",
        in_barriers=input_barriers,
        building_gap=f"{N100_Values.rbc_building_clearance_distance_m.value} Meters",
        minimum_size="1 meters",
    )

    # Copying and assigning new name to layer
    arcpy.management.Copy(
        in_data=Building_N100.polygon_propogate_displacement___building_polygons_after_displacement___n100_building.value,
        out_data=Building_N100.polygon_resolve_building_conflicts___after_rbc___n100_building.value,
    )
    print("Finished")


@timing_decorator
def invisible_building_polygons_to_point():
    """
    Converts invisible building polygons to points and separates them from non-invisible polygons.
    """
    print("Transforming polygons marked with invisibility 1 to points ...")

    # Making new feature layer of polygons that is invisible
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.polygon_resolve_building_conflicts___after_rbc___n100_building.value,
        expression="invisibility = 1",
        output_name=Building_N100.polygon_resolve_building_conflicts___invisible_polygons_after_rbc___n100_building.value,
    )

    # Making new feature layer of polygons that is NOT invisible
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.polygon_resolve_building_conflicts___after_rbc___n100_building.value,
        expression="invisibility = 0",
        output_name=Building_N100.polygon_resolve_building_conflicts___not_invisible_polygons_after_rbc___n100_building.value,
    )

    # Polygon to point
    arcpy.management.FeatureToPoint(
        in_features=Building_N100.polygon_resolve_building_conflicts___invisible_polygons_after_rbc___n100_building.value,
        out_feature_class=Building_N100.polygon_resolve_building_conflicts___invisible_polygons_to_points___n100_building.value,
    )

    print("Finished.")


@timing_decorator
def intersecting_building_polygons_to_point():
    """
    Identifies building polygons that intersects road and converts them into points.
    """
    print("Finding intersecting points... ")

    # Selecting buildings that DO NOT overlap with road buffer layer and will be kept as polygons
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.polygon_resolve_building_conflicts___not_invisible_polygons_after_rbc___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.data_preparation___road_symbology_buffers___n100_building.value,
        inverted=True,  # Inverted
        output_name=Building_N100.polygon_resolve_building_conflicts___building_polygons_not_invisible_not_intersecting___n100_building.value,
    )

    # Selecting buildings that overlap with road buffer layer and will be transformed to points
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.polygon_resolve_building_conflicts___not_invisible_polygons_after_rbc___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.data_preparation___road_symbology_buffers___n100_building.value,
        inverted=False,
        output_name=Building_N100.polygon_resolve_building_conflicts___building_polygons_intersecting_road___n100_building.value,
    )

    # Transforming these polygons to points
    arcpy.management.FeatureToPoint(
        in_features=Building_N100.polygon_resolve_building_conflicts___building_polygons_intersecting_road___n100_building.value,
        out_feature_class=Building_N100.polygon_resolve_building_conflicts___intersecting_polygons_to_points___n100_building.value,
    )


@timing_decorator
def merging_invisible_intersecting_points():
    """
    Merges points from intersecting building polygons and invisible polygons.
    """
    print("Merging points...")
    arcpy.management.Merge(
        inputs=[
            Building_N100.polygon_resolve_building_conflicts___intersecting_polygons_to_points___n100_building.value,
            Building_N100.polygon_resolve_building_conflicts___invisible_polygons_to_points___n100_building.value,
        ],
        output=Building_N100.polygon_resolve_building_conflicts___final_merged_points___n100_building.value,
    )


@timing_decorator
def check_if_building_polygons_are_big_enough():
    """
    Removes building polygons from the input layer that have a shape area smaller than
    a specified threshold (3200 square meters).
    """
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.polygon_resolve_building_conflicts___building_polygons_not_invisible_not_intersecting___n100_building.value,
        expression="Shape_Area >= 3200",
        output_name=Building_N100.polygon_resolve_building_conflicts___building_polygons_final___n100_building.value,
    )


@timing_decorator
def small_building_polygons_to_points():
    """
    Selects small building polygons based on a specified area threshold and transforms them into points.
    """

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.polygon_resolve_building_conflicts___building_polygons_not_invisible_not_intersecting___n100_building.value,
        expression="Shape_Area < 3200",
        output_name=Building_N100.polygon_resolve_building_conflicts___small_building_polygons___n100_building.value,
    )

    # Transforming small polygons to points
    arcpy.management.FeatureToPoint(
        in_features=Building_N100.polygon_resolve_building_conflicts___small_building_polygons___n100_building.value,
        out_feature_class=Building_N100.polygon_resolve_building_conflicts___small_building_polygons_to_point___n100_building.value,
    )


if __name__ == "__main__":
    main()
