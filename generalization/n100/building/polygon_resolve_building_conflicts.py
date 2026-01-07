import arcpy
from pprint import pprint
import config
from custom_tools.general_tools import custom_arcpy
from custom_tools.general_tools.partition_iterator import PartitionIterator
from custom_tools.general_tools.polygon_processor import PolygonProcessor
from composition_configs import core_config, logic_config

from custom_tools.generalization_tools.building.resolve_building_conflicts import (
    ResolveBuildingConflictsPolygon,
)
from file_manager import work_file_manager
from input_data import input_symbology


# Importing environment settings
from env_setup import environment_setup
from constants.n100_constants import N100_SQLResources, N100_Symbology

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
    hospital_church_points_to_squares()
    resolve_building_conflicts_polygon()
    intersecting_building_polygons_to_point()
    merging_invisible_intersecting_points()
    check_if_building_polygons_are_big_enough()
    small_building_polygons_to_points()


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


def resolve_building_conflicts_polygon():
    """RBC = ResolveBuildingConflicts"""

    building = "building"
    railroad = "railroad"
    road = "road"
    begrensningskurve = "begrensningskurve"
    power_grid_lines = "power_grid_lines"
    hospital_churches = "hospital_churches"
    railroad_station = "railroad_station"

    # rbc is ResolveBuildingConflicts
    rbc_polygons = "rbc_polygons"
    rbc_points = "rbc_points"

    rbc_input_config = core_config.PartitionInputConfig(
        entries=[
            core_config.InputEntry.processing_input(
                object=building,
                path=Building_N100.polygon_propogate_displacement___building_polygons_after_displacement___n100_building.value,
            ),
            core_config.InputEntry.context_input(
                object=railroad,
                path=Building_N100.data_selection___railroad_tracks_n100_input_data___n100_building.value,
            ),
            core_config.InputEntry.context_input(
                object=railroad_station,
                path=Building_N100.data_preparation___railway_stations_to_polygons___n100_building.value,
            ),
            core_config.InputEntry.context_input(
                object=road,
                path=Building_N100.data_preparation___road_symbology_buffers___n100_building.value,
            ),
            core_config.InputEntry.context_input(
                object=begrensningskurve,
                path=Building_N100.data_preparation___processed_begrensningskurve___n100_building.value,
            ),
            core_config.InputEntry.context_input(
                object=power_grid_lines,
                path=Building_N100.data_preparation___power_grid_lines___n100_building.value,
            ),
            core_config.InputEntry.context_input(
                object=hospital_churches,
                path=Building_N100.polygon_resolve_building_conflicts___hospital_church_squares___n100_building.value,
            ),
        ]
    )

    rbc_output_config = core_config.PartitionOutputConfig(
        entries=[
            core_config.OutputEntry.vector_output(
                object=building,
                tag=rbc_polygons,
                path=Building_N100.polygon_resolve_building_conflicts___not_invisible_polygons_after_rbc___n100_building.value,
            ),
            core_config.OutputEntry.vector_output(
                object=building,
                tag=rbc_points,
                path=Building_N100.polygon_resolve_building_conflicts___invisible_polygons_to_points___n100_building.value,
            ),
        ]
    )

    rbc_io_config = core_config.PartitionIOConfig(
        input_config=rbc_input_config,
        output_config=rbc_output_config,
        documentation_directory=Building_N100.rbc_polygon_documentation_n100_building.value,
    )

    polygon_rbc_input_data_structure = [
        logic_config.SymbologyLayerSpec(
            unique_name=building,
            input_feature=core_config.InjectIO(object=building, tag="input"),
            input_lyrx=input_symbology.SymbologyN100.building_polygon.value,
            grouped_lyrx=False,
        ),
        logic_config.SymbologyLayerSpec(
            unique_name=road,
            input_feature=core_config.InjectIO(object=road, tag="input"),
            input_lyrx=input_symbology.SymbologyN100.road_buffer.value,
            grouped_lyrx=False,
        ),
        logic_config.SymbologyLayerSpec(
            unique_name=railroad,
            input_feature=core_config.InjectIO(object=railroad, tag="input"),
            input_lyrx=input_symbology.SymbologyN100.railway.value,
            grouped_lyrx=False,
        ),
        logic_config.SymbologyLayerSpec(
            unique_name=railroad_station,
            input_feature=core_config.InjectIO(object=railroad_station, tag="input"),
            input_lyrx=input_symbology.SymbologyN100.road_buffer.value,
            grouped_lyrx=False,
        ),
        logic_config.SymbologyLayerSpec(
            unique_name=begrensningskurve,
            input_feature=core_config.InjectIO(object=begrensningskurve, tag="input"),
            input_lyrx=input_symbology.SymbologyN100.begrensningskurve_polygon.value,
            grouped_lyrx=False,
        ),
        logic_config.SymbologyLayerSpec(
            unique_name=power_grid_lines,
            input_feature=core_config.InjectIO(object=power_grid_lines, tag="input"),
            input_lyrx=config.symbology_samferdsel,
            grouped_lyrx=True,
            target_layer_name="N100_Samferdsel_senterlinje_veg_anlegg_sort_maske",
        ),
        logic_config.SymbologyLayerSpec(
            unique_name=hospital_churches,
            input_feature=core_config.InjectIO(object=hospital_churches, tag="input"),
            input_lyrx=input_symbology.SymbologyN100.building_polygon.value,
            grouped_lyrx=False,
        ),
    ]

    rbc_polygon_barrier_default_rule = logic_config.BarrierDefault(
        gap_meters=30,
        use_turn_orientation=False,
    )

    rbc_init_config = logic_config.RbcPolygonInitKwargs(
        input_data_structure=polygon_rbc_input_data_structure,
        output_building_polygons=core_config.InjectIO(
            object=building, tag=rbc_polygons
        ),
        output_collapsed_polygon_points=core_config.InjectIO(
            object=building, tag=rbc_points
        ),
        work_file_manager_config=core_config.WorkFileConfig(
            root_file=Building_N100.polygon_resolve_building_conflicts___root_file___n100_building.value
        ),
        building_unique_name=building,
        barrier_default=rbc_polygon_barrier_default_rule,
        barrier_overrides=None,
    )

    polygon_rbc_method = core_config.ClassMethodEntryConfig(
        class_=ResolveBuildingConflictsPolygon,
        method=ResolveBuildingConflictsPolygon.run,
        init_params=rbc_init_config,
    )

    rbc_method_inject_config = core_config.MethodEntriesConfig(
        entries=[polygon_rbc_method]
    )

    rbc_partition_run_config = core_config.PartitionRunConfig(
        max_elements_per_partition=25_000,
        context_radius_meters=500,
    )

    rbc_parition_work_file_manager_config = core_config.WorkFileConfig(
        root_file=Building_N100.polygon_resolve_building_conflicts___partition_root_file___n100_building.value,
        keep_files=True,
    )

    partition_polygon_rbc = PartitionIterator(
        partition_io_config=rbc_io_config,
        partition_method_inject_config=rbc_method_inject_config,
        partition_iterator_run_config=rbc_partition_run_config,
        work_file_manager_config=rbc_parition_work_file_manager_config,
    )

    partition_polygon_rbc.run()


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
