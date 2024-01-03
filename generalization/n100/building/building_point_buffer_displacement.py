import arcpy
import os
import time

from env_setup import environment_setup
from input_data import input_n100
from custom_tools import custom_arcpy
from file_manager.n100.file_manager_buildings import Building_N100
from custom_tools.polygon_processor import PolygonProcessor


def main():
    setup_arcpy_environment()

    last_output_feature = creating_raod_buffer()
    copy_output_feature(last_output_feature)


def setup_arcpy_environment():
    """
    Sets up the ArcPy environment based on predefined settings.
    """
    environment_setup.general_setup()


def selection():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n100.AdminFlate,
        expression="NAVN = 'Asker'",
        output_name=Building_N100.rbc_selection__selection_area_resolve_building_conflicts__n100.value,
    )

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.preperation_veg_sti__unsplit_veg_sti__n100.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT.value,
        select_features=Building_N100.rbc_selection__selection_area_resolve_building_conflicts__n100.value,
        output_name=Building_N100.building_point_buffer_displacement__roads_study_area__n100.value,
    )

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.preparation_begrensningskurve__begrensningskurve_buffer_erase_2__n100.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT.value,
        select_features=Building_N100.rbc_selection__selection_area_resolve_building_conflicts__n100.value,
        output_name=Building_N100.building_point_buffer_displacement__begrensningskurve_study_area__n100.value,
    )

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT.value,
        select_features=Building_N100.rbc_selection__selection_area_resolve_building_conflicts__n100.value,
        output_name=Building_N100.building_point_buffer_displacement__buildings_study_area__n100.value,
    )


def pre_create_template_feature_class():
    # Select a query and buffer width to create a template feature class
    template_query = "MOTORVEGTYPE = 'Motorveg'"
    template_buffer_width = 42.5

    selection_output_name = f"{Building_N100.building_point_buffer_displacement__selection_roads__n100.value}_template"
    buffer_output_name = f"{Building_N100.building_point_buffer_displacement__roads_buffer__n100.value}_template"

    custom_arcpy.select_attribute_and_make_feature_layer(
        input_layer=Building_N100.preperation_veg_sti__unsplit_veg_sti__n100.value,
        expression=template_query,
        output_name=selection_output_name,
    )

    arcpy.analysis.PairwiseBuffer(
        in_features=selection_output_name,
        out_feature_class=buffer_output_name,
        buffer_distance_or_field=f"{template_buffer_width} Meters",
    )

    return buffer_output_name


def create_or_clear_output_feature_class(template_feature_class, output_fc):
    # Delete the existing output feature class if it exists
    if arcpy.Exists(output_fc):
        arcpy.management.Delete(output_fc)

    # Create a new feature class
    output_workspace, output_class_name = os.path.split(output_fc)
    arcpy.CreateFeatureclass_management(
        out_path=output_workspace,
        out_name=output_class_name,
        template=template_feature_class,
        spatial_reference=environment_setup.project_spatial_reference,
    )


def create_feature_class_with_same_schema(source_fc, template_fc, output_fc):
    """
    Creates a new feature class with the same schema as the template and
    transfers only the geometry from the source feature class.
    """
    # Create a new feature class using the template
    output_workspace, output_class_name = os.path.split(output_fc)
    arcpy.CreateFeatureclass_management(
        output_workspace,
        output_class_name,
        "POLYGON",  # Assuming the geometry type is polygon
        template_fc,
        spatial_reference=arcpy.Describe(template_fc).spatialReference,
    )

    # Transfer geometry from source to the new feature class
    with arcpy.da.SearchCursor(
        source_fc, ["SHAPE@"]
    ) as s_cursor, arcpy.da.InsertCursor(output_fc, ["SHAPE@"]) as i_cursor:
        for row in s_cursor:
            i_cursor.insertRow(row)


def align_schema_to_template():
    """
    Creates a new feature class with the same schema as the template and
    transfers only the geometry from the preparation_begrensningskurve feature class.
    """
    template_feature_class = pre_create_template_feature_class()
    preparation_fc_modified = (
        Building_N100.building_point_buffer_displacement__align_buffer_schema_to_template__n100.value
    )

    create_feature_class_with_same_schema(
        Building_N100.preparation_begrensningskurve__begrensningskurve_buffer_erase_2__n100.value,
        template_feature_class,
        preparation_fc_modified,
    )

    return preparation_fc_modified


