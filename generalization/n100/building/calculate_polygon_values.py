# Importing custom files
from file_manager.n100.file_manager_buildings import Building_N100
from constants.n100_constants import N100_SQLResources

# Importing general packages
import arcpy
from collections import Counter

# Importing timing decorator
from custom_tools.timing_decorator import timing_decorator


@timing_decorator("calculate_polygon_values.py")
def main():
    """
    Summary:
        Adds required fields for building point for symbology and resolves building conflicts: angle, hierarchy, and invisibility.
    """

    adding_angle_hierarchy_invisibility_fields()
    adding_symbol_val()


def adding_angle_hierarchy_invisibility_fields():

    # Adding multiple fields
    print("Adding fields...")
    arcpy.management.AddFields(
        in_table=Building_N100.simplify_polygons___spatial_join_polygons___n100_building.value,
        field_description=[
            ["angle", "SHORT"],
            ["hierarchy", "SHORT"],
            ["invisibility", "SHORT"],
        ],
    )

    # Assigning values to the fields
    print("Assigning values to fields...")
    arcpy.management.CalculateFields(
        in_table=Building_N100.simplify_polygons___spatial_join_polygons___n100_building.value,
        expression_type="PYTHON3",
        fields=[
            ["angle", "0"],
            ["hierarchy", "1"],  # Hierachy 1 so buildings can be moved around
            ["invisibility", "0"],
        ],
    )


def adding_symbol_val():

    arcpy.AddField_management(
        in_table=Building_N100.simplify_polygons___spatial_join_polygons___n100_building.value,
        field_name="symbol_val",
        field_type="SHORT",
    )

    # Determining and assigning symbol val
    arcpy.CalculateField_management(
        in_table=Building_N100.simplify_polygons___spatial_join_polygons___n100_building.value,
        field="symbol_val",
        expression="determineVal(!BYGGTYP_NBR!)",
        expression_type="PYTHON3",
        code_block=N100_SQLResources.nbr_symbol_val_code_block.value,
    )

    # Assigning new name to the final building polygons
    print("Making a copy of the feature class...")
    arcpy.management.CopyFeatures(
        Building_N100.simplify_polygons___spatial_join_polygons___n100_building.value,
        Building_N100.calculate_polygon_values___final___n100_building.value,
    )
