# Importing packages
import arcpy
import os


# Importing custom input files modules
from input_data import input_n50
from input_data import input_n100
from input_data import input_other
from input_data import input_elveg
from input_data import input_roads

# Importing custom modules
from file_manager.n100.file_manager_roads import Road_N100
from env_setup import environment_setup
import env_setup.global_config
import config
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.decorators.partition_io_decorator import partition_io_decorator
from custom_tools.general_tools.partition_iterator import PartitionIterator
from custom_tools.general_tools.study_area_selector import StudyAreaSelector
from custom_tools.general_tools import custom_arcpy
from custom_tools.general_tools import file_utilities
from custom_tools.general_tools.polygon_processor import PolygonProcessor
from custom_tools.general_tools.line_to_buffer_symbology import LineToBufferSymbology
from input_data.input_symbology import SymbologyN100
from constants.n100_constants import (
    N100_Symbology,
    N100_SQLResources,
    N100_Values,
    NvdbAlias,
    MediumAlias,
)


@timing_decorator
def main():
    environment_setup.main()

    file_utilities.deleting_added_field_from_feature_to_x(
        input_feature=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_medium_t_kryss___n100_road.value
    )

    arcpy.env.referenceScale = 100000
    data_selection()
    table_management()
    dissolve_merge_and_reduce_roads()
    manage_intersections()

    # thin_roadnetwork()


@timing_decorator
def data_selection():
    selector = StudyAreaSelector(
        input_output_file_dict={
            input_roads.roads: Road_N100.data_selection___nvdb_roads___n100_road.value,
        },
        selecting_file=input_n100.AdminFlate,
        selecting_sql_expression="navn IN ('Oslo', 'Ringerike')",
        select_local=config.select_study_area,
    )

    selector.run()


@timing_decorator
def table_management():
    reclassify_missing_vegnummer = """def Reclass(value):
        if value is None:
            return -99
        else:
            return value
    """

    arcpy.management.CalculateField(
        in_table=Road_N100.data_selection___nvdb_roads___n100_road.value,
        field="VEGNUMMER",
        expression="Reclass(!VEGNUMMER!)",
        expression_type="PYTHON3",
        code_block=reclassify_missing_vegnummer,
    )

    arcpy.management.AddFields(
        in_table=Road_N100.data_selection___nvdb_roads___n100_road.value,
        field_description=[
            ["invisibility", "SHORT"],
            ["hierarchy", "SHORT"],
            ["character", "SHORT"],
        ],
    )

    assign_hierarchy_to_nvdb_roads = f"""def Reclass(VEGKATEGORI):
        if VEGKATEGORI == '{NvdbAlias.europaveg}':
            return 1
        elif VEGKATEGORI in ['{NvdbAlias.riksveg}', '{NvdbAlias.fylkesveg}']:
            return 2
        elif VEGKATEGORI == '{NvdbAlias.kommunalveg}':
            return 3
        elif VEGKATEGORI == '{NvdbAlias.privatveg}':
            return 4
        elif VEGKATEGORI == '{NvdbAlias.skogsveg}':
            return 5
        
        else:
            return 5
    """

    arcpy.management.CalculateField(
        in_table=Road_N100.data_selection___nvdb_roads___n100_road.value,
        field="hierarchy",
        expression="Reclass(!VEGKATEGORI!)",
        expression_type="PYTHON3",
        code_block=assign_hierarchy_to_nvdb_roads,
    )

    reclassify_null_values = f"""def Reclass(VEGKATEGORI):
        if VEGKATEGORI is None:
            return 5
        else:
            return VEGKATEGORI
    """

    arcpy.management.CalculateField(
        in_table=Road_N100.data_selection___nvdb_roads___n100_road.value,
        field="hierarchy",
        expression="Reclass(!VEGKATEGORI!)",
        expression_type="PYTHON3",
        code_block=reclassify_null_values,
    )

    define_character_field = f"""def Reclass(TYPEVEG):
        if TYPEVEG == 'rundkjøring':
            return 0
        elif TYPEVEG in 'kanalisertVeg':
            return 1
        elif TYPEVEG == 'rampe':
            return 2
        else: 
            return 999
    """

    arcpy.management.CalculateField(
        in_table=Road_N100.data_selection___nvdb_roads___n100_road.value,
        field="character",
        expression="Reclass(!TYPEVEG!)",
        expression_type="PYTHON3",
        code_block=define_character_field,
    )

    arcpy.management.CalculateField(
        in_table=Road_N100.data_selection___nvdb_roads___n100_road.value,
        field="invisibility",
        expression=0,
    )


@timing_decorator
def dissolve_merge_and_reduce_roads():
    arcpy.management.MultipartToSinglepart(
        in_features=Road_N100.data_selection___nvdb_roads___n100_road.value,
        out_feature_class=Road_N100.data_preparation___road_single_part___n100_road.value,
    )

    arcpy.analysis.PairwiseDissolve(
        in_features=Road_N100.data_preparation___road_single_part___n100_road.value,
        out_feature_class=Road_N100.data_preparation___dissolved_road_feature___n100_road.value,
        dissolve_field=[
            "OBJTYPE",
            "TYPEVEG",
            "MEDIUM",
            "VEGFASE",
            "VEGKATEGORI",
            "VEGNUMMER",
            "SUBTYPEKODE",
            "character",
        ],
        multi_part="SINGLE_PART",
    )

    arcpy.cartography.MergeDividedRoads(
        in_features=Road_N100.data_preparation___dissolved_road_feature___n100_road.value,
        merge_field="VEGNUMMER",
        merge_distance="100 Meters",
        out_features=Road_N100.data_preparation___merge_divided_roads___n100_road.value,
        out_displacement_features=Road_N100.data_preparation___merge_divided_roads_displacement_feature___n100_road.value,
        character_field="character",
    )

    arcpy.management.CopyFeatures(
        in_features=Road_N100.data_preparation___merge_divided_roads___n100_road.value,
        out_feature_class=Road_N100.data_preparation___remove_small_road_lines___n100_road.value,
    )

    arcpy.topographic.RemoveSmallLines(
        in_features=Road_N100.data_preparation___remove_small_road_lines___n100_road.value,
        minimum_length="100 meters",
    )


def manage_intersections():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.data_preparation___remove_small_road_lines___n100_road.value,
        expression=f"MEDIUM IN ('{MediumAlias.on_surface}', '{MediumAlias.bridge}')",
        output_name=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_medium_ul___n100_road.value,
        selection_type="NEW_SELECTION",
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.data_preparation___remove_small_road_lines___n100_road.value,
        expression=f" MEDIUM = '{MediumAlias.tunnel}'",
        output_name=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_medium_t___n100_road.value,
        selection_type="NEW_SELECTION",
    )

    arcpy.management.FeatureToLine(
        in_features=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_medium_t___n100_road.value,
        out_feature_class=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_medium_t_kryss___n100_road.value,
    )

    file_utilities.deleting_added_field_from_feature_to_x(
        input_feature=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_medium_t_kryss___n100_road.value
    )

    arcpy.management.Append(
        inputs=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_medium_ul___n100_road.value,
        target=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_medium_t_kryss___n100_road.value,
    )


if __name__ == "__main__":
    main()
