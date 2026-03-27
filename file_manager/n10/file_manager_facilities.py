# Imports
from enum import Enum
from env_setup import global_config
from file_manager.base_file_manager import BaseFileManager

# Initialize BaseFileManager
scale = global_config.scale_n10
object_name = global_config.object_bygg_og_anlegg
file_manager = BaseFileManager(scale=scale, object_name=object_name)


# All scripts
ledning_file = "ledning"
railway_file = "railway"
train_station_file = "train_station"


class Facility_N10(Enum):
    # ========================================
    #                                  LEDNING
    # ========================================

    ledning__n10_facility = file_manager.generate_file_name_gdb(
        script_source_name=ledning_file, description="ledning"
    )

    ledning_output__n10_facility = file_manager.generate_file_name_gdb(
        script_source_name=ledning_file, description="ledning_output"
    )

    mast_output__n10_facility = file_manager.generate_file_name_gdb(
        script_source_name=ledning_file, description="mast_output"
    )

    # ========================================
    #                                     BANE
    # ========================================

    input_railway_n10 = file_manager.generate_file_name_gdb(
        script_source_name=railway_file, description="fkb"
    )
    output_railway_n10 = file_manager.generate_file_name_gdb(
        script_source_name=railway_file, description="fkb_generalisert"
    )

    railway__n10_facility = file_manager.generate_file_name_gdb(
        script_source_name=railway_file, description="railway"
    )

    railway_output__n10_facility = file_manager.generate_file_name_gdb(
        script_source_name=railway_file, description="railway_output"
    )

    # ========================================
    #                       ROTERING TOGSTASJON
    # ========================================

    train_station__n10_facility = file_manager.generate_file_name_gdb(
        script_source_name=train_station_file, description="train_station_rotated"
    )
