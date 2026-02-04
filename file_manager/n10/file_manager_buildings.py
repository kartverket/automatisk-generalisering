# Imports
from enum import Enum
from env_setup import global_config
from file_manager.base_file_manager import BaseFileManager

# Initialize BaseFileManager
scale = global_config.scale_n10
object_name = global_config.object_bygning
file_manager = BaseFileManager(scale=scale, object_name=object_name)

squash_buildings = "squash_buildings"


class Building_N10(Enum):
    """
    An enumeration for building-related geospatial data file paths within the N10 scale and building object context.

    Utilizes the BaseFileManager to generate standardized file paths for geodatabase files, general files, and layer files,
    tailored to building data preparation and analysis tasks.

    Example Syntaxes:
        - For Geodatabase (.gdb) Files:
            the_file_name_of_the_script___the_description_of_the_file___n100_building = file_manager.generate_file_name_gdb(
                script_source_name="the_file_name_of_the_script",
                description="the_description_of_the_file"
            )

        - For General Files (e.g., .txt, .csv):
            the_file_name_of_the_script___the_description_of_the_file___n100_building_filetype_extension = file_manager.generate_file_name_general_files(
                script_source_name="the_file_name_of_the_script",
                description="the_description_of_the_file",
                file_type="filetype_extension"
            )

        - For ArcGIS Layer Files (.lyrx):
            the_file_name_of_the_script___the_description_of_the_file___n100_building_lyrx = file_manager.generate_file_name_lyrx(
                script_source_name="the_file_name_of_the_script",
                description="the_description_of_the_file"
            )

    These examples show how to utilize the BaseFileManager's methods to generate file paths for different types of files,
    reflecting the specific needs and naming conventions of building data management within the project.
    """

    ###########################################
    ############# SQUASH BUILDINGS ############
    ###########################################

    squash_buildings___other_buildings___n10 = file_manager.generate_file_name_gdb(
        script_source_name=squash_buildings, description="other_buildings"
    )

    squash_buildings___adjacent_buildings___n10 = file_manager.generate_file_name_gdb(
        script_source_name=squash_buildings, description="adjacent_buildings"
    )

    squash_buildings___neighbors___n10 = file_manager.generate_file_name_gdb(
        script_source_name=squash_buildings, description="neighbors"
    )

    squash_buildings___neighbors_dissolved___n10 = file_manager.generate_file_name_gdb(
        script_source_name=squash_buildings, description="neighbors_dissolved"
    )

    squash_buildings___clustered___n10 = file_manager.generate_file_name_gdb(
        script_source_name=squash_buildings, description="clustered"
    )

    squash_buildings___non_clustered___n10 = file_manager.generate_file_name_gdb(
        script_source_name=squash_buildings, description="non_clustered"
    )

    squash_buildings___harmonize_attributes___n10 = file_manager.generate_file_name_gdb(
        script_source_name=squash_buildings, description="harmonize_attributes"
    )

    squash_buildings___final___n10 = file_manager.generate_file_name_gdb(
        script_source_name=squash_buildings, description="final"
    )
