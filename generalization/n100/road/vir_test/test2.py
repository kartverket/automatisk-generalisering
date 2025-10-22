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
    shrunked_underpass()
    shrunked_bridge()
    shrunked_ER_bridge()
    shrunked_surface_road()
    surface_ER()
    cross()
    keep()
    update_vegstatus()


@timing_decorator
def shrunked_underpass():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_roads.elveg_and_sti,
        expression="medium='U'",
        output_name=Road_N100.test2___veg_u___n100_road.value,
        selection_type="NEW_SELECTION",
    )

    arcpy.analysis.Buffer(
        in_features=Road_N100.test2___veg_u___n100_road.value,  # FIX: fjernet ekstra _n100_road
        out_feature_class=Road_N100.test2___veg_u_poly100___n100_road.value,
        buffer_distance_or_field="1 meters",
        line_end_type="FLAT",
    )

    arcpy.analysis.Buffer(
        in_features=Road_N100.test2___veg_u_poly100___n100_road.value,
        out_feature_class=Road_N100.test2___veg_u_poly100_shrunked___n100_road.value,
        buffer_distance_or_field="-50 centimeters",
    )


@timing_decorator
def shrunked_bridge():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_roads.elveg_and_sti,
        expression="medium='L'",
        output_name=Road_N100.test2___veg_l___n100_road.value,
        selection_type="NEW_SELECTION",
    )

    arcpy.analysis.Buffer(
        in_features=Road_N100.test2___veg_l___n100_road.value,
        out_feature_class=Road_N100.test2___veg_l_poly100___n100_road.value,
        buffer_distance_or_field="1 meters",
        line_end_type="FLAT",
    )

    arcpy.analysis.Buffer(
        in_features=Road_N100.test2___veg_l_poly100___n100_road.value,
        out_feature_class=Road_N100.test2___veg_l_poly100_shrunked___n100_road.value,
        buffer_distance_or_field="-50 centimeters",
    )


@timing_decorator
def shrunked_ER_bridge():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_roads.elveg_and_sti,
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
        out_feature_class=Road_N100.test2___ER_bridge_poly100___n100_road.value,
        buffer_distance_or_field="1 meters",
        line_end_type="FLAT",
    )

    arcpy.analysis.Buffer(
        in_features=Road_N100.test2___ER_bridge_poly100___n100_road.value,  # FIX: fjernet ekstra _n100_road
        out_feature_class=Road_N100.test2___ER_bridge_shrunked___n100_road.value,
        buffer_distance_or_field="-50 centimeters",
    )


@timing_decorator
def shrunked_surface_road():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_roads.elveg_and_sti,
        expression="medium='T'",
        output_name=Road_N100.test2___veg_t___n100_road.value,
        selection_type="NEW_SELECTION",
    )

    # arcpy.analysis.Buffer(
    #     in_features=Road_N100.test2___elveg_and_sti_medium_t___n100_road.value,  # FIX: fjernet ekstra _n100_road
    #     out_feature_class=Road_N100.test2___elveg_and_sti_t_buff100___n100_road.value,
    #     buffer_distance_or_field="1 meters",
    #     line_end_type="FLAT",
    # )
    #
    # arcpy.analysis.Buffer(
    #     in_features=Road_N100.test2___elveg_and_sti_t_buff100___n100_road.value,  # FIX: fjernet ekstra _n100_road
    #     out_feature_class=Road_N100.test2___shrunk_surface_road___n100_road.value,
    #     buffer_distance_or_field="-50 centimeters",
    # )


@timing_decorator
def surface_ER():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test2___ER___n100_road.value,
        expression="medium='T'",
        output_name=Road_N100.test2___ER_t___n100_road.value,
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
        in_fc=Road_N100.test2___veg_l_poly100_shrunked___n100_road.value,
        select_fc=Road_N100.test2___ER_t___n100_road.value,
        out_fc=Road_N100.test2___bridge_cross_ER___n100_road.value,
        lyr_name="veg_l_poly100_shrunked_lyr",
    )

    # Tunneler under ER
    select_intersect_and_copy(
        in_fc=Road_N100.test2___veg_u_poly100_shrunked___n100_road.value,
        select_fc=Road_N100.test2___ER_t___n100_road.value,
        out_fc=Road_N100.test2___underpass_cross_ER___n100_road.value,
        lyr_name="veg_u_poly100_shrunked_lyr",
    )

    # Veger på bakken som har ER-bru over seg
    select_intersect_and_copy(
        in_fc=Road_N100.test2___veg_t___n100_road.value,
        select_fc=Road_N100.test2___ER_bridge_shrunked___n100_road.value,
        out_fc=Road_N100.test2___surface_under_ER___n100_road.value,
        lyr_name="veg_t_lyr",
    )


@timing_decorator
# select from CROSS those objects that are most important
def keep():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test2___bridge_cross_ER___n100_road.value,
        expression="vegkategori IN ('E', 'R', 'F', 'K', 'P')",
        output_name=Road_N100.test2___keep_bru_ERFKP___n100_road.value,
        selection_type="NEW_SELECTION",
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test2___underpass_cross_ER___n100_road.value,
        expression="vegkategori IN ('E', 'R', 'F', 'K', 'P')",
        output_name=Road_N100.test2___keep_underpass_ERFKP___n100_road.value,
        selection_type="NEW_SELECTION",
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test2___surface_under_ER___n100_road.value,
        expression="vegkategori IN ('E', 'R', 'F', 'K', 'P')",
        output_name=Road_N100.test2___keep_surface_ERFKP___n100_road.value,
        selection_type="NEW_SELECTION",
    )


# now, with keep find shares a line segment in elveg and sti and code accordingly
# for example, use vagstatus and code to A for bridges that cross ER and are kategori F, K or P
# give status A, so it can be found and given the desired hierarchy
# vegstatus can the be used so that objects with status A or B change hierarchy


@timing_decorator
def update_vegstatus():
    """Updates VEGSTATUS directly in the original elveg_and_sti dataset
    for features that intersect the 'keep' datasets."""

    print("Updating VEGSTATUS for intersecting features...")

    arcpy.management.Merge(
        inputs=[
            Road_N100.test2___keep_bru_ERFKP___n100_road.value,
            Road_N100.test2___keep_underpass_ERFKP___n100_road.value,
        ],
        output=Road_N100.test2___merged_keep___n100_road.value,
    )

    # Make a feature layer from the input dataset
    arcpy.management.MakeFeatureLayer(
        in_features=input_roads.elveg_and_sti, out_layer="elveg_sti_lyr"
    )
    # Select all features that intersect with the merged keep layer
    arcpy.management.SelectLayerByLocation(
        in_layer="elveg_sti_lyr",
        overlap_type="HAVE_THEIR_CENTER_IN",
        select_features=Road_N100.test2___merged_keep___n100_road.value,
        selection_type="NEW_SELECTION",
    )

    # Update VEGSTATUS for the selected features
    count = 0
    with arcpy.da.UpdateCursor("elveg_sti_lyr", ["VEGSTATUS"]) as cursor:
        for row in cursor:
            row[0] = "A"  # <-- set your desired value here
            cursor.updateRow(row)
            count += 1

    print(f" VEGSTATUS updated to 'A' for {count} features in elveg/sti.")


if __name__ == "__main__":
    main()
