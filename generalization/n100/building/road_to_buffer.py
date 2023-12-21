import arcpy
import os

from env_setup import environment_setup
from custom_tools import custom_arcpy
from file_manager.n100.file_manager_buildings import Building_N100


def main():
    setup_arcpy_environment()

    creating_raod_buffer()


def setup_arcpy_environment():
    """
    Sets up the ArcPy environment based on predefined settings.
    """
    environment_setup.general_setup()


def pre_create_template_feature_class():
    # Select a query and buffer width to create a template feature class
    template_query = "MOTORVEGTYPE = 'Motorveg'"
    template_buffer_width = 42.5

    selection_output_name = (
        f"{Building_N100.roads_to_polygon__selection_roads__n100.value}_template"
    )
    buffer_output_name = (
        f"{Building_N100.roads_to_polygon__roads_buffer__n100.value}_template"
    )

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


def create_or_clear_output_feature_class(template_feature_class):
    output_fc = Building_N100.roads_to_polygon__roads_buffer_appended__n100.value

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

    feature_selection = Building_N100.roads_to_polygon__selection_roads__n100.value
    buffer_feature = Building_N100.roads_to_polygon__roads_buffer__n100.value
    counter = 1

    # Pre-create a template feature class
    template_feature_class = pre_create_template_feature_class()

    # Create or clear the output feature class
    create_or_clear_output_feature_class(template_feature_class)

    # Loop through each SQL query and create a buffer
    for sql_query, buffer_width in sql_queries.items():
        buffer_width_str = str(buffer_width).replace(".", "_")
        selection_output_name = f"{feature_selection}_selection_{counter}"
        buffer_output_name = f"{buffer_feature}_{buffer_width_str}m_{counter}"

        custom_arcpy.select_attribute_and_make_feature_layer(
            input_layer=Building_N100.preperation_veg_sti__unsplit_veg_sti__n100.value,
            expression=sql_query,
            output_name=selection_output_name,
        )

        arcpy.analysis.PairwiseBuffer(
            in_features=selection_output_name,
            out_feature_class=buffer_output_name,
            buffer_distance_or_field=f"{buffer_width} Meters",
        )

        arcpy.management.Append(
            inputs=buffer_output_name,
            target=Building_N100.roads_to_polygon__roads_buffer_appended__n100.value,
        )

        counter += 1


if __name__ == "__main__":
    main()
