import arcpy
import os
from datetime import datetime

import config
from env_setup.global_config import (
    final_outputs,
    scale_n10,
    scale_n50,
    scale_n100,
    scale_n250,
    scale_n500,
    object_admin,
    object_arealdekke_flate,
    object_bygning,
    object_elv_bekk,
    object_veg_sti,
    object_bygg_og_anlegg,
    object_bane,
    main_directory_name,
    lyrx_directory_name,
    general_files_name,
)

project_spatial_reference = 25833


def main():
    """
    Initializes and executes the setup for ArcGIS Pro environment and project directory structure.

    Summary:
        This function performs the essential initialization tasks for setting up the ArcGIS Pro
        environment and creating a predefined directory structure for the project.

    Details:
        - Initializes the ArcGIS environment setup by configuring workspace, output coordinate system (EPSG:25833),
          xy tolerance (0.02 meters), and xy resolution (0.01 meters), parallel processing factor and set the overwrite output flag to True.
        - Sets up the project directory structure, including creating geodatabases and layer files directories.
    """
    StartTimePrinter.print_start_time()
    arc_gis_environment_setup = ArcGisEnvironmentSetup()
    arc_gis_environment_setup.setup()

    directory_setup_instance = ProjectDirectorySetup()
    directory_setup_instance.setup()


class StartTimePrinter:
    """
    Prints the start time/date when it is called for the first time.

    Summary:
        This class is responsible for printing the current date and time the first time it is called.

    Details:
        - Uses a class variable to ensure the message is printed only once.
        - Prints the current date and time in a readable format.
    """

    _has_printed = False

    @classmethod
    def print_start_time(cls):
        if not cls._has_printed:
            start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\nScript start time: {start_time}")
            cls._has_printed = True


class ArcGisEnvironmentSetup:
    """
    Configures and initializes the ArcGIS Pro environment settings.

    Summary:
        Sets up the ArcGIS Pro environment with specified workspace and spatial reference.
        Ensures setup is performed only once globally.

    Details:
        - Checks if setup has already been done globally to avoid duplication.
        - Sets `arcpy.env.overwriteOutput` to True, ensuring existing files can be overwritten.
        - Configures `arcpy.env.workspace` with the specified workspace path.
        - Sets the output coordinate system to the specified spatial reference (EPSG code).
        - Establishes `arcpy.env.XYTolerance` and `arcpy.env.XYResolution` for geometric precision.
        - Adjusts `arcpy.env.parallelProcessingFactor` according to CPU percentage configured, optimizing performance.

    Attributes:
        workspace (str): The directory path for the ArcGIS workspace.
        spatial_reference (int): The EPSG code for the spatial reference, defaulting to 25833 (ETRS89 / UTM zone 33N).
    """

    _setup_done_globally = False

    def __init__(
        self,
        workspace=config.default_project_workspace,
        spatial_reference=25833,
    ):
        self.workspace = workspace
        self.spatial_reference = spatial_reference

    def setup(self):
        if ArcGisEnvironmentSetup._setup_done_globally:
            return

        arcpy.env.overwriteOutput = True
        arcpy.env.workspace = self.workspace
        arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(
            self.spatial_reference
        )
        arcpy.env.XYTolerance = "0.02 Meters"
        arcpy.env.XYResolution = "0.01 Meters"
        arcpy.env.parallelProcessingFactor = config.cpu_percentage

        ArcGisEnvironmentSetup._setup_done_globally = True

        print("\nArcGIS Pro environment setup completed with the following settings:")
        print("- Overwrite Output: True")
        print(f"- Workspace: {arcpy.env.workspace}")
        print(f"- Output Coordinate System: EPSG:{self.spatial_reference}")
        print(f"- XY Tolerance: {arcpy.env.XYTolerance}")
        print(f"- XY Resolution: {arcpy.env.XYResolution}")
        print(f"- Parallel Processing Factor: {arcpy.env.parallelProcessingFactor}\n")


class ProjectDirectorySetup:
    """
    Creates and configures the project directory structure and geodatabases.

    Summary:
        Establishes a predefined directory structure for project files and geodatabases, ensuring it's done only once globally.

    Details:
        - Checks if the global setup has already been completed to prevent redundancy.
        - Creates a main directory and specified subdirectories for organizing project files.
        - Generates geodatabases in the designated subdirectories for data storage.
        - Sets up additional subdirectories within the subdirectories for miscellaneous files and layer configurations.
        - A common method `create_subdir_structure` is introduced to handle the creation of additional subdirectories within the subdirectories.

    Attributes:
        base_directory (str): The root directory for the project structure.
        sub_directories (list): A list of names for subdirectories to be created within the project structure.
        gdb_names (list): Names of the geodatabases to be created in each subdirectory.
    """

    _setup_done_globally = False

    def __init__(self, base_directory=config.output_folder):
        self.base_directory = base_directory
        self.sub_directories = [
            scale_n10,
            scale_n50,
            scale_n100,
            scale_n250,
            scale_n500,
        ]
        self.gdb_names = [
            final_outputs,
            object_admin,
            object_arealdekke_flate,
            object_bygning,
            object_elv_bekk,
            object_veg_sti,
            object_bygg_og_anlegg,
            object_bane,
        ]

    def setup(self):
        if ProjectDirectorySetup._setup_done_globally:
            return

        main_directory_path = os.path.join(self.base_directory, main_directory_name)
        self.create_directory_structure(main_directory_path)
        self.create_gdbs_in_subdirectories(main_directory_path)
        self.create_subdirectory_structure(
            main_directory_path, subdir_structure=lyrx_directory_name
        )
        self.create_subdirectory_structure(
            main_directory_path, subdir_structure=general_files_name
        )

        print("Directory structure completed.\n")
        ProjectDirectorySetup._setup_done_globally = True

    def create_directory_structure(
        self,
        main_directory_path,
    ):
        os.makedirs(main_directory_path, exist_ok=True)
        for sub_directory in self.sub_directories:
            path = os.path.join(
                main_directory_path,
                sub_directory,
            )
            os.makedirs(path, exist_ok=True)

    def create_gdbs_in_subdirectories(
        self,
        main_directory_path,
    ):
        for sub_directory in self.sub_directories:
            subdir_path = os.path.join(
                main_directory_path,
                sub_directory,
            )
            for gdb_name in self.gdb_names:
                gdb_path = os.path.join(subdir_path, f"{gdb_name}.gdb")
                if not arcpy.Exists(gdb_path):
                    arcpy.CreateFileGDB_management(
                        out_folder_path=subdir_path,
                        out_name=f"{gdb_name}.gdb",
                    )

    def create_subdirectory_structure(
        self,
        main_directory_path,
        subdir_structure,
    ):
        for sub_directory in self.sub_directories:
            structure_path = os.path.join(
                main_directory_path,
                sub_directory,
                subdir_structure,
            )
            os.makedirs(structure_path, exist_ok=True)


if __name__ == "__main__":
    main()
