import arcpy
import os

from env_setup import environment_setup
from custom_tools import custom_arcpy
from file_manager.n100.file_manager_buildings import Building_N100


def main():
    setup_arcpy_environment()

    (
        max_object_id,
        partition_polygon,
    ) = pre_iteration()

    (
        append_feature_building_points,
        append_feature_building_polygon,
        partition_field,
        iteration_append_point_feature,
        iteration_append_polygon_feature,
        input_building_points,
        input_building_polygon,
    ) = create_append_feature_class()

    iteration_partition(
        max_object_id,
        partition_polygon,
        append_feature_building_points,
        append_feature_building_polygon,
        iteration_append_point_feature,
        iteration_append_polygon_feature,
        input_building_points,
        input_building_polygon,
        partition_field,
    )


def setup_arcpy_environment():
    """
    Sets up the ArcPy environment based on predefined settings.
    """
    environment_setup.general_setup()


def pre_iteration():
    partition_polygon = (
        Building_N100.create_cartographic_partitions__cartographic_partitions__n100.value
    )

    # Find the maximum OBJECTID in the feature class
    max_object_id = arcpy.da.SearchCursor(
        partition_polygon, "OBJECTID", sql_clause=(None, "ORDER BY OBJECTID DESC")
    ).next()[0]

    return (
        max_object_id,
        partition_polygon,
    )


def create_append_feature_class():
    append_feature_building_points = (
        Building_N100.iteration__append_feature_building_point__n100.value
    )
    append_feature_building_polygon = (
        Building_N100.iteration__append_feature_building_polygon__n100.value
    )

    iteration_append_point_feature = (
        Building_N100.iteration__building_points_iteration_selection_append__n100.value
    )
    iteration_append_polygon_feature = (
        Building_N100.iteration__building_polygon_iteration_selection_append__n100.value
    )

    input_building_points = f"{Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value}_copy"
    arcpy.management.Copy(
        in_data=Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value,
        out_data=input_building_points,
    )
    print(f"copied {input_building_points}")

    partition_field = "partition_select"
    arcpy.AddField_management(
        in_table=input_building_points,
        field_name=partition_field,
        field_type="LONG",
    )
    print(f"added field {partition_field}")

    input_building_polygon = f"{Building_N100.simplify_building_polygons__simplified_grunnriss__n100.value}_copy"
    arcpy.management.Copy(
        in_data=Building_N100.simplify_building_polygons__simplified_grunnriss__n100.value,
        out_data=input_building_polygon,
    )
    print(f"copied {input_building_polygon}")

    arcpy.AddField_management(
        in_table=input_building_polygon,
        field_name=partition_field,
        field_type="LONG",
    )
    print(f"added field {partition_field}")

    # Check and delete the final output feature class if it exists
    if arcpy.Exists(append_feature_building_points):
        arcpy.management.Delete(append_feature_building_points)

    # Check and delete the final output feature class if it exists
    if arcpy.Exists(append_feature_building_polygon):
        arcpy.management.Delete(append_feature_building_polygon)

    if not arcpy.Exists(append_feature_building_points):
        # Create the final output feature class using the schema of the first erased feature
        arcpy.management.CreateFeatureclass(
            out_path=os.path.dirname(append_feature_building_points),
            out_name=os.path.basename(append_feature_building_points),
            template=input_building_points,
        )
        print(f"Created {append_feature_building_points}")

    if not arcpy.Exists(append_feature_building_polygon):
        # Create the final output feature class using the schema of the first erased feature
        arcpy.management.CreateFeatureclass(
            out_path=os.path.dirname(append_feature_building_polygon),
            out_name=os.path.basename(append_feature_building_polygon),
            template=Building_N100.simplify_building_polygons__simplified_grunnriss__n100.value,
        )
        print(f"Created {append_feature_building_polygon}")

    return (
        append_feature_building_points,
        append_feature_building_polygon,
        partition_field,
        iteration_append_point_feature,
        iteration_append_polygon_feature,
        input_building_points,
        input_building_polygon,
    )


