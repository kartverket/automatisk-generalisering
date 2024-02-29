import arcpy
import os

import config
from env_setup.global_config import (
    scale_n50,
    scale_n100,
    scale_n250,
    scale_n500,
    object_admin,
    object_arealdekke_flate,
    object_bygning,
    object_elv_bekk,
    object_veg_sti,
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
    arc_gis_environment_setup = ArcGisEnvironmentSetup()
    arc_gis_environment_setup.setup()

    directory_setup_instance = ProjectDirectorySetup()
    directory_setup_instance.setup()


class ArcGisEnvironmentSetup:
    """
    Configures and initializes the ArcGIS Pro environment settings.

    Summary:
        Sets up the ArcGIS Pro environment with specified workspace and spatial reference. Ensures setup is performed only once globally.

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
            print("ArcGIS Pro environment setup has already been completed. Skipping.")
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

        print("ArcGIS Pro environment setup completed with the following settings:")
        print("- Overwrite Output: True")
        print(f"- Workspace: {arcpy.env.workspace}")
        print(f"- Output Coordinate System: EPSG:{self.spatial_reference}")
        print(f"- XY Tolerance: {arcpy.env.XYTolerance}")
        print(f"- XY Resolution: {arcpy.env.XYResolution}")
        print(f"- Parallel Processing Factor: {arcpy.env.parallelProcessingFactor}")
        print("ArcGIS Pro environment setup completed.\n")


class ProjectDirectorySetup:
    """
    Creates and configures the project directory structure and geodatabases.

    Summary:
        Establishes a predefined directory structure for project files and geodatabases, ensuring it's done only once globally.

    Details:
        - Checks if the global setup has already been completed to prevent redundancy.
        - Creates a main directory and specified subdirectories for organizing project files.
        - Generates geodatabases in the designated subdirectories for data storage.
        - Sets up directories for layer files (`lyrx`) to organize map layer configurations.
        - Creates a directory for general files, facilitating organized storage of miscellaneous project files.

    Attributes:
        base_directory (str): The root directory for the project structure.
        sub_directories (list): A list of names for subdirectories to be created within the project structure.
        gdb_names (list): Names of the geodatabases to be created in each subdirectory.
    """

    _setup_done_globally = False

    def __init__(self, base_directory=config.output_folder):
        self.base_directory = base_directory
        self.sub_directories = [
            scale_n50,
            scale_n100,
            scale_n250,
            scale_n500,
        ]
        self.gdb_names = [
            object_admin,
            object_arealdekke_flate,
            object_bygning,
            object_elv_bekk,
            object_veg_sti,
        ]

    def setup(self):
        if ProjectDirectorySetup._setup_done_globally:
            print("Global setup has already been completed. Skipping.")
            return

        self.create_directory_structure()
        self.create_gdbs_in_subdirs()
        self.create_lyrx_directory_structure()
        self.create_general_files_structure()

        ProjectDirectorySetup._setup_done_globally = True

    def create_directory_structure(self):
        main_directory = os.path.join(self.base_directory, main_directory_name)
        os.makedirs(main_directory, exist_ok=True)
        for subdir in self.sub_directories:
            path = os.path.join(main_directory, subdir)
            os.makedirs(path, exist_ok=True)
            print(f"Created directory: {path}")

    def create_gdbs_in_subdirs(self):
        for subdir in self.sub_directories:
            subdir_path = os.path.join(
                self.base_directory, "automatic_generalization_outputs", subdir
            )
            for gdb_name in self.gdb_names:
                gdb_path = os.path.join(subdir_path, f"{gdb_name}.gdb")
                if not arcpy.Exists(gdb_path):
                    arcpy.CreateFileGDB_management(subdir_path, f"{gdb_name}.gdb")
                    print(f"Created GDB: {gdb_path}")
                else:
                    print(f"GDB already exists: {gdb_path}")

    def create_lyrx_directory_structure(self):
        for subdir in self.sub_directories:
            lyrx_directory_path = os.path.join(
                self.base_directory, main_directory_name, subdir, lyrx_directory_name
            )
            os.makedirs(lyrx_directory_path, exist_ok=True)
            print(f"Created directory: {lyrx_directory_path}")

    def create_general_files_structure(self):
        main_directory = os.path.join(self.base_directory, main_directory_name)
        os.makedirs(main_directory, exist_ok=True)
        for subdir in self.sub_directories:
            general_files_path = os.path.join(
                main_directory, subdir, general_files_name
            )
            os.makedirs(general_files_path, exist_ok=True)
            print(f"Created 'general_files' folder: {general_files_path}")


if __name__ == "__main__":
    main()
