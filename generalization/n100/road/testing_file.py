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


@timing_decorator
def main():
    environment_setup.main()
    # adding_fields_to_roads()
    # multipart_to_singlepart()
    # give_vegnummer_to_paths()
    # calculate_values_for_merge_divided_roads()
    # merge_divided_roads()
    # calculate_hierarchy_for_thin_road_network()
    thin_road_network_500_straight_to_3000()
    thin_road_network_500_to_1000_to_2000_to_3000()
    thinning_out_kommunal_veg_500_3000()


@timing_decorator
def adding_fields_to_roads():
    arcpy.management.CopyFeatures(
        config.path_to_roads_nvdb,
        Road_N100.testing_file___roads_copy___n100_road.value,
    )
    arcpy.management.AddFields(
        in_table=Road_N100.testing_file___roads_copy___n100_road.value,
        field_description=[
            ["invisibility_500", "SHORT"],  # used for both of the functions
            ["invisibility_3000_1", "SHORT"],
            ["invisibility_1000", "SHORT"],
            ["invisibility_2000", "SHORT"],
            ["invisibility_3000_2", "SHORT"],
            ["invisibility_kommunal_veg", "SHORT"],
            ["hierarchy_kommunal_veg", "SHORT"],
            ["hierarchy", "SHORT"],
            ["merge_field", "LONG"],
            ["character", "SHORT"],
        ],
    )


@timing_decorator
def multipart_to_singlepart():
    """
    This tool is useful when you need to break up multipart geometries
     into their individual geometries for further analysis or processing.
     For example, in road networks, you may want to analyze each
      road segment individually rather than as part of a larger multipart feature.
    """
    arcpy.management.MultipartToSinglepart(
        in_features=Road_N100.testing_file___roads_copy___n100_road.value,
        out_feature_class=Road_N100.testing_file___multipart_to_singlepart___n100_road.value,
    )


def give_vegnummer_to_paths():
    arcpy.management.CalculateField(
        in_table=Road_N100.testing_file___multipart_to_singlepart___n100_road.value,
        field="VEGNUMMER",
        expression="1 if !VEGNUMMER! is None else !VEGNUMMER!",
        expression_type="PYTHON3",
    )


@timing_decorator
def calculate_values_for_merge_divided_roads():
    # Calculate field for merge
    arcpy.management.CalculateField(
        in_table=Road_N100.testing_file___multipart_to_singlepart___n100_road.value,
        field="merge_field",
        expression="!VEGNUMMER!",
        expression_type="PYTHON3",
    )

    assign_character_to_vegtrase = """def Reclass(TYPEVEG):
        if TYPEVEG == 'rundkjøring':
            return 0
        elif TYPEVEG == 'rampe':
            return 2
        elif TYPEVEG == 'enkelBilveg':
            return 1
        elif TYPEVEG == 'kanalisertVeg':
            return 1
        else:
            return 1
    """

    # Calculate field for character
    arcpy.management.CalculateField(
        in_table=Road_N100.testing_file___multipart_to_singlepart___n100_road.value,
        field="character",
        expression="Reclass(!TYPEVEG!)",
        expression_type="PYTHON3",
        code_block=assign_character_to_vegtrase,
    )


@timing_decorator
def merge_divided_roads():
    """
    Road character field:

    Field values are assessed as follows:

    0—Traffic circles or roundabouts
    1—Carriageways, boulevards, dual-lane highways, or other parallel trending roads
    2—On- or off-ramps, highway intersection connectors
    999—Features will not be merged
    """
    # Execute Merge Divided Roads
    arcpy.cartography.MergeDividedRoads(
        in_features=Road_N100.testing_file___multipart_to_singlepart___n100_road.value,
        merge_field="VEGNUMMER",
        merge_distance="50 Meters",
        out_features=Road_N100.testing_file___merge_divided_roads_output___n100_road.value,
        out_displacement_features=Road_N100.first_generalization____merge_divided_roads_displacement_feature___n100_road.value,
        character_field="character",
    )