def creating_raod_buffer():
    # Define the SQL queries and their corresponding buffer widths
    sql_queries = {
        "MOTORVEGTYPE = 'Motorveg'": 42.5,
        """ 
        SUBTYPEKODE = 3 
        Or MOTORVEGTYPE = 'Motortrafikkveg' 
        Or (SUBTYPEKODE = 2 And MOTORVEGTYPE = 'Motortrafikkveg') 
        Or (SUBTYPEKODE = 2 And MOTORVEGTYPE = 'Ikke motorveg') 
        Or (SUBTYPEKODE = 4 And MOTORVEGTYPE = 'Ikke motorveg') 
        """: 22.5,
        """
        SUBTYPEKODE = 1
        Or SUBTYPEKODE = 5
        Or SUBTYPEKODE = 6
        Or SUBTYPEKODE = 9
        """: 20,
        """
        SUBTYPEKODE = 7
        Or SUBTYPEKODE = 8
        Or SUBTYPEKODE = 10
        Or SUBTYPEKODE =11
        """: 7.5,
    }

    feature_selection = (
        Building_N100.building_point_buffer_displacement__selection_roads__n100.value
    )
    buffer_feature_base = (
        Building_N100.building_point_buffer_displacement__roads_buffer_appended__n100.value
    )

    # Define buffer factors and corresponding output feature classes
    buffer_factors = [0.25, 0.5, 0.75, 0.999, 1]
    output_feature_classes = {}

    # Pre-create a template feature class
    template_feature_class = pre_create_template_feature_class()
    preparation_fc_modified = align_schema_to_template()

    # Create or clear output feature classes for each buffer factor
    output_feature_classes = {}
    for factor in buffer_factors:
        factor_str = str(factor).replace(".", "_")
        output_fc = f"{buffer_feature_base}_factor_{factor_str}"
        output_feature_classes[factor] = output_fc
        create_or_clear_output_feature_class(template_feature_class, output_fc)

    # Initial input for the PolygonProcessor
    current_building_points = (
        Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value
    )

    for factor in buffer_factors:
        buffer_output_names = []

        # Create buffers for each road selection at the current factor
        counter = 1
        for sql_query, original_width in sql_queries.items():
            selection_output_name = f"{feature_selection}_selection_{counter}"
            custom_arcpy.select_attribute_and_make_feature_layer(
                input_layer=Building_N100.preperation_veg_sti__unsplit_veg_sti__n100.value,
                expression=sql_query,
                output_name=selection_output_name,
            )

            buffer_width = original_width * factor + (15 if factor == 1 else 0)
            buffer_width_str = str(buffer_width).replace(".", "_")
            buffer_output_name = f"{buffer_feature_base}_{buffer_width_str}m_{counter}"
            buffer_output_names.append(buffer_output_name)

            arcpy.analysis.PairwiseBuffer(
                in_features=selection_output_name,
                out_feature_class=buffer_output_name,
                buffer_distance_or_field=f"{buffer_width} Meters",
            )
            print(f"Buffered {buffer_output_name} created.")
            counter += 1

        # Merge all buffers for the current factor into a single feature class
        output_fc = output_feature_classes[factor]
        arcpy.management.Merge(
            inputs=buffer_output_names + [preparation_fc_modified],
            output=output_fc,
        )
        print(f"Merged buffers into {output_fc}.")

        building_symbol_dimensions = {
            1: (145, 145),
            2: (145, 145),
            3: (195, 145),
            4: (40, 40),
            5: (80, 80),
            6: (30, 30),
            7: (45, 45),
            8: (45, 45),
            9: (53, 45),
        }

        print("Polygon Processor started...")
        polygon_processor = PolygonProcessor(
            input_building_points=current_building_points,
            output_polygon_feature_class=f"{Building_N100.building_point_buffer_displacement__iteration_points_to_square_polygons__n100.value}_{counter}",
            building_symbol_dimensions=building_symbol_dimensions,
            symbol_field_name="symbol_val",
            index_field_name="OBJECTID",
        )
        polygon_processor.run()

        # Perform Erase and FeatureToPoint operations
        output_feature_to_point = f"{Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value}_{counter}"
        arcpy.analysis.PairwiseErase(
            in_features=f"{Building_N100.building_point_buffer_displacement__iteration_points_to_square_polygons__n100.value}_{counter}",
            erase_features=output_fc,
            out_feature_class=f"{Building_N100.building_point_buffer_displacement__building_polygon_erased__n100.value}_{counter}",
        )

        arcpy.management.FeatureToPoint(
            in_features=f"{Building_N100.building_point_buffer_displacement__building_polygon_erased__n100.value}_{counter}",
            out_feature_class=output_feature_to_point,
            point_location="INSIDE",
        )

        # Update current_building_points for the next iteration
        current_building_points = output_feature_to_point

        last_output_feature_to_point = output_feature_to_point

        counter += 1

    return last_output_feature_to_point


def copy_output_feature(last_output_feature_to_point):
    arcpy.management.Copy(
        in_data=last_output_feature_to_point,
        out_data=Building_N100.building_point_buffer_displacement__displaced_building_points__n100.value,
    )


if __name__ == "__main__":
    main()
