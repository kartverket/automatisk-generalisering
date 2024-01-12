import arcpy
import os
import gc

import config
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
        append_building_points_2,
        append_building_polygon_2,
        partition_field,
        iteration_point_feature,
        iteration_polygon_feature,
        input_building_points,
        input_building_polygon,
    ) = create_append_feature_class_2()

    iteration_partition_2(
        max_object_id,
        partition_polygon,
        append_building_points_2,
        append_building_polygon_2,
        iteration_point_feature,
        iteration_polygon_feature,
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


def create_append_feature_class_2():
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

    partition_field = "part_sele"
    arcpy.AddField_management(
        in_table=input_building_points,
        field_name=partition_field,
        field_type="LONG",
    )
    print(f"added field {partition_field}")

    input_building_polygon = f"{Building_N100.iteration__building_polygon_base_partition_selection__n100.value}_copy"
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


def iteration_partition_2(
    max_object_id,
    partition_polygon,
    append_building_points_2,
    append_building_polygon_2,
    iteration_point_feature,
    iteration_polygon_feature,
    input_building_points,
    input_building_polygon,
    partition_field,
):
    for object_id in range(1, max_object_id + 1):
        iteration_partition = (
            f"{Building_N100.iteration__iteration_partition__n100.value}_{object_id}"
        )
        custom_arcpy.select_attribute_and_make_feature_layer(
            input_layer=partition_polygon,
            expression=f"OBJECTID = {object_id}",
            output_name=iteration_partition,
        )

        # Check and delete the final output feature class if it exists
        if arcpy.Exists(iteration_point_feature):
            arcpy.management.Delete(iteration_point_feature)

        if not arcpy.Exists(iteration_point_feature):
            # Create the final output feature class using the schema of the first erased feature
            arcpy.management.CreateFeatureclass(
                out_path=os.path.dirname(iteration_point_feature),
                out_name=os.path.basename(iteration_point_feature),
                template=input_building_points,
            )
            print(f"Created {iteration_point_feature}")

        # Check and delete the final output feature class if it exists
        if arcpy.Exists(iteration_polygon_feature):
            arcpy.management.Delete(iteration_polygon_feature)

        if not arcpy.Exists(iteration_polygon_feature):
            # Create the final output feature class using the schema of the first erased feature
            arcpy.management.CreateFeatureclass(
                out_path=os.path.dirname(iteration_polygon_feature),
                out_name=os.path.basename(iteration_polygon_feature),
                template=Building_N100.simplify_building_polygons__simplified_grunnriss__n100.value,
            )
            print(f"Created {iteration_polygon_feature}")

        building_points_base_partition_selection = f"{Building_N100.iteration__building_points_base_partition_selection__n100.value}_{object_id}"
        arcpy.management.MakeFeatureLayer(
            input_building_points,
            building_points_base_partition_selection,
        )

        arcpy.management.SelectLayerByLocation(
            in_layer=building_points_base_partition_selection,
            overlap_type="WITHIN_A_DISTANCE",
            select_features=iteration_partition,
            search_distance="500 Meters",
            selection_type="NEW_SELECTION",
        )

        # Check for building points in this partition
        count_points = int(
            arcpy.management.GetCount(
                building_points_base_partition_selection
            ).getOutput(0)
        )
        if count_points > 0:
            arcpy.management.Copy(
                in_data=building_points_base_partition_selection,
                out_data=f"{iteration_point_feature}_{object_id}_copy",
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

            arcpy.management.CopyFeatures(
                building_points_base_partition_selection,
                f"{building_points_base_partition_selection}_temp",
            )
            print(f"created {building_points_base_partition_selection}_temp")

            arcpy.management.Append(
                inputs=building_points_base_partition_selection,
                target=iteration_point_feature,
                schema_type="NO_TEST",
            )

            arcpy.management.SelectLayerByLocation(
                in_layer=building_points_base_partition_selection,
                overlap_type="HAVE_THEIR_CENTER_IN",
                select_features=iteration_partition,
                selection_type="NEW_SELECTION",
            )

            arcpy.CalculateField_management(
                in_table=building_points_base_partition_selection,
                field=partition_field,
                expression="1",
            )

            arcpy.management.Append(
                inputs=building_points_base_partition_selection,
                target=iteration_point_feature,
                schema_type="NO_TEST",
            )

            print("Next line is sql syntax \n")
            print(f"{partition_field} = 1")

            arcpy.management.CopyFeatures(
                building_points_base_partition_selection,
                f"{building_points_base_partition_selection}_temp",
            )
            print(f"created {building_points_base_partition_selection}_temp")

            arcpy.management.CopyFeatures(
                iteration_point_feature,
                f"{iteration_point_feature}_temp",
            )
            print(f"created {iteration_point_feature}_temp")

            selected_points_from_partition = f"{iteration_point_feature}_temp"
            custom_arcpy.select_attribute_and_make_feature_layer(
                input_layer=iteration_point_feature,
                expression=f"{partition_field} = 1",
                output_name=selected_points_from_partition,
            )

            arcpy.management.Append(
                inputs=selected_points_from_partition,
                target=append_building_points_2,
                schema_type="NO_TEST",
            )
            print(f"appended selected points to {append_building_points_2}")

        building_polygon_base_partition_selection = f"{Building_N100.iteration__building_polygon_base_partition_selection__n100.value}_{object_id}"
        arcpy.management.MakeFeatureLayer(
            input_building_polygon,
            building_polygon_base_partition_selection,
        )

        arcpy.management.SelectLayerByLocation(
            in_layer=building_polygon_base_partition_selection,
            overlap_type="WITHIN_A_DISTANCE",
            select_features=iteration_partition,
            search_distance="500 Meters",
            selection_type="NEW_SELECTION",
        )

        # Check for building polygons in this partition
        count_polygons = int(
            arcpy.management.GetCount(
                building_polygon_base_partition_selection
            ).getOutput(0)
        )
        if count_polygons > 0:
            arcpy.management.Copy(
                in_data=building_polygon_base_partition_selection,
                out_data=f"{iteration_polygon_feature}_{object_id}",
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
                target=iteration_polygon_feature,
                schema_type="NO_TEST",
            )

            arcpy.management.SelectLayerByLocation(
                in_layer=building_polygon_base_partition_selection,
                overlap_type="HAVE_THEIR_CENTER_IN",
                select_features=partition_polygon,
                selection_type="NEW_SELECTION",
            )

            arcpy.CalculateField_management(
                in_table=building_polygon_base_partition_selection,
                field=partition_field,
                expression="1",
            )

            arcpy.management.Append(
                inputs=building_polygon_base_partition_selection,
                target=iteration_polygon_feature,
                schema_type="NO_TEST",
            )

            selected_polygon_from_partition = f"{iteration_polygon_feature}_temp"
            custom_arcpy.select_attribute_and_make_feature_layer(
                input_layer=iteration_polygon_feature,
                expression=f"{partition_field} = 1",
                output_name=selected_polygon_from_partition,
            )

            arcpy.management.Append(
                inputs=selected_polygon_from_partition,
                target=append_building_polygon_2,
                schema_type="NO_TEST",
            )

            print(f"appended selected polygon to {append_building_polygon_2}")

        # Clean up iteration features
        try:
            arcpy.management.Delete(iteration_partition)
            arcpy.management.Delete(iteration_point_feature)
            arcpy.management.Delete(iteration_polygon_feature)
            arcpy.management.Delete(selected_points_from_partition)
            arcpy.management.Delete(selected_polygon_from_partition)
            arcpy.management.Delete(building_points_base_partition_selection)
            arcpy.management.Delete(building_polygon_base_partition_selection)
        except Exception as e:
            print(f"An error occurred: {e}")

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