def calculate_hierarchy_for_thin_road_network():
    assign_hierarchy_to_nvdb_roads = """def Reclass(VEGKATEGORI):
        if VEGKATEGORI == 'E':  # Europaveg
            return 1
        elif VEGKATEGORI == 'R':  # Riksveg
            return 2
        elif VEGKATEGORI == 'K':  # Kommunalveg
            return 3
        elif VEGKATEGORI == 'P':  # Privatveg
            return 4
        elif VEGKATEGORI in ['D', 'A', 'U', 'G', 'T']:  # Sti, Gang- og sykkelveg, Traktorveg
            return 5
        else:
            return 5
"""

    # Calculate field for hierarchy
    arcpy.management.CalculateField(
        in_table=Road_N100.testing_file___merge_divided_roads_output___n100_road.value,
        field="hierarchy",
        expression="Reclass(!VEGKATEGORI!)",
        expression_type="PYTHON3",
        code_block=assign_hierarchy_to_nvdb_roads,
    )


@timing_decorator
def thin_road_network_500_straight_to_3000():
    arcpy.management.CopyFeatures(
        Road_N100.testing_file___merge_divided_roads_output___n100_road.value,
        Road_N100.testing_file___road_input_500_straight_to_3000___n100_road.value,
    )

    # 500
    arcpy.env.referenceScale = "100000"
    arcpy.cartography.ThinRoadNetwork(
        in_features=Road_N100.testing_file___road_input_500_straight_to_3000___n100_road.value,
        minimum_length="500 Meters",
        invisibility_field="invisibility_500",
        hierarchy_field="hierarchy",
    )
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.testing_file___road_input_500_straight_to_3000___n100_road.value,
        expression="invisibility_500 = 0",
        output_name=Road_N100.testing_file___thin_road_network_500_visible_features___n100_road.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )

    # 3000

    arcpy.env.referenceScale = "100000"
    arcpy.cartography.ThinRoadNetwork(
        in_features=Road_N100.testing_file___thin_road_network_500_visible_features___n100_road.value,
        minimum_length="3000 Meters",
        invisibility_field="invisibility_3000_1",
        hierarchy_field="hierarchy",
    )
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.testing_file___thin_road_network_500_visible_features___n100_road.value,
        expression="invisibility_3000_1 = 0",
        output_name=Road_N100.testing_file___thin_road_network_3000_1___n100_road.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )


@timing_decorator
def thin_road_network_500_to_1000_to_2000_to_3000():
    # 500
    arcpy.management.CopyFeatures(
        Road_N100.testing_file___thin_road_network_500_visible_features___n100_road.value,  # 500 m from the first function
        Road_N100.testing_file___road_input_500_1000_2000_3000___n100_road.value,
    )

    # 1000
    arcpy.env.referenceScale = "100000"
    arcpy.cartography.ThinRoadNetwork(
        in_features=Road_N100.testing_file___road_input_500_1000_2000_3000___n100_road.value,
        minimum_length="1000 Meters",
        invisibility_field="invisibility_1000",
        hierarchy_field="hierarchy",
    )
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.testing_file___road_input_500_1000_2000_3000___n100_road.value,
        expression="invisibility_1000 = 0",
        output_name=Road_N100.testing_file___thin_road_network_1000___n100_road.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )

    # 2000
    arcpy.env.referenceScale = "100000"
    arcpy.cartography.ThinRoadNetwork(
        in_features=Road_N100.testing_file___thin_road_network_1000___n100_road.value,
        minimum_length="2000 Meters",
        invisibility_field="invisibility_2000",
        hierarchy_field="hierarchy",
    )
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.testing_file___thin_road_network_1000___n100_road.value,
        expression="invisibility_2000 = 0",
        output_name=Road_N100.testing_file___thin_road_network_2000___n100_road.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )

    # 3000

    arcpy.env.referenceScale = "100000"
    arcpy.cartography.ThinRoadNetwork(
        in_features=Road_N100.testing_file___thin_road_network_2000___n100_road.value,
        minimum_length="3000 Meters",
        invisibility_field="invisibility_3000_2",
        hierarchy_field="hierarchy",
    )
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.testing_file___thin_road_network_2000___n100_road.value,
        expression="invisibility_3000_2 = 0",
        output_name=Road_N100.testing_file___thin_road_network_3000_2___n100_road.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )


