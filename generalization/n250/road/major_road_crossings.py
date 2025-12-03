# Importing packages
import arcpy

arcpy.env.overwriteOutput = True

# Importing custom modules
from file_manager.n250.file_manager_roads import Road_N250
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools import custom_arcpy

data_files = {
    # Stores all the relevant file paths to the geodata used in this Python file
    "input": Road_N250.data_selection___nvdb_roads___n250_road.value,
    "road_u": Road_N250.major_road_crossing__road_u__n250_road.value,
    "buffer_u": Road_N250.major_road_crossing__road_u_buffer__n250_road.value,
    "buffer_u_shrunked": Road_N250.major_road_crossing__road_u_buffer_shrunked__n250_road.value,
    "road_l": Road_N250.major_road_crossing__road_l__n250_road.value,
    "buffer_l": Road_N250.major_road_crossing__road_l_buffer__n250_road.value,
    "buffer_l_shrunked": Road_N250.major_road_crossing__road_l_buffer_shrunked__n250_road.value,
    "major_road": Road_N250.major_road_crossing__ER__n250_road.value,
    "major_road_bridge": Road_N250.major_road_crossing__ER_bridge__n250_road.value,
    "major_road_buffer": Road_N250.major_road_crossing__ER_bridge_buffer__n250_road.value,
    "major_road_shrunked": Road_N250.major_road_crossing__ER_bridge_shrunked__n250_road.value,
    "road_t": Road_N250.major_road_crossing__road_t__n250_road.value,
    "major_road_t": Road_N250.major_road_crossing__ER_t__n250_road.value,
    "bridge_cross_ER": Road_N250.major_road_crossing__bridge_cross_ER__n250_road.value,
    "underpass_cross_ER": Road_N250.major_road_crossing__underpass_cross_ER__n250_road.value,
    "surface_under_ER": Road_N250.major_road_crossing__surface_under_ER__n250_road.value,
    "keep_bru": Road_N250.major_road_crossing__keep_bru_ERFKP__n250_road.value,
    "keep_underpass": Road_N250.major_road_crossing__keep_underpass_ERFKP__n250_road.value,
    "keep_surface": Road_N250.major_road_crossing__keep_surface_ERFKP__n250_road.value,
    "merged_keep": Road_N250.major_road_crossing__merged_keep__n250_road.value,
    "output": Road_N250.major_road_crossing__output__n250_road.value,
}


@timing_decorator
def categories_major_road_crossings():
    """
    Creates major road crossings feature classes and updates the attribute 'er_kryssningspunkt'
    in the input road feature class for all roads that cross major roads (E and R).
    """
    print()
    shrunked_underpass()
    shrunked_bridge()
    shrunked_ER_bridge()
    surface_road()
    surface_ER()
    cross()
    keep()
    update_crossing_point_attribute()

    # Deletes all the intermediate files created during the process
    delete_intermediate_files()
    print()


##################
# Help functions
##################


def select_intersect_and_copy(
    in_fc: str, select_fc: str, out_fc: str, lyr_name: str = "tmp_lyr"
) -> None:
    """
    Creates a feature layer from 'in_fc', selects all features that intersect with 'select_fc', and
    copies the selected features to 'out_fc'.

    Args:
        in_fc (str): Input feature class to create a feature layer from
        select_fc (str): Feature class to select intersecting features from 'in_fc'
        out_fc (str): Output feature class to store the selected features
        lyr_name (str): Name of the temporary feature layer. Default is "tmp_lyr"
    """
    arcpy.management.MakeFeatureLayer(in_features=in_fc, out_layer=lyr_name)
    arcpy.management.SelectLayerByLocation(
        in_layer=lyr_name,
        overlap_type="INTERSECT",
        select_features=select_fc,
        selection_type="NEW_SELECTION",
    )
    arcpy.management.CopyFeatures(in_features=lyr_name, out_feature_class=out_fc)
    arcpy.management.Delete(lyr_name)  # Cleans up the temporary layer


##################
# Main functions
##################


