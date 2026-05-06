from datetime import datetime
from pathlib import Path

import arcpy
import config

from env_setup.global_config import (
    final_outputs,
    object_admin,
    object_arealdekke_flate,
    object_bane,
    object_bygg_og_anlegg,
    object_bygning,
    object_elv_bekk,
    object_hoyde,
    object_veg_sti,
    scale_n10,
    scale_n50,
    scale_n100,
    scale_n250,
    scale_n500,
)
from env_setup.project_layout import ProjectLayout

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
        - Creates the main directory and a per-scale subdirectory for organizing project files.
        - Generates geodatabases in each scale subdirectory for data storage.
        - Creates lyrx and general-files subdirectories within each scale subdirectory.

    Attributes:
        layout (ProjectLayout): The layout used to compose the directory and gdb paths.
        scales (list): Per-scale subdirectories to create.
        gdb_names (list): Names of the geodatabases to create in each scale subdirectory.
    """

    _setup_done_globally = False

    def __init__(self, layout: ProjectLayout | None = None):
        self.layout = layout or ProjectLayout(output_root=Path(config.output_folder))
        self.scales = [
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
            object_hoyde,
        ]

    def setup(self):
        if ProjectDirectorySetup._setup_done_globally:
            return

        self.layout.main_dir.mkdir(parents=True, exist_ok=True)
        for scale in self.scales:
            scale_dir = self.layout.scale_dir(scale)
            scale_dir.mkdir(parents=True, exist_ok=True)
            for gdb_name in self.gdb_names:
                gdb_path = self.layout.gdb(scale, gdb_name)
                if not arcpy.Exists(str(gdb_path)):
                    arcpy.CreateFileGDB_management(
                        out_folder_path=str(scale_dir),
                        out_name=f"{gdb_name}.gdb",
                    )
            self.layout.lyrx_dir(scale).mkdir(parents=True, exist_ok=True)
            self.layout.general_files_dir(scale).mkdir(parents=True, exist_ok=True)

        print("Directory structure completed.\n")
        ProjectDirectorySetup._setup_done_globally = True


if __name__ == "__main__":
    main()
