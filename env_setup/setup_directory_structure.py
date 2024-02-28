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


class ProjectDirectorySetup:
    _setup_done_globally = False

    def __init__(self, base_directory=config.output_folder):
        self.base_directory = base_directory
        self.sub_directories = [scale_n50, scale_n100, scale_n250, scale_n500]
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
    directory_setup_instance = ProjectDirectorySetup()
    directory_setup_instance.setup()