@timing_decorator
def shrunked_underpass() -> None:
    """
    Creates shrunked buffers for roads with medium 'U' (underpass).
    """
    road_fc = data_files["input"]
    road_u_fc = data_files["road_u"]
    buffer_fc = data_files["buffer_u"]
    shrunked_fc = data_files["buffer_u_shrunked"]

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=road_fc,
        expression="medium='U'",
        output_name=road_u_fc,
        selection_type="NEW_SELECTION",
    )

    arcpy.analysis.Buffer(
        in_features=road_u_fc,
        out_feature_class=buffer_fc,
        buffer_distance_or_field="1 meters",
        line_end_type="FLAT",
    )

    arcpy.analysis.Buffer(
        in_features=buffer_fc,
        out_feature_class=shrunked_fc,
        buffer_distance_or_field="-50 centimeters",
    )


@timing_decorator
def shrunked_bridge() -> None:
    """
    Creates shrunked buffers for roads with medium 'L' (bridge).
    """
    road_fc = data_files["input"]
    road_l_fc = data_files["road_l"]
    buffer_fc = data_files["buffer_l"]
    shrunked_fc = data_files["buffer_l_shrunked"]

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=road_fc,
        expression="medium='L'",
        output_name=road_l_fc,
        selection_type="NEW_SELECTION",
    )

    arcpy.analysis.Buffer(
        in_features=road_l_fc,
        out_feature_class=buffer_fc,
        buffer_distance_or_field="1 meters",
        line_end_type="FLAT",
    )

    arcpy.analysis.Buffer(
        in_features=buffer_fc,
        out_feature_class=shrunked_fc,
        buffer_distance_or_field="-50 centimeters",
    )


@timing_decorator
def shrunked_ER_bridge() -> None:
    """
    Creates shrunked buffers for major roads with medium 'L' (bridge).
    """
    road_fc = data_files["input"]
    main_road_fc = data_files["major_road"]
    main_road_bridge_fc = data_files["major_road_bridge"]
    main_road_buffer_fc = data_files["major_road_buffer"]
    main_road_shrunked_fc = data_files["major_road_shrunked"]

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=road_fc,
        expression="vegkategori IN ('E', 'R')",
        output_name=main_road_fc,
        selection_type="NEW_SELECTION",
    )
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=main_road_fc,
        expression="medium='L'",
        output_name=main_road_bridge_fc,
        selection_type="NEW_SELECTION",
    )

    arcpy.analysis.Buffer(
        in_features=main_road_bridge_fc,
        out_feature_class=main_road_buffer_fc,
        buffer_distance_or_field="1 meters",
        line_end_type="FLAT",
    )

    arcpy.analysis.Buffer(
        in_features=main_road_buffer_fc,
        out_feature_class=main_road_shrunked_fc,
        buffer_distance_or_field="-50 centimeters",
    )


@timing_decorator
def surface_road() -> None:
    """
    Creates feature class for roads with medium 'T' (surface road).
    """
    road_fc = data_files["input"]
    road_t_fc = data_files["road_t"]

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=road_fc,
        expression="medium='T'",
        output_name=road_t_fc,
        selection_type="NEW_SELECTION",
    )


@timing_decorator
def surface_ER() -> None:
    """
    Creates feature class for major roads with medium 'T' (surface road).
    """
    main_road_fc = data_files["major_road"]
    main_road_t_fc = data_files["major_road_t"]

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=main_road_fc,
        expression="medium='T'",
        output_name=main_road_t_fc,
        selection_type="NEW_SELECTION",
    )


