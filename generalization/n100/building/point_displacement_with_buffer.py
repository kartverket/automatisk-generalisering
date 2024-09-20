# Importing packages
import arcpy
import os

from input_data import input_n100
from file_manager.n100.file_manager_buildings import Building_N100
from constants.n100_constants import N100_Symbology, N100_SQLResources, N100_Values

import env_setup.global_config
from custom_tools.general_tools.polygon_processor import PolygonProcessor
from custom_tools.general_tools.partition_iterator import PartitionIterator
from custom_tools.generalization_tools.building.buffer_displacement import (
    BufferDisplacement,
)
from env_setup import environment_setup
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools import custom_arcpy


@timing_decorator
def main():
    """
    What:
        Displaces building points relative to road buffers based on specified buffer increments.
        It processes multiple features, mainly focusing on roads taking into account varied symbology width for roads,
        displacing building points away from roads and other barriers, while iteratively calculating buffer increments.

    How:
        Selects hospitals, churches and tourist huts so that they are not potentially lost in the buffer displacement process.
        Then runs the buffer displacement logic on the remaining points (see `BufferDisplacement` documentation for more details.
        Finally merges the output of the BufferDisplacement with the previous hospital, church and tourist hut selection.

    Why:
        To make sure there are no graphic conflicts with buildings and roads prior to RBC improving the result of RBC,
        but also the processing speed.
    """
    environment_setup.main()

    extracting_churches_hospitals()
    buffer_displacement()
    merge_church_hospitals_buffer_displaced_points()


@timing_decorator
def extracting_churches_hospitals():
    """
    Selects and saves features identified as churches or hospitals based on `symbol_val`.
    Separates out features that are not churches or hospitals.
    """
    church_hospital_tourist_hut_sql_expression = (
        "symbol_val IN (1, 2, 3) Or byggtyp_nbr = 956"
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.hospital_church_clusters___final___n100_building.value,
        expression=church_hospital_tourist_hut_sql_expression,
        output_name=Building_N100.point_displacement_with_buffer___church_hospital_selection___n100_building.value,
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.hospital_church_clusters___final___n100_building.value,
        expression=church_hospital_tourist_hut_sql_expression,
        output_name=Building_N100.point_displacement_with_buffer___building_points_selection___n100_building.value,
        inverted=True,
    )


@timing_decorator
def buffer_displacement():
    """
    What:
        Displaces building points relative to road buffers based on specified buffer increments.
        It processes multiple features, mainly focusing on roads taking into account varied symbology width for roads,
        displacing building points away from roads and other barriers, while iteratively calculating buffer increments.

    How:
        Runs the BufferDisplacement using the PartitionIterator. See `BufferDisplacement` documentation for more details.
    """
    building_points = "building_points"
    bane = "bane"
    river = "river"
    train_stations = "train_stations"
    urban_area = "urban_area"
    roads = "roads"

    inputs = {
        building_points: [
            "input",
            Building_N100.point_displacement_with_buffer___building_points_selection___n100_building.value,
        ],
        roads: [
            "input",
            Building_N100.data_preparation___unsplit_roads___n100_building.value,
        ],
        river: [
            "context",
            Building_N100.data_preparation___processed_begrensningskurve___n100_building.value,
        ],
        urban_area: [
            "context",
            Building_N100.data_preparation___urban_area_selection_n100___n100_building.value,
        ],
        train_stations: [
            "context",
            Building_N100.data_selection___railroad_stations_n100_input_data___n100_building.value,
        ],
        bane: [
            "context",
            Building_N100.data_selection___railroad_tracks_n100_input_data___n100_building.value,
        ],
    }

    outputs = {
        building_points: [
            "buffer_displacement",
            Building_N100.point_displacement_with_buffer___displaced_building_points___n100_building.value,
        ],
    }
    misc_objects = {
        "begrensningskurve": [
            ("river", "context"),
            0,
        ],
        "urban_areas": [
            ("urban_area", "context"),
            1,
        ],
        "bane_station": [
            ("train_stations", "context"),
            1,
        ],
        "bane_lines": [
            ("bane", "context"),
            1,
        ],
    }

    buffer_displacement_config = {
        "class": BufferDisplacement,
        "method": "run",
        "params": {
            "input_road_lines": ("roads", "input"),
            "input_building_points": ("building_points", "input"),
            "input_misc_objects": misc_objects,
            "output_building_points": ("building_points", "buffer_displacement"),
            "sql_selection_query": N100_SQLResources.road_symbology_size_sql_selection.value,
            "root_file": Building_N100.point_displacement_with_buffer___root_file___n100_building.value,
            "building_symbol_dimensions": N100_Symbology.building_symbol_dimensions.value,
            "buffer_displacement_meter": N100_Values.buffer_clearance_distance_m.value,
            "write_work_files_to_memory": False,
            "keep_work_files": False,
        },
    }

    buffer_displacement_partition_iteration = PartitionIterator(
        alias_path_data=inputs,
        alias_path_outputs=outputs,
        custom_functions=[buffer_displacement_config],
        root_file_partition_iterator=Building_N100.point_displacement_with_buffer___root_file___n100_building.value,
        dictionary_documentation_path=Building_N100.point_displacement_with_buffer___documentation___building_n100.value,
        feature_count="1400000",
    )

    buffer_displacement_partition_iteration.run()


@timing_decorator
def merge_church_hospitals_buffer_displaced_points():
    arcpy.management.Merge(
        inputs=[
            Building_N100.point_displacement_with_buffer___church_hospital_selection___n100_building.value,
            Building_N100.point_displacement_with_buffer___displaced_building_points___n100_building.value,
        ],
        output=Building_N100.point_displacement_with_buffer___merged_buffer_displaced_points___n100_building.value,
    )


if __name__ == "__main__":
    main()
