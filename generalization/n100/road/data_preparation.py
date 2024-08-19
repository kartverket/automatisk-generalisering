# Importing packages
import arcpy

# Importing custom input files modules
from input_data import input_n50
from input_data import input_n100
from input_data import input_other

# Importing custom modules
from file_manager.n100.file_manager_roads import Road_N100
from env_setup import environment_setup
import env_setup.global_config
import config
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools import custom_arcpy
from custom_tools.general_tools.polygon_processor import PolygonProcessor
from custom_tools.general_tools.line_to_buffer_symbology import LineToBufferSymbology
from input_data.input_symbology import SymbologyN100
from constants.n100_constants import N100_Symbology, N100_SQLResources, N100_Values


def main():
    environment_setup.main()
    selecting_paths_from_n50()
    adding_fields_to_n50_paths_and_calculating_hierarchy()
    selecting_vegtrase_and_kjorebane_from_nvdb()
    selecting_everything_but_rampe()
    adding_fields_and_calculating_values()


def selecting_paths_from_n50():
    # Selecting paths (stier) from n50
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n50.VegSti,
        expression="objtype = 'VegSenterlinje'",
        output_name=Road_N100.data_preperation___paths_n50___n100_road.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
        inverted=True,
    )


def adding_fields_to_n50_paths_and_calculating_hierarchy():
    # Adding fields to the table
    arcpy.management.AddFields(
        in_table=Road_N100.data_preperation___paths_n50___n100_road.value,
        field_description=[
            ["invisibility", "SHORT"],
            ["hierarchy", "SHORT"],
            ["characters", "SHORT"],
        ],
    )

    # Defining the Python code for field calculation
    assign_hierarchy_to_n50_paths = """
def Reclass(subtypekode):
    if subtypekode in [6, 8, 10, 7]:
        return 1
    elif subtypekode in [11, 9]:
        return 2
    else:
        return 3
"""

    # Applying the field calculation using the custom function
    arcpy.management.CalculateField(
        in_table=Road_N100.data_preperation___paths_n50___n100_road.value,
        field="hierarchy",
        expression="Reclass(!subtypekode!)",
        expression_type="PYTHON3",
        code_block=assign_hierarchy_to_n50_paths,
    )

    arcpy.CalculateField_management(
        in_table=Road_N100.data_preperation___paths_n50___n100_road.value,
        field="hierarchy",
        expression="Reclass(!subtypekode!)",
        expression_type="PYTHON3",
        code_block=assign_hierarchy_to_n50_paths,
    )


def selecting_vegtrase_and_kjorebane_from_nvdb():
    # Selecting all hospitals and making feature layer
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=config.path_to_roads_nvdb,  # Input nvdb
        expression="DETALJNIVÅ = 'Vegtrase' Or DETALJNIVÅ = 'Vegtrase og kjørebane'",
        output_name=Road_N100.data_preperation___selecting_vegtrase_and_kjorebane_nvdb___n100_road.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )


def selecting_everything_but_rampe():
    # Selecting all hospitals and making feature layer
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.data_preperation___selecting_vegtrase_and_kjorebane_nvdb___n100_road.value,
        expression="TYPEVEG = 'rampe'",
        output_name=Road_N100.data_preperation___selecting_everything_but_rampe_nvdb___n100_road.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
        inverted=True,
    )


def adding_fields_and_calculating_values():
    arcpy.management.AddFields(
        in_table=Road_N100.data_preperation___selecting_everything_but_rampe_nvdb___n100_road.value,
        field_description=[
            ["invisibility", "SHORT"],
            ["hierarchy", "SHORT"],
            ["merge", "LONG"],
            ["characters", "SHORT"],
        ],
    )

    arcpy.CalculateField_management(
        in_table=Road_N100.data_preperation___selecting_everything_but_rampe_nvdb___n100_road.value,
        field="merge",
        expression="!vegnummer!",
        expression_type="PYTHON3",
    )

    arcpy.CalculateField_management(
        in_table=Road_N100.data_preperation___selecting_everything_but_rampe_nvdb___n100_road.value,
        field="characters",
        expression="!character!",
        expression_type="PYTHON3",
    )

    assign_hierarchy_to_road_types = """def Reclass(road_category):
        if road_category in ['Europaveg', 'Riksveg', 'Fylkesveg']:
            return 1
        elif road_category == 'Kommunal veg':
            return 2
        elif road_category == 'Privat veg':
            return 3
        elif road_category == 'Skogsveg':
            return 4
        else:
            return 5
    """

    arcpy.management.CalculateField(
        in_table=Road_N100.data_preperation___selecting_everything_but_rampe_nvdb___n100_road.value,
        field="hierarchy",
        expression="Reclass(!VEGSYSTEM_VEGKATEGORI!)",
        expression_type="PYTHON3",
        code_block=assign_hierarchy_to_road_types,
    )

    arcpy.management.CopyFeatures(
        Road_N100.data_preperation___selecting_everything_but_rampe_nvdb___n100_road.value,
        Road_N100.data_preperation___selecting_everything_but_rampe_with_calculated_fields_nvdb___n100_road.value,
    )


if __name__ == "__main__":
    main()