@timing_decorator
def cross() -> None:
    """
    Selects the crossings between shrunked underpass, shrunked bridge and surface roads
    with major roads (ER) and stores them in respective feature classes.
    """
    shrunked_l_fc = data_files["buffer_l_shrunked"]
    shrunked_u_fc = data_files["buffer_u_shrunked"]
    road_t = data_files["road_t"]
    major_t = data_files["major_road_t"]
    major_bridge = data_files["major_road_shrunked"]
    bridge_x_ER = data_files["bridge_cross_ER"]
    underpass_x_ER = data_files["underpass_cross_ER"]
    surface_u_ER = data_files["surface_under_ER"]

    # Bridges from all categories that cross over ER
    select_intersect_and_copy(
        in_fc=shrunked_l_fc,
        select_fc=major_t,
        out_fc=bridge_x_ER,
        lyr_name="veg_l_poly100_shrunked_lyr",
    )

    # Tunnels under ER
    select_intersect_and_copy(
        in_fc=shrunked_u_fc,
        select_fc=major_t,
        out_fc=underpass_x_ER,
        lyr_name="veg_u_poly100_shrunked_lyr",
    )

    # Roads on surface having ER bridges over them
    select_intersect_and_copy(
        in_fc=road_t,
        select_fc=major_bridge,
        out_fc=surface_u_ER,
        lyr_name="veg_t_lyr",
    )


# Select from CROSS those objects that are most important
@timing_decorator
def keep() -> None:
    """
    Selects and keeps the most important crossings from the previously created crossing feature classes.
    """
    bridge_x_ER = data_files["bridge_cross_ER"]
    underpass_x_ER = data_files["underpass_cross_ER"]
    surface_u_ER = data_files["surface_under_ER"]
    keep_bru = data_files["keep_bru"]
    keep_underpass = data_files["keep_underpass"]
    keep_surface = data_files["keep_surface"]

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=bridge_x_ER,
        expression="vegkategori IN ('E', 'R', 'F', 'K', 'P')",
        output_name=keep_bru,
        selection_type="NEW_SELECTION",
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=underpass_x_ER,
        expression="vegkategori IN ('E', 'R', 'F', 'K', 'P')",
        output_name=keep_underpass,
        selection_type="NEW_SELECTION",
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=surface_u_ER,
        expression="vegkategori IN ('E', 'R', 'F', 'K', 'P')",
        output_name=keep_surface,
        selection_type="NEW_SELECTION",
    )


@timing_decorator
def update_crossing_point_attribute() -> None:
    """
    Creates a new field 'er_kryssningspunkt' in the input road feature class and updates it to 1
    for all roads that intersect with the kept major road crossings.
    """

    print("\nUpdating 'er_kryssningspunkt' for intersecting features...")

    road_fc = data_files["input"]
    new_road_fc = data_files["output"]
    bridge_fc = data_files["keep_bru"]
    underpass_fc = data_files["keep_underpass"]
    merged_keep_fc = data_files["merged_keep"]

    arcpy.management.CopyFeatures(in_features=road_fc, out_feature_class=new_road_fc)
    arcpy.management.AddField(
        in_table=new_road_fc, field_name="er_kryssningspunkt", field_type="SHORT"
    )
    arcpy.management.CalculateField(
        in_table=new_road_fc,
        field="er_kryssningspunkt",
        expression=0,
        expression_type="PYTHON3",
    )

    arcpy.management.Merge(
        inputs=[
            bridge_fc,
            underpass_fc,
        ],
        output=merged_keep_fc,
    )

    arcpy.management.MakeFeatureLayer(
        in_features=new_road_fc, out_layer="elveg_sti_lyr"
    )
    arcpy.management.SelectLayerByLocation(
        in_layer="elveg_sti_lyr",
        overlap_type="HAVE_THEIR_CENTER_IN",
        select_features=merged_keep_fc,
        selection_type="NEW_SELECTION",
    )

    count = 0
    with arcpy.da.UpdateCursor("elveg_sti_lyr", ["er_kryssningspunkt"]) as cursor:
        for row in cursor:
            row[0] = 1
            cursor.updateRow(row)
            count += 1

    print(f"Updated 'er_kryssningspunkt' for {count} features.\n")


@timing_decorator
def delete_intermediate_files() -> None:
    """
    Deletes the intermediate files used during the process.
    """
    keep = ["input", "output"]
    for key in data_files:
        if key not in keep:
            arcpy.management.Delete(data_files[key])


if __name__ == "__main__":
    categories_major_road_crossings()
