# Importing packages
import arcpy
import os

from custom_tools.general_tools.study_area_selector import StudyAreaSelector

# Importing custom input files modules
from input_data import input_n50
from input_data import input_n100
from input_data import input_other

# Importing custom modules
from file_manager.n100.file_manager_roads import Road_N100
from env_setup import environment_setup
import config
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools import custom_arcpy


def main():
    environment_setup.main()
    selecting_paths_and_nvdb_roads_in_studyarea()
    merge_n50_and_nvdb()
    multipart_to_singlepart()
    merge_divided_roads()
    thin_road_network_1()
    collapse_road_detail()
    thin_road_network_2()
    thin_road_network_3()
    spatial_join_between_functional_roadclass_and_roads()
    calculate_new_hierarchy_based_on_functional_road_class()
    thin_road_network_4()
    remove_rundkjoring_that_survived_collapse_road_detail()


@timing_decorator
def selecting_paths_and_nvdb_roads_in_studyarea():
    selector = StudyAreaSelector(
        input_output_file_dict={
            Road_N100.data_preperation___paths_n50_with_calculated_fields___n100_road.value: Road_N100.first_generalization___paths_in_study_area___n100_road.value,
            Road_N100.data_preperation___selecting_everything_but_rampe_with_calculated_fields_nvdb___n100_road.value: Road_N100.first_generalization____nvdb_roads_in_study_area___n100_road.value,
            config.path_to_functional_road_class: Road_N100.data_preperation___functional_road_class_dataset___n100_road.value,
        },
        selecting_file=input_n100.AdminFlate,
        selecting_sql_expression="navn IN ('Oslo')",
        select_local=config.select_study_area,
    )

    selector.run()


@timing_decorator
def merge_n50_and_nvdb():
    # Merging paths and nvdb roads
    arcpy.management.Merge(
        inputs=[
            Road_N100.first_generalization___paths_in_study_area___n100_road.value,
            Road_N100.first_generalization____nvdb_roads_in_study_area___n100_road.value,
        ],
        output=Road_N100.first_generalization____merged_roads_and_paths___n100_road.value,
    )


@timing_decorator
def multipart_to_singlepart():
    arcpy.management.MultipartToSinglepart(
        in_features=Road_N100.first_generalization____merged_roads_and_paths___n100_road.value,
        out_feature_class=Road_N100.first_generalization____multipart_to_singlepart___n100_road.value,
    )


@timing_decorator
def merge_divided_roads():
    # Execute Merge Divided Roads
    arcpy.cartography.MergeDividedRoads(
        in_features=Road_N100.first_generalization____multipart_to_singlepart___n100_road.value,
        merge_field="VEGNUMMER",
        merge_distance="50 Meters",
        out_features=Road_N100.first_generalization____merge_divided_roads_features___n100_road.value,
        out_displacement_features=Road_N100.first_generalization____merge_divided_roads_displacement_feature___n100_road.value,
        character_field="characters",
    )


@timing_decorator
def thin_road_network_1():
    arcpy.cartography.ThinRoadNetwork(
        in_features=Road_N100.first_generalization____merge_divided_roads_features___n100_road.value,
        minimum_length="500 Meters",
        invisibility_field="invisibility_1",
        hierarchy_field="hierarchy",
    )
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.first_generalization____merge_divided_roads_features___n100_road.value,
        expression="invisibility_1 = 0",
        output_name=Road_N100.first_generalization____visible_features_after_thin_road_network_1___n100_road.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )


@timing_decorator
def collapse_road_detail():
    arcpy.cartography.CollapseRoadDetail(
        in_features=Road_N100.first_generalization____visible_features_after_thin_road_network_1___n100_road.value,
        collapse_distance="90 Meters",
        output_feature_class=Road_N100.first_generalization____collapse_road_detail___n100_road.value,
    )


@timing_decorator
def thin_road_network_2():
    arcpy.cartography.ThinRoadNetwork(
        in_features=Road_N100.first_generalization____collapse_road_detail___n100_road.value,
        minimum_length="1000 Meters",
        invisibility_field="invisibility_2",
        hierarchy_field="hierarchy",
    )
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.first_generalization____collapse_road_detail___n100_road.value,
        expression="invisibility_2 = 0",
        output_name=Road_N100.first_generalization____visible_features_after_thin_road_network_2___n100_road.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )


@timing_decorator
def thin_road_network_3():
    arcpy.cartography.ThinRoadNetwork(
        in_features=Road_N100.first_generalization____visible_features_after_thin_road_network_2___n100_road.value,
        minimum_length="2000 Meters",
        invisibility_field="invisibility_3",
        hierarchy_field="hierarchy",
    )
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.first_generalization____visible_features_after_thin_road_network_2___n100_road.value,
        expression="invisibility_3 = 0",
        output_name=Road_N100.first_generalization____visible_features_after_thin_road_network_3___n100_road.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )

    arcpy.management.CopyFeatures(
        in_features=Road_N100.first_generalization____visible_features_after_thin_road_network_3___n100_road.value,
        out_feature_class=Road_N100.data_preperation___going_into_spatial_join___n100_road.value,
    )


@timing_decorator
def spatial_join_between_functional_roadclass_and_roads():
    # Create FieldMappings and FieldMap objects
    field_mappings = arcpy.FieldMappings()

    # Add all fields from the target features
    field_mappings.addTable(
        Road_N100.data_preperation___going_into_spatial_join___n100_road.value
    )

    # Create a FieldMap object for the VEGKLASSE field from join features
    vegklasse_field_map = arcpy.FieldMap()
    vegklasse_field_map.addInputField(
        Road_N100.data_preperation___functional_road_class_dataset___n100_road.value,
        "VEGKLASSE",
    )

    # Rename the field in case of conflicts or to ensure proper naming in output
    output_field = vegklasse_field_map.outputField
    output_field.name = "VEGKLASSE"
    vegklasse_field_map.outputField = output_field

    # Add the VEGKLASSE FieldMap to the FieldMappings
    field_mappings.addFieldMap(vegklasse_field_map)

    # Perform the Spatial Join with the custom FieldMappings

    arcpy.analysis.SpatialJoin(
        target_features=Road_N100.data_preperation___going_into_spatial_join___n100_road.value,
        join_features=Road_N100.data_preperation___functional_road_class_dataset___n100_road.value,
        out_feature_class=Road_N100.data_preperation___spatial_join_completed___n100_road.value,
        join_operation="JOIN_ONE_TO_MANY",
        join_type="KEEP_ALL",
        field_mapping=field_mappings,
        match_option="SHARE_A_LINE_SEGMENT_WITH",
    )


"""
        if vegklasse in ['0', '1']:
            return 0
        elif vegklasse in ['2', '3']:
            return 1
        elif vegklasse in ['4', '5']:
            return 2
        elif vegklasse == '6':
            return 3
        elif vegklasse == '7':
            return 4
        elif vegklasse in ['8', '9']:
            return 5
        elif vegklasse is None: 
            return 6"""


@timing_decorator
def calculate_new_hierarchy_based_on_functional_road_class():
    assign_hierarchy_based_on_functional_road_class = """
def Reclass(vegklasse):
    if vegklasse == '0':
        return 0
    elif vegklasse == '1':
        return 1
    elif vegklasse == '2':
        return 2
    elif vegklasse == '3':
        return 3
    elif vegklasse == '4':
        return 4
    elif vegklasse == '5':
        return 5
    elif vegklasse == '6':
        return 6
    elif vegklasse == '7':
        return 7
    elif vegklasse == '8':
        return 8
    elif vegklasse == '9':
        return 9
    elif vegklasse is None: 
        return 10
    """

    arcpy.management.AddField(
        in_table=Road_N100.data_preperation___spatial_join_completed___n100_road.value,
        field_name="functional_hierarchy",
        field_type="SHORT",
    )

    arcpy.management.CalculateField(
        in_table=Road_N100.data_preperation___spatial_join_completed___n100_road.value,
        field="functional_hierarchy",
        expression="Reclass(!VEGKLASSE!)",
        expression_type="PYTHON3",
        code_block=assign_hierarchy_based_on_functional_road_class,
    )


@timing_decorator
def thin_road_network_4():
    arcpy.cartography.ThinRoadNetwork(
        in_features=Road_N100.data_preperation___spatial_join_completed___n100_road.value,
        minimum_length="2000 Meters",
        invisibility_field="invisibility_4",
        hierarchy_field="functional_hierarchy",
    )
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.data_preperation___spatial_join_completed___n100_road.value,
        expression="invisibility_4 = 0",
        output_name=Road_N100.first_generalization____visible_features_after_thin_road_network_4___n100_road.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )


@timing_decorator
def remove_rundkjoring_that_survived_collapse_road_detail():
    print("Starting the removal process for rundkjoring that survived collapse...")

    # Select only rundkjoring parts
    print("Selecting rundkjoring parts...")
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.first_generalization____visible_features_after_thin_road_network_4___n100_road.value,
        expression="TYPEVEG = 'rundkjøring'",
        output_name=Road_N100.first_generalization____selecting_rundkjoring___n100_road.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )
    print("Rundkjoring parts selected.")

    # Dissolving rundkjoring features
    print("Dissolving rundkjoring features...")
    arcpy.management.Dissolve(
        in_features=Road_N100.first_generalization____selecting_rundkjoring___n100_road.value,
        out_feature_class=Road_N100.first_generalization____dissolving_rundkjoring___n100_road.value,
        dissolve_field="TYPEVEG",
    )
    print("Rundkjoring features dissolved.")

    # Selecting all road parts except for rundkjoring
    print("Selecting all road parts except for rundkjoring...")
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.data_preperation___spatial_join_completed___n100_road.value,
        expression="TYPEVEG = 'rundkjøring'",
        output_name=Road_N100.first_generalization____selecting_all_road_parts_except_rundkjoring___n100_road.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
        inverted=True,
    )
    print("All road parts except rundkjoring selected.")

    # Copying the road class so no changes are made to the original
    print("Copying the road feature class...")
    arcpy.management.CopyFeatures(
        in_features=Road_N100.first_generalization____selecting_all_road_parts_except_rundkjoring___n100_road.value,
        out_feature_class=Road_N100.first_generalization____roads_going_into_extend_line___n100_road.value,
    )
    print("Road feature class copied.")


"""

    arcpy.analysis.PairwiseBuffer(
        in_features=Road_N100.first_generalization____dissolving_rundkjoring___n100_road.value,
        out_feature_class=Road_N100.first_generalization____rundkjoring_buffer___n100_road.value,
        buffer_distance_or_field="25 Meter",
        dissolve_option="ALL",
    )

    arcpy.management.MultipartToSinglepart(
        in_features=Road_N100.first_generalization____rundkjoring_buffer___n100_road.value,
        out_feature_class=Road_N100.first_generalization____rundkjoring_buffer_multipart_to_singlepart___n100_road.value,
    )

    # Using the newly created polygons to create a point in the centroid
    print("Converting polygons to points at centroid...")
    arcpy.management.FeatureToPoint(
        in_features=Road_N100.first_generalization____rundkjoring_buffer_multipart_to_singlepart___n100_road.value,
        out_feature_class=Road_N100.first_generalization____feature_to_point___n100_road.value,
        point_location="INSIDE",
    )

    # Copy the snapped road features
    print("Copying snapped road features...")
    arcpy.management.CopyFeatures(
        in_features=Road_N100.first_generalization____roads_going_into_extend_line___n100_road.value,
        out_feature_class=Road_N100.first_generalization____roads_after_snap___n100_road.value,
    )
    print("Snapped road features copied.")

    print("Process completed.")

    arcpy.edit.ExtendLine(
        in_features=Road_N100.first_generalization____roads_going_into_extend_line___n100_road.value,
        length="30 Meters",
        extend_to=Road_N100.first_generalization____feature_to_point___n100_road.value,
    )
    # Create a new polygon feature class
    print("Creating a new polygon feature class...")
    out_path, out_name = os.path.split(
        Road_N100.first_generalization____polygon_created_from_line___n100_road.value
    )
    arcpy.CreateFeatureclass_management(
        out_path=out_path,
        out_name=out_name,
        geometry_type="POLYGON",
        spatial_reference=Road_N100.first_generalization____dissolving_rundkjoring___n100_road.value,
    )
    print(f"New polygon feature class created: {os.path.join(out_path, out_name)}")

    # Creating polygons from rundkjoring lines
    print("Creating polygons from rundkjoring lines...")
    with arcpy.da.InsertCursor(
        Road_N100.first_generalization____polygon_created_from_line___n100_road.value,
        ["SHAPE@"],
    ) as cursor:
        with arcpy.da.SearchCursor(
            Road_N100.first_generalization____dissolving_rundkjoring___n100_road.value,
            ["SHAPE@"],
        ) as search_cursor:
            for row in search_cursor:
                line_geometry = row[0]
                # Create a polygon from the line
                polygon = arcpy.Polygon(line_geometry.getPart(0))
                cursor.insertRow([polygon])
    print("Polygons created from rundkjoring lines.")

    print("Polygons converted to points.")

"""


if __name__ == "__main__":
    main()
