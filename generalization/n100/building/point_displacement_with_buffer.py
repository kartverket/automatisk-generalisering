# Importing packages
import arcpy
import os

from input_data import input_n100
from file_manager.n100.file_manager_buildings import Building_N100
from constants.n100_constants import N100_Symbology, N100_SQLResources

from custom_tools.polygon_processor import PolygonProcessor
from env_setup import environment_setup
from custom_tools.timing_decorator import timing_decorator
from custom_tools import custom_arcpy


@timing_decorator
def main():
    """
    Summary:
        Needs summary

    Details:
        1. `setup_arcpy_environment`:
            Sets up the ArcPy environment based on predefined settings defined in `general_setup`.
            This function ensures that the ArcPy environment is properly configured for the specific project by utilizing
            the `general_setup` function from the `environment_setup` module.

        2. `selection`:
            Makes the selection of the relevant input features using a sub selection since the operation is too processing heavy to be done for the global dataset. Small scale test logic untill this logic is made OOP.

        3. `creating_raod_buffer`:
            This function creates a buffered feature with a size corresponding to the road width in its symbology.
            Then it iterates through the road features first creating a smaller buffer and gradually increasing the size.
            For each iteration uses the erase tool to erase the polgon created from building points to gradually move it away from road features to prevent overlapp with road features.

        4. `copy_output_feature`:
            Copies the last output of the `creating_raod_buffer` iteration to be able to integrate it into our `file_manager` system.
    """
    environment_setup.main()
    selection()

    last_output_feature = creating_road_buffer()
    copy_output_feature(last_output_feature)


@timing_decorator
def selection():
    """
    Summary:
        Makes the selection of the relevant input features using a sub selection since the operation is too processing heavy to be done for the global dataset. Small scale test logic untill this logic is made OOP.

    Details:
        - Selects a region from the administrative boundary layer to be used as a selection feature.
        - Then selects the input features that intersects with the selected region.
    """
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n100.AdminFlate,
        expression="navn IN ('Asker', 'Oslo', 'Trondheim', 'Ringerike')",
        output_name=Building_N100.point_resolve_building_conflicts___selection_area_resolve_building_conflicts___n100_building.value,
    )

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.data_preparation___unsplit_roads___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT.value,
        select_features=Building_N100.point_resolve_building_conflicts___selection_area_resolve_building_conflicts___n100_building.value,
        output_name=Building_N100.building_point_buffer_displacement__roads_study_area__n100.value,
    )

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.data_preparation___begrensningskurve_buffer_erase_2___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT.value,
        select_features=Building_N100.point_resolve_building_conflicts___selection_area_resolve_building_conflicts___n100_building.value,
        output_name=Building_N100.building_point_buffer_displacement__begrensningskurve_study_area__n100.value,
    )

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.hospital_church_clusters___final___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT.value,
        select_features=Building_N100.point_resolve_building_conflicts___selection_area_resolve_building_conflicts___n100_building.value,
        output_name=Building_N100.building_point_buffer_displacement__buildings_study_area__n100.value,
    )


@timing_decorator
def pre_create_template_feature_class():
    """
    Summary:
        Creates a small selection of road features to be used as a template feature class.

    Details:
        - Defines a template query "motorvegtype = 'Motorveg'" and buffer width of 42.5 meters to create a template feature class.
        - Selects road features based on the template query and creates a selection output layer.
        - Applies pairwise buffering to the selected road features, creating a buffer output feature class with the specified buffer width.
    """

    # Select a query and buffer width to create a template feature class
    template_query = "motorvegtype = 'Motorveg'"
    template_buffer_width = 42.5

    selection_output_name = f"{Building_N100.building_point_buffer_displacement__selection_roads__n100.value}_template"
    buffer_output_name = f"{Building_N100.building_point_buffer_displacement__roads_buffer__n100.value}_template"

    custom_arcpy.select_attribute_and_make_feature_layer(
        input_layer=Building_N100.data_preparation___unsplit_roads___n100_building.value,
        expression=template_query,
        output_name=selection_output_name,
    )

    arcpy.analysis.PairwiseBuffer(
        in_features=selection_output_name,
        out_feature_class=buffer_output_name,
        buffer_distance_or_field=f"{template_buffer_width} Meters",
    )

    return buffer_output_name


