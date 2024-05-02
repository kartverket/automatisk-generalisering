# Importing modules
import arcpy
import time

# Importing custom files
import config
from custom_tools import custom_arcpy

from file_manager.n100.file_manager_buildings import Building_N100


# Importing timing decorator
from custom_tools.timing_decorator import timing_decorator


def main():
    removing_points_in_urban_areas()
    selecting_all_tourist_cabins()
    assigning_final_names()


@timing_decorator
def removing_points_in_urban_areas():

    # Selecting building points that are NOT intersecting with urban areas
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.removing_overlapping_points___final___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.data_preparation___urban_area_selection_n100___n100_building.value,
        inverted=False,
        output_name=Building_N100.finalizing_buildings___points_not_in_urban_areas___n100_building.value,
    )


@timing_decorator
def selecting_all_tourist_cabins():

    selecting_tourist_cabins = "byggtyp_nbr = 956"

    # Selecting all building points categorized as tourist cabins
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.finalizing_buildings___points_not_in_urban_areas___n100_building.value,
        expression=selecting_tourist_cabins,
        output_name=Building_N100.finalizing_buildings___tourist_cabins___n100_building.value,
    )
    # Selecting all other building points (not tourist cabins)
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.finalizing_buildings___points_not_in_urban_areas___n100_building.value,
        expression=selecting_tourist_cabins,
        output_name=Building_N100.finalizing_buildings___all_point_except_tourist_cabins___n100_building.value,
        inverted=True,
    )


@timing_decorator
def assigning_final_names():

    arcpy.management.CopyFeatures(
        Building_N100.Building_N100.finalizing_buildings___tourist_cabins___n100_building.value,
        Building_N100.finalizing_buildings___TuristHytte___n100_building.value,
    )

    arcpy.management.CopyFeatures(
        Building_N100.point_resolve_building_conflicts___final_points_merged___n100_building.value,
        Building_N100.point_resolve_building_conflicts___building_points_final___n100_building.value,
    )
