# Imports
from enum import Enum
import config
from env_setup import setup_directory_structure


# Scale name
scale = setup_directory_structure.scale_n100

# Object name
object = setup_directory_structure.object_elv_bekk

# Relative paths
relative_path_gdb = (
    rf"{config.output_folder}\automatic_generalization_outputs\{scale}\{object}.gdb"
)

relative_path_general_files = rf"{config.output_folder}\automatic_generalization_outputs\{scale}\{setup_directory_structure.general_files_name}"

relative_path_lyrx = rf"{config.output_folder}\automatic_generalization_outputs\{scale}\{setup_directory_structure.lyrx_directory_name}"


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


##############################################################################################################################################


class River_N100(Enum):
    pass