@timing_decorator
def create_or_clear_output_feature_class(template_feature_class, output_fc):
    """
    Summary:
        Makes sure there are not an existing append feature class to prevent unintetional data duplication.
        It checks if the feature class exist, deliting it if it does. Then it creates a new feature class.

    Details:
        - First it checks if the feature clas exists.
        - If it exists it deletes it.
        - Then it creates a new feature class.
    """

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


@timing_decorator
def create_feature_class_with_same_schema(source_fc, template_fc, output_fc):
    """
    Summary:
        The logic to create a new feature class with the same schema as the template feature class, then using cursor to extract the geometry from the source feature class and transfer it to the newly created feature class.

    Details:
        - Defines a new feature class in the specified output workspace using the provided template feature class.
        - Ensures that the spatial reference of the new feature class matches that of the template feature class.
        - Transfers the geometry from the source feature class to the newly created feature class.
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


@timing_decorator
def align_schema_to_template():
    """
    Summary:
        Creates a new feature class with the same schema as the template and transfers only the geometry from the `preparation_begrensningskurve` feature class.

    Details:
        - Retrieves the template feature class using the `pre_create_template_feature_class` function.
        - Prepares the modified feature class for the building point buffer displacement process, obtaining its path from `Building_N100.building_point_buffer_displacement__align_buffer_schema_to_template__n100.value`.
        - Utilizes the `create_feature_class_with_same_schema` function to create a feature class with the same schema as the template, copying only the geometry from the preparation_begrensningskurve feature class.
    """

    template_feature_class = pre_create_template_feature_class()
    preparation_fc_modified = (
        Building_N100.building_point_buffer_displacement__align_buffer_schema_to_template__n100.value
    )

    create_feature_class_with_same_schema(
        Building_N100.building_point_buffer_displacement__begrensningskurve_study_area__n100.value,
        template_feature_class,
        preparation_fc_modified,
    )

    return preparation_fc_modified


@timing_decorator
def creating_road_buffer():
    """
    Summary:
        This function creates a buffered feature with a size corresponding to the road width in its symbology.
        Then it iterates through the road features first creating a smaller buffer and gradually increasing the size.
        For each iteration uses the erase tool to erase the polgon created from building points to gradually move it away from road features to prevent overlapp with road features.

    Details:
        - This function creates a buffered feature with a size corresponding to the road width in its symbology.
        - It begins by defining SQL queries and their corresponding buffer widths based on road attributes.
        - The function then selects road features based on the SQL queries and creates buffers with varying sizes for each selection.
        - The process is performed iteratively with different buffer factors to create multiple sets of buffered features.
        - It uses the `
        - For each buffer, it uses the erase tool to remove overlapping building points, gradually moving them away from road features.
        - The final output contains the buffered features with gradually displaced building points to prevent overlap with road features.

    """

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
        Building_N100.building_point_buffer_displacement__buildings_study_area__n100.value
    )

    for factor in buffer_factors:
        buffer_output_names = []

        # Create buffers for each road selection at the current factor
        counter = 1
        for (
            sql_query,
            original_width,
        ) in N100_SQLResources.road_symbology_size_sql_selection.value.items():
            selection_output_name = f"{feature_selection}_selection_{counter}"
            custom_arcpy.select_attribute_and_make_feature_layer(
                input_layer=Building_N100.building_point_buffer_displacement__roads_study_area__n100.value,
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

        print("Polygon Processor started...")
        polygon_processor = PolygonProcessor(
            input_building_points=current_building_points,
            output_polygon_feature_class=f"{Building_N100.building_point_buffer_displacement__iteration_points_to_square_polygons__n100.value}_{counter}",
            building_symbol_dimensions=N100_Symbology.building_symbol_dimensions.value,
            symbol_field_name="symbol_val",
            index_field_name="OBJECTID",
        )
        polygon_processor.run()

        # Perform Erase and FeatureToPoint operations
        output_feature_to_point = f"{Building_N100.calculate_point_values___points_going_into_rbc___n100_building.value}_{counter}"
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


@timing_decorator
def copy_output_feature(last_output_feature_to_point):
    """
    Summary:
        Copies the last output of the `creating_raod_buffer` iteration to be able to integrate it into our `file_manager` system.

    Details:
        - Uses the returned last output from `creating_raod_buffer` as input to copy the feature using `file_manager` system.
    """
    arcpy.management.Copy(
        in_data=last_output_feature_to_point,
        out_data=Building_N100.building_point_buffer_displacement__displaced_building_points__n100.value,
    )


if __name__ == "__main__":
    main()