def thinning_out_kommunal_veg():
    arcpy.management.CopyFeatures(
        Road_N100.testing_file___thin_road_network_3000_2___n100_road.value,
        Road_N100.testing_file___thinning_kommunal_veg___n100_road.value,
    )

    thinning_kommunal_veg = """
def Reclass(VEGKATEGORI):
    if VEGKATEGORI == 'E':  # Europaveg
        return 1
    elif VEGKATEGORI == 'R':  # Riksveg
        return 2
    elif VEGKATEGORI == 'P':  # Privatveg
        return 3
    elif VEGKATEGORI in ['D', 'A', 'U', 'G', 'T']:  # Sti, Gang- og sykkelveg, Traktorveg
        return 4
    elif VEGKATEGORI == 'K':  # Kommunalveg
        return 5
    else:
        return 5
"""

    # Calculate field for hierarchy
    arcpy.management.CalculateField(
        in_table=Road_N100.testing_file___thinning_kommunal_veg___n100_road.value,
        field="hierarchy_kommunal_veg",
        expression="Reclass(!VEGKATEGORI!)",
        expression_type="PYTHON3",
        code_block=thinning_kommunal_veg,
    )

    arcpy.env.referenceScale = "100000"
    arcpy.cartography.ThinRoadNetwork(
        in_features=Road_N100.testing_file___thinning_kommunal_veg___n100_road.value,
        minimum_length="500 Meters",
        invisibility_field="invisibility_kommunal_veg",
        hierarchy_field="hierarchy_kommunal_veg",
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.testing_file___thinning_kommunal_veg___n100_road.value,
        expression="invisibility_kommunal_veg = 0",
        output_name=Road_N100.testing_file___thinning_kommunal_veg_visible_roads___n100_road.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )


def thinning_out_kommunal_veg_500_3000():
    arcpy.management.CopyFeatures(
        Road_N100.testing_file___thin_road_network_3000_1___n100_road.value,
        Road_N100.testing_file___thinning_kommunal_veg___n100_road.value,
    )

    thinning_kommunal_veg = """
def Reclass(VEGKATEGORI):
    if VEGKATEGORI == 'E':  # Europaveg
        return 1
    elif VEGKATEGORI == 'R':  # Riksveg
        return 2
    elif VEGKATEGORI == 'P':  # Privatveg
        return 3
    elif VEGKATEGORI in ['D', 'A', 'U', 'G', 'T']:  # Sti, Gang- og sykkelveg, Traktorveg
        return 4
    elif VEGKATEGORI == 'K':  # Kommunalveg
        return 5
    else:
        return 5
"""

    # Calculate field for hierarchy
    arcpy.management.CalculateField(
        in_table=Road_N100.testing_file___thinning_kommunal_veg___n100_road.value,
        field="hierarchy_kommunal_veg",
        expression="Reclass(!VEGKATEGORI!)",
        expression_type="PYTHON3",
        code_block=thinning_kommunal_veg,
    )

    arcpy.env.referenceScale = "100000"
    arcpy.cartography.ThinRoadNetwork(
        in_features=Road_N100.testing_file___thinning_kommunal_veg___n100_road.value,
        minimum_length="500 Meters",
        invisibility_field="invisibility_kommunal_veg",
        hierarchy_field="hierarchy_kommunal_veg",
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.testing_file___thinning_kommunal_veg___n100_road.value,
        expression="invisibility_kommunal_veg = 0",
        output_name=Road_N100.testing_file___thinning_kommunal_veg_visible_roads___n100_road.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )


if __name__ == "__main__":
    main()
