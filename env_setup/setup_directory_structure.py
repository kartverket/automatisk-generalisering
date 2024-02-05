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


def main():
    # Create directory structure and GDBs
    create_directory_structure(
        base_directory,
        sub_directories,
        main_directory_name,
    )
    create_gdbs_in_subdirs(
        base_directory,
        sub_directories,
        gdb_names,
    )
    create_lyrx_directory_structure(
        base_directory,
        sub_directories,
        main_directory_name,
        lyrx_directory_name,
    )
    create_general_files_structure(
        base_directory,
        sub_directories,
        main_directory_name,
        general_files_name,
    )


def create_directory_structure(
    base_directory,
    sub_directories,
    main_directory_name,
):
    # Create the main directory
    main_directory = os.path.join(base_directory, main_directory_name)
    os.makedirs(main_directory, exist_ok=True)

    # Create each subdirectory
    for subdir in sub_directories:
        path = os.path.join(main_directory, subdir)
        os.makedirs(path, exist_ok=True)
        print(f"Created directory: {path}")


def create_gdbs_in_subdirs(
    base_directory,
    sub_directories,
    gdb_names,
):
    for subdir in sub_directories:
        subdir_path = os.path.join(
            base_directory,
            "automatic_generalization_outputs",
            subdir,
        )
        for gdb_name in gdb_names:
            gdb_path = os.path.join(
                subdir_path,
                f"{gdb_name}.gdb",
            )
            if not arcpy.Exists(gdb_path):
                arcpy.CreateFileGDB_management(
                    out_folder_path=subdir_path,
                    out_name=f"{gdb_name}.gdb",
                )
                print(f"Created GDB: {gdb_path}")
            else:
                print(f"GDB already exists: {gdb_path}")


def create_lyrx_directory_structure(
    base_directory,
    sub_directories,
    main_directory_name,
    lyrx_directory_name,
):
    # Iterate over each subdirectory to create 'lyrx_outputs' folder
    for subdir in sub_directories:
        lyrx_directory_path = os.path.join(
            base_directory,
            main_directory_name,
            subdir,
            lyrx_directory_name,
        )
        os.makedirs(
            lyrx_directory_path,
            exist_ok=True,
        )
        print(f"Created directory: {lyrx_directory_path}")


def create_general_files_structure(
    base_directory,
    sub_directories,
    main_directory_name,
    general_files_name,
):
    # Create the main directory
    main_directory = os.path.join(
        base_directory,
        main_directory_name,
    )
    os.makedirs(
        main_directory,
        exist_ok=True,
    )

    # Create 'general_files' folder in each subdirectory
    for subdir in sub_directories:
        general_files_path = os.path.join(
            main_directory,
            subdir,
            general_files_name,
        )
        os.makedirs(
            general_files_path,
            exist_ok=True,
        )
        print(f"Created 'general_files' folder: {general_files_path}")


# Subdirectories and GDB names
sub_directories = [
    scale_n50,
    scale_n100,
    scale_n250,
    scale_n500,
]
gdb_names = [
    object_admin,
    object_arealdekke_flate,
    object_bygning,
    object_elv_bekk,
    object_veg_sti,
]

# Base directory defined in config.py
base_directory = config.output_folder
if __name__ == "__main__":
    main()
