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
        partition_buffer,
        erased_edge_buffer,
    ) = pre_iteration()

    # (
    #     append_building_points,
    #     append_building_polygon,
    # ) = create_append_feature_class()
    #
    # iterate_partition(
    #     max_object_id,
    #     partition_polygon,
    #     partition_buffer,
    #     erased_edge_buffer,
    #     append_building_points,
    #     append_building_polygon,
    # )

    (
        append_building_points_2,
        append_building_polygon_2,
        input_building_points,
        input_building_polygon,
    ) = create_append_feature_class_2()

    iteration_partition_2(
        max_object_id,
        partition_polygon,
        append_building_points_2,
        append_building_polygon_2,
        input_building_points,
        input_building_polygon,
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

    partition_buffer = (
        Building_N100.create_cartographic_partitions__cartographic_partitions_buffer__n100.value
    )

    erased_edge_buffer = (
        Building_N100.create_cartographic_partitions__buffer_erased__n100.value
    )

    # Find the maximum OBJECTID in the feature class
    max_object_id = arcpy.da.SearchCursor(
        partition_polygon, "OBJECTID", sql_clause=(None, "ORDER BY OBJECTID DESC")
    ).next()[0]

    return max_object_id, partition_polygon, partition_buffer, erased_edge_buffer


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


def create_append_feature_class():
    append_building_points = (
        Building_N100.iteration__append_feature_building_point__n100.value
    )

    append_building_polygon = (
        Building_N100.iteration__append_feature_building_polygon__n100.value
    )
    # Check and delete the final output feature class if it exists
    if arcpy.Exists(append_building_points):
        arcpy.management.Delete(append_building_points)

    # Check and delete the final output feature class if it exists
    if arcpy.Exists(append_building_polygon):
        arcpy.management.Delete(append_building_polygon)

    if not arcpy.Exists(append_building_points):
        # Create the final output feature class using the schema of the first erased feature
        arcpy.management.CreateFeatureclass(
            out_path=os.path.dirname(append_building_points),
            out_name=os.path.basename(append_building_points),
            template=Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value,
        )
        print(f"Created {append_building_points}")

    if not arcpy.Exists(append_building_polygon):
        # Create the final output feature class using the schema of the first erased feature
        arcpy.management.CreateFeatureclass(
            out_path=os.path.dirname(append_building_polygon),
            out_name=os.path.basename(append_building_polygon),
            template=Building_N100.simplify_building_polygons__simplified_grunnriss__n100.value,
        )
        print(f"Created {append_building_polygon}")

    return append_building_points, append_building_polygon


def create_append_feature_class_2():
    append_building_points_2 = (
        f"{Building_N100.iteration__append_feature_building_point__n100.value}_2"
    )

    append_building_polygon_2 = (
        f"{Building_N100.iteration__append_feature_building_polygon__n100.value}_2"
    )

    input_building_points = f"{Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value}_copy"
    arcpy.management.Copy(
        in_data=Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value,
        out_data=input_building_points,
    )
    partition_field = "partition_selection"
    arcpy.AddField_management(
        in_table=input_building_points,
        field_name=partition_field,
        field_type="LONG",
    )

    input_building_polygon = f"{Building_N100.iteration__building_polygon_partition_selection__n100.value}_copy"
    arcpy.management.Copy(
        in_data=Building_N100.simplify_building_polygons__simplified_grunnriss__n100.value,
        out_data=input_building_polygon,
    )
    partition_field = "partition_selection"
    arcpy.AddField_management(
        in_table=input_building_polygon,
        field_name=partition_field,
        field_type="LONG",
    )

    # Check and delete the final output feature class if it exists
    if arcpy.Exists(append_building_points_2):
        arcpy.management.Delete(append_building_points_2)

    # Check and delete the final output feature class if it exists
    if arcpy.Exists(append_building_polygon_2):
        arcpy.management.Delete(append_building_polygon_2)

    if not arcpy.Exists(append_building_points_2):
        # Create the final output feature class using the schema of the first erased feature
        arcpy.management.CreateFeatureclass(
            out_path=os.path.dirname(append_building_points_2),
            out_name=os.path.basename(append_building_points_2),
            template=input_building_points,
        )
        print(f"Created {append_building_points_2}")

    if not arcpy.Exists(append_building_polygon_2):
        # Create the final output feature class using the schema of the first erased feature
        arcpy.management.CreateFeatureclass(
            out_path=os.path.dirname(append_building_polygon_2),
            out_name=os.path.basename(append_building_polygon_2),
            template=Building_N100.simplify_building_polygons__simplified_grunnriss__n100.value,
        )
        print(f"Created {append_building_polygon_2}")

    return (
        append_building_points_2,
        append_building_polygon_2,
        input_building_points,
        input_building_polygon,
    )


def iteration_partition_2(
    max_object_id,
    partition_polygon,
    append_building_points_2,
    append_building_polygon_2,
    input_building_points,
    input_building_polygon,
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
        building_points_partition_selection_2 = f"{Building_N100.iteration__building_points_partition_selection__n100.value}_{object_id}"
        arcpy.management.MakeFeatureLayer(
            input_building_points,
            building_points_partition_selection_2,
        )

        arcpy.management.SelectLayerByLocation(
            in_layer=building_points_partition_selection_2,
            overlap_type="WITHIN_A_DISTANCE",
            select_features=partition_polygon,
            search_distance="500 Meters",
            selection_type="NEW_SELECTION",
        )

        arcpy.management.SelectLayerByLocation(
            in_layer=building_points_partition_selection_2,
            overlap_type="HAVE_THEIR_CENTER_IN",
            select_features=partition_polygon,
            selection_type="REMOVE_FROM_SELECTION",
        )

        arcpy.management.Append(
            inputs=building_points_partition_selection_2,
            target=append_building_points_2,
            schema_type="NO_TEST",
        )

        building_polygon_partition_selection_2 = f"{Building_N100.iteration__building_polygon_partition_selection__n100.value}_{object_id}"
        arcpy.management.MakeFeatureLayer(
            input_building_polygon,
            building_polygon_partition_selection_2,
        )

        arcpy.management.SelectLayerByLocation(
            in_layer=building_polygon_partition_selection_2,
            overlap_type="WITHIN_A_DISTANCE",
            select_features=partition_polygon,
            search_distance="500 Meters",
            selection_type="NEW_SELECTION",
        )

        arcpy.management.SelectLayerByLocation(
            in_layer=building_polygon_partition_selection_2,
            overlap_type="HAVE_THEIR_CENTER_IN",
            select_features=partition_polygon,
            selection_type="REMOVE_FROM_SELECTION",
        )

        arcpy.management.Append(
            inputs=building_polygon_partition_selection_2,
            target=append_building_polygon_2,
            schema_type="NO_TEST",
        )

        # Clean up iteration features
        arcpy.management.Delete(iteration_partition)
        arcpy.management.Delete(building_points_partition_selection_2)
        arcpy.management.Delete(building_polygon_partition_selection_2)

        print(f"iteration {object_id} done")


def iterate_partition(
    max_object_id,
    partition_polygon,
    partition_buffer,
    erased_edge_buffer,
    append_building_points,
    append_building_polygon,
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

        # Select the individual buffer object by OBJECTID
        iteration_buffer = (
            f"{Building_N100.iteration__iteration_buffer__n100.value}_{object_id}"
        )
        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=partition_buffer,
            expression=f"OBJECTID = {object_id}",
            output_name=iteration_buffer,
        )

        # Select the individual erased buffer object by OBJECTID
        iteration_erased_buffer = f"{Building_N100.iteration__iteration_erased_buffer__n100.value}_{object_id}"
        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=erased_edge_buffer,
            expression=f"OBJECTID = {object_id}",
            output_name=iteration_erased_buffer,
        )

        #### SELECT LOCATION AND MAKE PERMANENT ####

        building_points_partition_selection = f"{Building_N100.iteration__building_points_partition_selection__n100.value}_{object_id}"
        custom_arcpy.select_location_and_make_permanent_feature(
            input_layer=Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value,
            overlap_type=custom_arcpy.OverlapType.HAVE_THEIR_CENTER_IN,
            select_features=iteration_partition,
            output_name=building_points_partition_selection,
        )

        building_polygon_partition_selection = f"{Building_N100.iteration__building_polygon_partition_selection__n100.value}_{object_id}"
        custom_arcpy.select_location_and_make_permanent_feature(
            input_layer=Building_N100.simplify_building_polygons__simplified_grunnriss__n100.value,
            overlap_type=custom_arcpy.OverlapType.HAVE_THEIR_CENTER_IN,
            select_features=iteration_partition,
            output_name=building_polygon_partition_selection,
        )

        arcpy.management.Append(
            inputs=building_points_partition_selection,
            target=append_building_points,
            schema_type="NO_TEST",
        )
        arcpy.management.Append(
            inputs=building_polygon_partition_selection,
            target=append_building_polygon,
            schema_type="NO_TEST",
        )

        # Clean up iteration features
        arcpy.management.Delete(iteration_partition)
        arcpy.management.Delete(iteration_buffer)
        arcpy.management.Delete(iteration_erased_buffer)
        arcpy.management.Delete(building_points_partition_selection)
        arcpy.management.Delete(building_polygon_partition_selection)

        # NEED TO FIND A LOGIC TO HANDLE FEATURES EXACTLY AT THE BOARDER OF THE PARTITION

        print(f"iteration {object_id} done")


if __name__ == "__main__":
    main()
