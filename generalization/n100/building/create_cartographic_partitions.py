import arcpy
import os

from env_setup import environment_setup
from custom_tools import custom_arcpy
from file_manager.n100.file_manager_buildings import Building_N100


def main():
    setup_arcpy_environment()
    create_cartographic_partitions()
    create_erased_features()


def setup_arcpy_environment():
    """
    Sets up the ArcPy environment based on predefined settings.
    """
    environment_setup.general_setup()


def create_cartographic_partitions():
    arcpy.cartography.CreateCartographicPartitions(
        in_features=[
            Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value,
            Building_N100.simplify_building_polygons__simplified_grunnriss__n100.value,
            Building_N100.preperation_veg_sti__unsplit_veg_sti__n100.value,
            Building_N100.preparation_begrensningskurve__begrensningskurve_buffer_erase_2__n100.value,
        ],
        out_features=Building_N100.create_cartographic_partitions__cartographic_partitions__n100.value,
        feature_count="15000",
        partition_method="FEATURES",
    )

    print(
        f"Created {Building_N100.create_cartographic_partitions__cartographic_partitions__n100.value}"
    )

    arcpy.analysis.PairwiseBuffer(
        in_features=Building_N100.create_cartographic_partitions__cartographic_partitions__n100.value,
        out_feature_class=Building_N100.create_cartographic_partitions__cartographic_partitions_buffer__n100.value,
        buffer_distance_or_field="500 Meters",
    )


def create_erased_features():
    # Fetch the buffer and partition feature classes
    buffer_fc = (
        Building_N100.create_cartographic_partitions__cartographic_partitions_buffer__n100.value
    )
    partition_fc = (
        Building_N100.create_cartographic_partitions__cartographic_partitions__n100.value
    )
    final_output_fc = (
        Building_N100.create_cartographic_partitions__buffer_erased__n100.value
    )

    # Check and delete the final output feature class if it exists
    if arcpy.Exists(final_output_fc):
        arcpy.management.Delete(final_output_fc)

    # Iterate over each object in the buffer feature class
    with arcpy.da.SearchCursor(buffer_fc, ["OBJECTID"]) as buffer_cursor:
        for buffer_row in buffer_cursor:
            buffer_object_id = buffer_row[0]

            # Select the individual buffer object by OBJECTID
            iteration_buffer = f"in_memory\\buffer_{buffer_object_id}"
            custom_arcpy.select_attribute_and_make_feature_layer(
                input_layer=buffer_fc,
                expression=f"OBJECTID = {buffer_object_id}",
                output_name=iteration_buffer,
            )

            iteration_partition = f"in_memory\\partition_{buffer_object_id}"
            custom_arcpy.select_attribute_and_make_feature_layer(
                input_layer=partition_fc,
                expression=f"OBJECTID = {buffer_object_id}",
                output_name=iteration_partition,
            )

            # Define the output feature class name for the erased feature
            erased_feature_class = f"in_memory\\erased_feature_{buffer_object_id}"

            # Perform the erase operation using the temporary buffer feature class
            arcpy.analysis.PairwiseErase(
                in_features=iteration_buffer,
                erase_features=iteration_partition,
                out_feature_class=erased_feature_class,
            )

            # Append the erased feature to the final output feature class
            if not arcpy.Exists(final_output_fc):
                # Create the final output feature class using the schema of the first erased feature
                arcpy.management.CreateFeatureclass(
                    out_path=os.path.dirname(final_output_fc),
                    out_name=os.path.basename(final_output_fc),
                    template=erased_feature_class,
                )

            arcpy.management.Append(
                inputs=erased_feature_class,
                target=final_output_fc,
                schema_type="NO_TEST",
            )

            # Clean up in_memory feature classes
            arcpy.management.Delete(iteration_buffer)
            arcpy.management.Delete(iteration_partition)
            arcpy.management.Delete(erased_feature_class)


if __name__ == "__main__":
    main()
