import arcpy
from enum import Enum
from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from env_setup import environment_setup
from file_manager import WorkFileManager
from file_manager.n10.file_manager_river import Elv_Bekk_N10
from input_data import input_arealdekke

# ========================
# Program
# ========================

def main():

    environment_setup.main()

    # Sets up work file manager and creates temporarily files
    working_fc = Elv_Bekk_N10.arealdekke_elv__n10_elv_bekk.value
    config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=config)

    files = create_wfm_gdbs(wfm=wfm)
    fetch_data(files=files)


# ========================
# Dictionary creation and
# Data fetching
# ========================

class fc(Enum):
    #Enum class for easier use of files dictionary. Prevents misspelling file variables
    rivers_fc="rivers_fc"

@timing_decorator
def create_wfm_gdbs(wfm: WorkFileManager) -> dict:
    """
    Creates all the temporarily files that are going to
    be used during the process of placing the lake heights.

    Args:
        wfm (WorkFileManager): The WorkFileManager instance that are keeping the files

    Returns:
        dict: A dictionary with all the files as variables
    """
    
    #Fetch data
    rivers_fc=wfm.build_file_path(file_name="rivers_fc", file_type="gdb")

    return {
        #Fetch data
        fc.rivers_fc: rivers_fc,

    }

@timing_decorator
def fetch_data(files: dict)->None:
    """
    Fetches relevant data.

    Args:
        files (dict): Dictionary with all the working files
    """
    
    arealdekke_lyr="arealdekke_lyr"
    arcpy.management.MakeFeatureLayer(in_features=input_arealdekke.arealdekke, out_layer=arealdekke_lyr, where_clause='')
    arcpy.management.CopyFeatures(in_features=arealdekke_lyr, out_feature_class=files[fc.rivers_fc])

# ========================
# Main functionality
# ========================

def find_centre_line(files:dict)->None:
    """
    Finds the centre of the rivers using a function made by Elling and Erlend.

    Args:
        files (dict): Dictionary with all the working files
    """

    pass

def min_distance_buffer(files:dict)->None:
    