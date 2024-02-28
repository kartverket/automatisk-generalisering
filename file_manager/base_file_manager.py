import config
import env_setup.global_config


class BaseFileManager:
    """
    The core file manager class handles the creation of absolute paths across our project,
    imported in different file managers.

    Functions:
        generate_file_name_gdb (str, str) -> str:
            Generates the absolute path for files that can be stored in geodatabases (gdb).
        generate_file_name_general_files (str, str, str) -> str:
            Generates the absolute path for files that cannot be stored in geodatabases,
            specifying its file type.
        generate_file_name_lyrx (str, str) -> str:
            Generates the absolute path for ArcGIS layer files (.lyrx) that cannot be stored
            in geodatabases.

    Attributes:
        local_root_directory (str): The local root directory for the project's output.
        project_root_directory (str): The root directory name of the project.
        general_files_directory_name (str): The directory name for storing general files.
        lyrx_directory_name (str): The directory name for storing ArcGIS layer files (.lyrx).

    Args:
        scale (str): The scale of the geospatial data, used to differentiate directories and
                     file names. Needs to be defined when imported.
        object_name (str): The name of the geospatial object, used to differentiate directories
                           and file names. Needs to be defined when imported.

    This class provides methods to generate standardized absolute paths for geodatabase files,
    general files, and layer files, using the project's naming conventions and directory structure.
    """

    # Define class-level attributes that are constant across instances
    local_root_directory = config.output_folder
    project_root_directory = env_setup.global_config.main_directory_name
    general_files_directory_name = env_setup.global_config.general_files_name
    lyrx_directory_name = env_setup.global_config.lyrx_directory_name

    def __init__(self, scale, object_name):
        """Initializes the BaseFileManager with specific scale and object name."""
        self.scale = scale
        self.object = object_name

        self.relative_path_gdb = rf"{self.local_root_directory}\{self.project_root_directory}\{self.scale}\{self.object}.gdb"
        self.relative_path_general_files = rf"{self.local_root_directory}\{self.project_root_directory}\{self.scale}\{self.general_files_directory_name}"
        self.relative_path_lyrx = rf"{self.local_root_directory}\{self.project_root_directory}\{self.scale}\{self.lyrx_directory_name}"

    def generate_file_name_gdb(
        self,
        script_source_name,
        description,
    ):
        """
        Generates a file path for geodatabase (.gdb) files.

        Args:
            script_source_name (str): The name of the script or source generating the file.
            description (str): A brief description of the file's purpose or contents.

        Returns:
            str: The absolute path for the .gdb file.
        """
        return rf"{self.relative_path_gdb}\{script_source_name}__{description}__{self.scale}_{self.object}"

    def generate_file_name_general_files(
        self,
        script_source_name,
        description,
        file_type,
    ):
        """
        Generates a file path for general files (e.g., CSV, TXT).

        Args:
            script_source_name (str): The name of the script or source generating the file.
            description (str): A brief description of the file's purpose or contents.
            file_type (str): The filetype extension (without dot).

        Returns:
            str: The absolute path for the general file, including the file extension.
        """
        return rf"{self.relative_path_general_files}\{script_source_name}__{description}__{self.scale}_{self.object}.{file_type}"

    def generate_file_name_lyrx(
        self,
        script_source_name,
        description,
    ):
        """
        Generates a file path for ArcGIS layer files (.lyrx).

        Args:
            script_source_name (str): The name of the script or source generating the file.
            description (str): A brief description of the layer file's purpose or contents.

        Returns:
            str: The absolute path for the .lyrx file.
        """
        return rf"{self.relative_path_lyrx}\{script_source_name}__{description}__{self.scale}_{self.object}.lyrx"
