# Importing packages
import arcpy

from file_manager.n100 import file_manager_rivers
from input_data import input_n100, input_other
from input_data import input_fkb

from composition_configs import core_config, logic_config, type_defs

# Importing custom modules
from file_manager.n100.file_manager_rivers import River_N100
from env_setup import environment_setup
import config
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools.partition_iterator import PartitionIterator
from custom_tools.general_tools.study_area_selector import StudyAreaSelector
from custom_tools.general_tools.geometry_tools import GeometryValidator
from custom_tools.general_tools import custom_arcpy
from custom_tools.general_tools import file_utilities


MERGE_DIVIDED_ROADS_ALTERATIVE = False

AREA_SELECTOR = "vassOmrNr IN ('016')"
SCALE = "n100"


@timing_decorator
def main():
    environment_setup.main()
    arcpy.env.referenceScale = 100000
    data_selection_and_validation(AREA_SELECTOR)
    filter_river_water_features()


@timing_decorator
def data_selection_and_validation(area_selection: str):
    """
    "vassOmrNr IN ('016')"
    """

    selector = StudyAreaSelector(
        input_output_file_dict={
            input_fkb.VannLinje: River_N100.data_selection___water_lines___n100_river.value,
            input_fkb.VannFlate: River_N100.data_selection___water_polygons___n100_river.value,
            input_fkb.VannPunkt: River_N100.data_selection___water_points___n100_river.value,
        },
        selecting_file=input_other.RiverBasins,
        selecting_sql_expression=area_selection,
        select_local=config.select_study_area,
    )

    selector.run()

    # input_features_validation = {
    #     "water_lines": River_N100.data_selection___water_lines___n100_river.value,
    #     "water_polygons": River_N100.data_selection___water_polygons___n100_river.value,
    #     "water_points": River_N100.data_selection___water_points___n100_river.value,
    # }
    # road_data_validation = GeometryValidator(
    #     input_features=input_features_validation,
    #     output_table_path=River_N100.data_preparation___geometry_validation___n100_river.value,
    # )
    # road_data_validation.check_repair_sequence()


@timing_decorator
def filter_river_water_features():
    # Can consider adding 'VeggrøftÅpen' to river line sellection. Byt really questionable.
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=River_N100.data_selection___water_lines___n100_river.value,
        expression="objtype IN ('ElvBekk', 'KanalGrøft', 'Kanalkant', 'KonnekteringVann')",
        output_name=River_N100.data_preparation___river_lines___n100_river.value,
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=River_N100.data_selection___water_lines___n100_river.value,
        expression="objtype IN ('Elvekant', 'Innsjøkant', 'Kanalkant')",
        output_name=River_N100.data_preparation___river_polygon_outline___n100_river.value,
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=River_N100.data_selection___water_polygons___n100_river.value,
        expression="objtype IN ('Elv', 'Innsjø', 'Kanal')",
        output_name=River_N100.data_preparation___river_polygons___n100_river.value,
    )


if __name__ == "__main__":
    main()