def iteration_partition(
    max_object_id,
    partition_polygon,
    append_feature_building_points,
    append_feature_building_polygon,
    iteration_append_point_feature,
    iteration_append_polygon_feature,
    input_building_points,
    input_building_polygon,
    partition_field,
):
    for object_id in range(1, max_object_id + 1):
        iteration_partition = (
            f"{Building_N100.iteration__iteration_partition__n100.value}_{object_id}"
        )
        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=partition_polygon,
            expression=f"OBJECTID = {object_id}",
            output_name=iteration_partition,
        )

        points_exist = False
        polygons_exist = False

        # Check and delete the final output feature class if it exists
        if arcpy.Exists(iteration_append_point_feature):
            arcpy.management.Delete(iteration_append_point_feature)

        if not arcpy.Exists(iteration_append_point_feature):
            # Create the final output feature class using the schema of the first erased feature
            arcpy.management.CreateFeatureclass(
                out_path=os.path.dirname(iteration_append_point_feature),
                out_name=os.path.basename(iteration_append_point_feature),
                template=input_building_points,
            )
            print(f"Created {iteration_append_point_feature}")

        # Check and delete the final output feature class if it exists
        if arcpy.Exists(iteration_append_polygon_feature):
            arcpy.management.Delete(iteration_append_polygon_feature)

        if not arcpy.Exists(iteration_append_polygon_feature):
            # Create the final output feature class using the schema of the first erased feature
            arcpy.management.CreateFeatureclass(
                out_path=os.path.dirname(iteration_append_polygon_feature),
                out_name=os.path.basename(iteration_append_polygon_feature),
                template=input_building_polygon,
            )
            print(f"Created {iteration_append_polygon_feature}")

        building_points_base_partition_selection = f"{Building_N100.iteration__building_points_base_partition_selection__n100.value}_{object_id}"
        building_points_present_partition = f"{Building_N100.iteration__building_points_present_partition__n100.value}_{object_id}"

        custom_arcpy.select_location_and_make_feature_layer(
            input_layer=input_building_points,
            overlap_type=custom_arcpy.OverlapType.HAVE_THEIR_CENTER_IN.value,
            select_features=iteration_partition,
            output_name=building_points_present_partition,
        )

        # Check for building points in this partition
        count_points = int(
            arcpy.management.GetCount(building_points_present_partition).getOutput(0)
        )
        if count_points > 0:
            points_exist = True
            print(f"iteration partition {object_id} has {count_points} building points")

            arcpy.CalculateField_management(
                in_table=building_points_present_partition,
                field=partition_field,
                expression="1",
            )

            arcpy.management.Append(
                inputs=building_points_present_partition,
                target=iteration_append_point_feature,
                schema_type="NO_TEST",
            )

            custom_arcpy.select_location_and_make_feature_layer(
                input_layer=input_building_points,
                overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
                select_features=iteration_partition,
                output_name=building_points_base_partition_selection,
                selection_type=custom_arcpy.SelectionType.NEW_SELECTION.value,
                search_distance="500 Meters",
            )

            arcpy.management.SelectLayerByLocation(
                in_layer=building_points_base_partition_selection,
                overlap_type="HAVE_THEIR_CENTER_IN",
                select_features=iteration_partition,
                selection_type="REMOVE_FROM_SELECTION",
            )

            arcpy.CalculateField_management(
                in_table=building_points_base_partition_selection,
                field=partition_field,
                expression="0",
            )

            arcpy.management.Append(
                inputs=building_points_base_partition_selection,
                target=iteration_append_point_feature,
                schema_type="NO_TEST",
            )

        building_polygon_base_partition_selection = f"{Building_N100.iteration__building_polygon_base_partition_selection__n100.value}_{object_id}"
        building_polygon_present_partition = f"{Building_N100.iteration__building_polygon_present_partition__n100.value}_{object_id}"

        custom_arcpy.select_location_and_make_feature_layer(
            input_layer=input_building_polygon,
            overlap_type=custom_arcpy.OverlapType.HAVE_THEIR_CENTER_IN.value,
            select_features=iteration_partition,
            output_name=building_polygon_present_partition,
        )

        # Check for building polygons in this partition
        count_polygons = int(
            arcpy.management.GetCount(building_polygon_present_partition).getOutput(0)
        )
        if count_polygons > 0:
            polygons_exist = True
            print(
                f"iteration partition {object_id} has {count_polygons} building polygons"
            )

            arcpy.CalculateField_management(
                in_table=building_polygon_present_partition,
                field=partition_field,
                expression="1",
            )

            arcpy.management.Append(
                inputs=building_polygon_present_partition,
                target=iteration_append_polygon_feature,
                schema_type="NO_TEST",
            )

            custom_arcpy.select_location_and_make_feature_layer(
                input_layer=input_building_polygon,
                overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
                select_features=iteration_partition,
                output_name=building_polygon_base_partition_selection,
                selection_type=custom_arcpy.SelectionType.NEW_SELECTION.value,
                search_distance="500 Meters",
            )

            arcpy.management.SelectLayerByLocation(
                in_layer=building_polygon_base_partition_selection,
                overlap_type="HAVE_THEIR_CENTER_IN",
                select_features=partition_polygon,
                selection_type="REMOVE_FROM_SELECTION",
            )

            arcpy.CalculateField_management(
                in_table=building_polygon_base_partition_selection,
                field=partition_field,
                expression="0",
            )

            arcpy.management.Append(
                inputs=building_polygon_base_partition_selection,
                target=iteration_append_polygon_feature,
                schema_type="NO_TEST",
            )

            selected_points_from_partition = f"{iteration_append_point_feature}_temp"

            #######################################
            # HERE I WOULD PUT LOGIC TO PROCESS ON building_points_base_partition_selection and building_polygon_base_partition_selection
            #######################################

            custom_arcpy.select_attribute_and_make_feature_layer(
                input_layer=iteration_append_point_feature,
                expression=f"{partition_field} = 1",
                output_name=selected_points_from_partition,
            )

            arcpy.management.Append(
                inputs=selected_points_from_partition,
                target=append_feature_building_points,
                schema_type="NO_TEST",
            )
            arcpy.management.Delete(selected_points_from_partition)

            print(f"appended selected points to {append_feature_building_points}")

            selected_polygon_from_partition = f"{iteration_append_polygon_feature}_temp"

            custom_arcpy.select_attribute_and_make_feature_layer(
                input_layer=iteration_append_polygon_feature,
                expression=f"{partition_field} = 1",
                output_name=selected_polygon_from_partition,
            )

            arcpy.management.Append(
                inputs=selected_polygon_from_partition,
                target=append_feature_building_polygon,
                schema_type="NO_TEST",
            )
            arcpy.management.Delete(selected_polygon_from_partition)

            print(f"appended selected points to {append_feature_building_polygon}")

        # Clean up iteration features
        try:
            arcpy.management.Delete(iteration_partition)
            arcpy.management.Delete(iteration_append_point_feature)
            arcpy.management.Delete(iteration_append_polygon_feature)
            arcpy.management.Delete(selected_points_from_partition)
            arcpy.management.Delete(selected_polygon_from_partition)
            arcpy.management.Delete(building_points_base_partition_selection)
            arcpy.management.Delete(building_polygon_base_partition_selection)
        except Exception as e:
            if not points_exist and not polygons_exist:
                print(f"An error occurred: {e}")
            if not points_exist:
                print("No building points in selected partition")
            if not polygons_exist:
                print("No building polygons in selected partition")

        print(f"iteration {object_id} done")


if __name__ == "__main__":
    main()


###############################
# LATER LOGIC GOES HERE
###############################


def move_edge_objects(partition_polygon):
    arcpy.management.Copy(
        in_data=Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value,
        out_data=f"{Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value}_copy",
    )

    arcpy.management.SelectLayerByLocation(
        in_layer=f"{Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value}_copy",
        overlap_type=custom_arcpy.OverlapType.BOUNDARY_TOUCHES,
    )

    custom_arcpy.select_location_and_make_feature_layer(
        input_layer=f"{Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value}_copy",
        overlap_type=custom_arcpy.OverlapType.BOUNDARY_TOUCHES,
        select_features=partition_polygon,
        output_name=f"{Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value}_copy",
    )
