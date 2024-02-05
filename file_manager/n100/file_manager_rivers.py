# Imports
from enum import Enum
import config
import env_setup.global_config
from env_setup import setup_directory_structure


# Scale name
scale = env_setup.global_config.scale_n100

# Object name
object = env_setup.global_config.object_elv_bekk

# Relative paths
relative_path_gdb = (
    rf"{config.output_folder}\automatic_generalization_outputs\{scale}\{object}.gdb"
)

relative_path_general_files = rf"{config.output_folder}\automatic_generalization_outputs\{scale}\{env_setup.global_config.general_files_name}"

relative_path_lyrx = rf"{config.output_folder}\automatic_generalization_outputs\{scale}\{env_setup.global_config.lyrx_directory_name}"


##############################################################################################################################################


# Creating file names based on set standard
def generate_file_name_gdb(
    function_name,
    description,
    scale,
):
    """
    Summary:
        Generates the full file path for files which can be stored in gdb's, where the files are generated to the river.gdb in the n100 subdirectory.

    Details:
        - The path is generated using the relative path to the bygning.gdb in the n100 subdirectory.
        - The file name is generated using the function name, description, and scale.
    """
    return rf"{relative_path_gdb}\{function_name}__{description}__{scale}"


def generate_file_name_general_files(
    function_name,
    description,
    scale,
    file_type,
):
    """
    Summary:
        Generates the full file path for files which can not be stored in gdb's, but are stored in the general_files subdirectory for n100.

    Details:
        - The path is generated using the relative path to the genral_files subdirectory.
        - The file name is generated using the function name, description, and scale.
    """
    return rf"{relative_path_general_files}\{function_name}__{description}__{scale}.{file_type}"


def generate_file_name_lyrx(
    function_name,
    description,
    scale,
):
    """
    Summary:
        Generates the full file path for lyrx files which can not be stored in gdb's. The lyrx files are generated to the lyrx_outputs subdirectory for n100.

    Details:
        - The path is generated using the relative path to the lyrx_outputs subdirectory.
        - The file name is generated using the function name, description, and scale.
    """
    return rf"{relative_path_lyrx}\{function_name}__{description}__{scale}.lyrx"


##############################################################################################################################################

# All file and function names in correct order
unconnected_river_geometry = "unconnected_river_geometry"
river_centerline = "river_centerline"
centerline_pruning = "centerline_pruning"

##############################################################################################################################################


class River_N100(Enum):
    #################################################
    ########### UNCONNECTED RIVER GEOMETRY  ###########
    #################################################

    unconnected_river_geometry__unsplit_river_features__n100 = generate_file_name_gdb(
        function_name=unconnected_river_geometry,
        description="unsplit_river_features",
        scale=scale,
    )

    unconnected_river_geometry__water_area_features__n100 = generate_file_name_gdb(
        function_name=unconnected_river_geometry,
        description="water_area_features",
        scale=scale,
    )

    unconnected_river_geometry__water_area_features_selected__n100 = (
        generate_file_name_gdb(
            function_name=unconnected_river_geometry,
            description="water_area_features_selected",
            scale=scale,
        )
    )

    unconnected_river_geometry__river_dangles__n100 = generate_file_name_gdb(
        function_name=unconnected_river_geometry,
        description="river_dangles",
        scale=scale,
    )

    unconnected_river_selected_river_dangles__n100 = generate_file_name_gdb(
        function_name=unconnected_river_geometry,
        description="selected_river_dangles",
        scale=scale,
    )

    unconnected_river_geometry__river_end_points__n100 = generate_file_name_gdb(
        function_name=unconnected_river_geometry,
        description="river_end_points",
        scale=scale,
    )
    unconnected_river_geometry__river_dangles_buffer__n100 = generate_file_name_gdb(
        function_name=unconnected_river_geometry,
        description="river_dangles_buffer",
        scale=scale,
    )

    unconnected_river_geometry__problematic_river_lines__n100 = generate_file_name_gdb(
        function_name=unconnected_river_geometry,
        description="problematic_river_lines",
        scale=scale,
    )

    unconnected_river_geometry__problematic_river_dangles__n100 = (
        generate_file_name_gdb(
            function_name=unconnected_river_geometry,
            description="problematic_river_dangles",
            scale=scale,
        )
    )

    #################################################
    ########### RIVER CENTERLINE ###########
    #################################################

    river_centerline__rivers_near_waterfeatures__n100 = generate_file_name_gdb(
        function_name=river_centerline,
        description="rivers_near_waterfeatures",
        scale=scale,
    )

    river_centerline__rivers_near_waterfeatures_erased__n100 = generate_file_name_gdb(
        function_name=river_centerline,
        description="rivers_near_waterfeatures_erased",
        scale=scale,
    )

    short__water_feature__n100 = generate_file_name_gdb(
        function_name="short",
        description="water_feature",
        scale=scale,
    )

    short__water_feature_centroid__n100 = generate_file_name_gdb(
        function_name="short",
        description="water_feature_centroid",
        scale=scale,
    )

    river_centerline__water_feature_centerline__n100 = generate_file_name_gdb(
        function_name=river_centerline,
        description="water_feature_centerline",
        scale=scale,
    )

    river_centerline__water_feature_collapsed__n100 = generate_file_name_gdb(
        function_name=river_centerline,
        description="water_feature_collapsed",
        scale=scale,
    )

    river_centerline__study_lake__n100 = generate_file_name_gdb(
        function_name=river_centerline,
        description="study_lake",
        scale=scale,
    )

    river_centerline__study_rivers__n100 = generate_file_name_gdb(
        function_name=river_centerline,
        description="study_rivers",
        scale=scale,
    )

    river_centerline__study_centerline__n100 = generate_file_name_gdb(
        function_name=river_centerline,
        description="study_centerline",
        scale=scale,
    )

    river_centerline__study_lake_collapsed__n100 = generate_file_name_gdb(
        function_name=river_centerline,
        description="study_lake_collapsed",
        scale=scale,
    )
    river_centerline__study_dangles__n100 = generate_file_name_gdb(
        function_name=river_centerline,
        description="study_dangles",
        scale=scale,
    )

    centerline_pruning__pruned_centerline__n100 = generate_file_name_gdb(
        function_name=centerline_pruning,
        description="pruned_centerline",
        scale=scale,
    )
