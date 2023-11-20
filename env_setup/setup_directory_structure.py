import arcpy
import os

import config


def create_directory_structure(base_directory, sub_directories):
    # Create the main directory
    main_directory = os.path.join(base_directory, "automatic_generalization_outputs")
    os.makedirs(main_directory, exist_ok=True)

    # Create each subdirectory
    for subdir in sub_directories:
        path = os.path.join(main_directory, subdir)
        os.makedirs(path, exist_ok=True)
        print(f"Created directory: {path}")


def create_gdbs_in_subdirs(base_directory, sub_directories, gdb_names):
    for subdir in sub_directories:
        subdir_path = os.path.join(
            base_directory, "automatic_generalization_outputs", subdir
        )
        for gdb_name in gdb_names:
            gdb_path = os.path.join(subdir_path, f"{gdb_name}.gdb")
            if not arcpy.Exists(gdb_path):
                arcpy.CreateFileGDB_management(
                    out_folder_path=subdir_path, out_name=f"{gdb_name}.gdb"
                )
                print(f"Created GDB: {gdb_path}")
            else:
                print(f"GDB already exists: {gdb_path}")


# Subdirectories and GDB names
sub_directories = ["N50", "N100", "N250", "N500"]
gdb_names = ["admin", "arealdekke_flate", "byggning", "elv_bekk", "veg_sti"]

# Base directory defined in config.py
base_directory = config.output_folder

# Create directory structure and GDBs
create_directory_structure(base_directory, sub_directories)
create_gdbs_in_subdirs(base_directory, sub_directories, gdb_names)
