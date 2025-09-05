# har tester ViR en måte å gi høyere hierarchy,
# eller eventuelt låse veger som krysser over store veger

import arcpy
from openpyxl.styles.builtins import output

from input_data import input_n50, input_n100
from file_manager.n100.file_manager_roads import Road_N100
from env_setup import environment_setup
from custom_tools.general_tools import custom_arcpy

from input_data import input_roads

from custom_tools.decorators.timing_decorator import timing_decorator


@timing_decorator
def main():
    environment_setup.main()
    shrunk_underpass()
    shrunk_bridge()
    shrunk_surface_road()
    bridge_ER()
    surface_ER()
    cross()
    keep()


@timing_decorator
def shrunk_underpass():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_roads.vegsenterlinje,
        expression="medium='U'",
        output_name=Road_N100.test2___vegsenterlinje_medium_u___n100_road.value,
        selection_type="NEW_SELECTION",
    )

    arcpy.analysis.Buffer(
        in_features=Road_N100.test2___vegsenterlinje_medium_u___n100_road.value,  # FIX: fjernet ekstra _n100_road
        out_feature_class=Road_N100.test2___vegsenterlinje_u_buff100___n100_road.value,
        buffer_distance_or_field="1 meters",
        line_end_type="FLAT",
    )

    arcpy.analysis.Buffer(
        in_features=Road_N100.test2___vegsenterlinje_u_buff100___n100_road.value,
        out_feature_class=Road_N100.test2___shrunk_underpass___n100_road.value,
        buffer_distance_or_field="-50 centimeters",
    )


@timing_decorator
def shrunk_bridge():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_roads.vegsenterlinje,
        expression="medium='L'",
        output_name=Road_N100.test2___vegsenterlinje_medium_l___n100_road.value,
        selection_type="NEW_SELECTION",
    )

    arcpy.analysis.Buffer(
        in_features=Road_N100.test2___vegsenterlinje_medium_l___n100_road.value,
        out_feature_class=Road_N100.test2___vegsenterlinje_l_buff100___n100_road.value,
        buffer_distance_or_field="1 meters",
        line_end_type="FLAT",
    )

    arcpy.analysis.Buffer(
        in_features=Road_N100.test2___vegsenterlinje_l_buff100___n100_road.value,
        out_feature_class=Road_N100.test2___shrunk_bridge___n100_road.value,
        buffer_distance_or_field="-50 centimeters",
    )


@timing_decorator
def shrunk_surface_road():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_roads.vegsenterlinje,
        expression="medium='T'",
        output_name=Road_N100.test2___vegsenterlinje_medium_t___n100_road.value,
        selection_type="NEW_SELECTION",
    )

    # arcpy.analysis.Buffer(
    #     in_features=Road_N100.test2___vegsenterlinje_medium_t___n100_road.value,  # FIX: fjernet ekstra _n100_road
    #     out_feature_class=Road_N100.test2___vegsenterlinje_t_buff100___n100_road.value,
    #     buffer_distance_or_field="1 meters",
    #     line_end_type="FLAT",
    # )
    #
    # arcpy.analysis.Buffer(
    #     in_features=Road_N100.test2___vegsenterlinje_t_buff100___n100_road.value,  # FIX: fjernet ekstra _n100_road
    #     out_feature_class=Road_N100.test2___shrunk_surface_road___n100_road.value,
    #     buffer_distance_or_field="-50 centimeters",
    # )


@timing_decorator
def bridge_ER():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_roads.vegsenterlinje,
        expression="vegkategori IN ('E', 'R')",
        output_name=Road_N100.test2___ER___n100_road.value,
        selection_type="NEW_SELECTION",
    )
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test2___ER___n100_road.value,
        expression="medium='L'",
        output_name=Road_N100.test2___ER_bridge___n100_road.value,
        selection_type="NEW_SELECTION",
    )

    arcpy.analysis.Buffer(
        in_features=Road_N100.test2___ER_bridge___n100_road.value,  # FIX: fjernet ekstra _n100_road
        out_feature_class=Road_N100.test2___ER_bridge_buffer100___n100_road.value,
        buffer_distance_or_field="1 meters",
        line_end_type="FLAT",
    )

    arcpy.analysis.Buffer(
        in_features=Road_N100.test2___ER_bridge_buffer100___n100_road.value,  # FIX: fjernet ekstra _n100_road
        out_feature_class=Road_N100.test2___ER_bridge_shrunk___n100_road.value,
        buffer_distance_or_field="-50 centimeters",
    )


@timing_decorator
def surface_ER():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test2___ER___n100_road.value,
        expression="medium='T'",
        output_name=Road_N100.test2___surface_ER___n100_road.value,
        selection_type="NEW_SELECTION",
    )


@timing_decorator
def select_intersect_and_copy(in_fc, select_fc, out_fc, lyr_name="tmp_lyr"):
    """Lager feature layer, selekterer på intersect og kopierer resultatet"""
    arcpy.management.MakeFeatureLayer(in_features=in_fc, out_layer=lyr_name)
    arcpy.management.SelectLayerByLocation(
        in_layer=lyr_name,
        overlap_type="INTERSECT",
        select_features=select_fc,
        selection_type="NEW_SELECTION",
    )
    arcpy.management.CopyFeatures(in_features=lyr_name, out_feature_class=out_fc)
    arcpy.management.Delete(lyr_name)  # rydder opp det midlertidige laget


@timing_decorator
def cross():
    # Bridges from all categories that cross over ER
    select_intersect_and_copy(
        in_fc=Road_N100.test2___shrunk_bridge___n100_road.value,
        select_fc=Road_N100.test2___surface_ER___n100_road.value,
        out_fc=Road_N100.test2___bridge_cross_ER___n100_road.value,
        lyr_name="shrunk_bridge_lyr",
    )

    # Tunneler under ER
    select_intersect_and_copy(
        in_fc=Road_N100.test2___shrunk_underpass___n100_road.value,
        select_fc=Road_N100.test2___surface_ER___n100_road.value,
        out_fc=Road_N100.test2___underpass_cross_ER___n100_road.value,
        lyr_name="shrunk_underpass_lyr",
    )

    # Veger på bakken som har ER-bru over seg
    select_intersect_and_copy(
        in_fc=Road_N100.test2___vegsenterlinje_medium_t___n100_road.value,
        select_fc=Road_N100.test2___ER_bridge_shrunk___n100_road.value,
        out_fc=Road_N100.test2___surface_under_ER___n100_road.value,
        lyr_name="vegsenterlinje_medium_t_lyr",
    )


@timing_decorator
# select from CROSS those objects that are most important
def keep():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___diss0___n100_road.value,
        expression="medium IN ('U', 'L')",
        output_name=Road_N100.test1___medium_ul0___n100_road.value,
        selection_type="NEW_SELECTION",
    )


if __name__ == "__main__":
    main()
