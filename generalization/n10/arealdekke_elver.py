import arcpy
from enum import Enum
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools import custom_arcpy

from composition_configs import core_config
from env_setup import environment_setup
from file_manager import WorkFileManager
from file_manager.n10.file_manager_river import Elv_Bekk_N10
from input_data import input_arealdekke

class prog_config(Enum):
    #Minimum width (metres) for river polygon to show up on map
    min_width_rivers=6

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

    river_segments_under_minimum(files=files)
    find_centre_line(files=files)
    enlarge_rivers_below_min(files=files)


# ========================
# Dictionary creation and
# Data fetching
# ========================

class fc(Enum):
    #Enum class for easier use of files dictionary. Prevents misspelling file variables
    rivers_fc="rivers_fc"
    river_centre_fc="river_centre_fc"
    centre_buffed_fc="centre_buffed_fc"
    rivers_polygon_line_fc="rivers_polygon_line_fc"
    rivers_polygon_line_buffed="rivers_polygon_line_buffed"
    small_river_centre_lines_fc="small_river_centre_lines_fc"
    river_segments_under_minimum_fc="river_segments_under_minimum_fc"
    river_segments_above_minimum_fc="river_segments_above_minimum_fc"
    river_above_minimum_buffed_fc="river_above_minimum_buffed_fc"
    river_below_min_edge_segments_fc="river_below_min_edge_segments_fc"
    river_below_min_edge_segments_single_fc="river_below_min_edge_segments_single_fc"
    centre_buffed_edge_intersections_fc="centre_buffed_edge_intersections_fc"

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
    river_centre_fc=wfm.build_file_path(file_name="river_centre_fc", file_type="gdb")
    centre_buffed_fc=wfm.build_file_path(file_name="centre_buffed_fc", file_type="gdb")
    rivers_polygon_line_fc=wfm.build_file_path(file_name="rivers_polygon_line_fc", file_type="gdb")
    rivers_polygon_line_buffed=wfm.build_file_path(file_name="rivers_polygon_line_buffed", file_type="gdb")
    small_river_centre_lines_fc=wfm.build_file_path(file_name="small_river_centre_lines_fc", file_type="gdb")
    river_segments_under_minimum_fc=wfm.build_file_path(file_name="river_segments_under_minimum_fc", file_type="gdb")
    river_segments_above_minimum_fc=wfm.build_file_path(file_name="river_segments_above_minimum_fc", file_type="gdb")
    river_above_minimum_buffed_fc=wfm.build_file_path(file_name="river_above_minimum_buffed_fc", file_type="gdb")
    river_below_min_edge_segments_fc=wfm.build_file_path(file_name="river_below_min_edge_segments_fc", file_type="gdb")
    river_below_min_edge_segments_single_fc=wfm.build_file_path(file_name="river_below_min_edge_segments_single_fc", file_type="gdb")
    centre_buffed_edge_intersections_fc=wfm.build_file_path(file_name="centre_buffed_edge_intersections_fc", file_type="gdb")

    return {
        #Fetch data
        fc.rivers_fc:rivers_fc,
        fc.river_centre_fc:river_centre_fc,
        fc.centre_buffed_fc:centre_buffed_fc,
        fc.rivers_polygon_line_fc:rivers_polygon_line_fc,
        fc.rivers_polygon_line_buffed:rivers_polygon_line_buffed,
        fc.small_river_centre_lines_fc:small_river_centre_lines_fc,
        fc.river_segments_under_minimum_fc:river_segments_under_minimum_fc,
        fc.river_segments_above_minimum_fc:river_segments_above_minimum_fc,
        fc.river_above_minimum_buffed_fc:river_above_minimum_buffed_fc,
        fc.river_below_min_edge_segments_fc:river_below_min_edge_segments_fc,
        fc.river_below_min_edge_segments_single_fc:river_below_min_edge_segments_single_fc,
        fc.centre_buffed_edge_intersections_fc:centre_buffed_edge_intersections_fc

    }

@timing_decorator
def fetch_data(files: dict)->None:
    """
    Fetches relevant data.

    Args:
        files (dict): Dictionary with all the working files
    """
    
    #Get data from gdb
    arealdekke_lyr="arealdekke_lyr"
    arcpy.management.MakeFeatureLayer(in_features=input_arealdekke.arealdekke, out_layer=arealdekke_lyr, where_clause="arealdekke='Ferskvann_elv_bekk'")
    
    #Repair data to remove self intersections
    arcpy.management.RepairGeometry(in_features=arealdekke_lyr, delete_null='DELETE_NULL')
    arcpy.management.EliminatePolygonPart(in_features=arealdekke_lyr, out_feature_class=files[fc.rivers_fc])

# ========================
# Main functionality
# ========================

@timing_decorator
def river_segments_under_minimum(files:dict)->None:
    rivers_lyr="rivers_lyr"
    rivers_polygon_line_lyr="rivers_polygon_line_fc"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.rivers_fc], out_layer=rivers_lyr)
    arcpy.management.PolygonToLine(in_features=rivers_lyr, out_feature_class=files[fc.rivers_polygon_line_fc])
    arcpy.management.MakeFeatureLayer(in_features=files[fc.rivers_polygon_line_fc], out_layer=rivers_polygon_line_lyr)
    
    arcpy.analysis.Buffer(
        in_features=rivers_polygon_line_lyr, 
        out_feature_class=files[fc.rivers_polygon_line_buffed], 
        buffer_distance_or_field=f'{prog_config.min_width_rivers.value/2} Meters',
        line_side='FULL',
        )
    
    rivers_polygon_line_buffed_lyr="rivers_polygon_line_buffed_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.rivers_polygon_line_buffed], out_layer=rivers_polygon_line_buffed_lyr)

    arcpy.analysis.Erase(in_features=rivers_lyr, erase_features=rivers_polygon_line_buffed_lyr, out_feature_class=files[fc.river_segments_above_minimum_fc])
    river_segments_above_minimum_lyr="river_segments_above_minimum_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.river_segments_above_minimum_fc], out_layer=river_segments_above_minimum_lyr)
    arcpy.analysis.Buffer(
        in_features=river_segments_above_minimum_lyr,
        out_feature_class=files[fc.river_above_minimum_buffed_fc],
        buffer_distance_or_field=f'{prog_config.min_width_rivers.value/2} Meters',
        line_side='FULL'
    )
    river_above_minimum_buffed_lyr="river_above_minimum_buffed_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.river_above_minimum_buffed_fc], out_layer=river_above_minimum_buffed_lyr)
    arcpy.analysis.Erase(in_features=rivers_lyr, erase_features=river_above_minimum_buffed_lyr, out_feature_class=files[fc.river_segments_under_minimum_fc])
    
@timing_decorator
def find_centre_line(files:dict)->None:
    """
    Finds the centre of the rivers using a function made by Elling and Erlend.

    Args:
        files (dict): Dictionary with all the working files
    """

    hydro_polygons_lyr="hydro_polygons_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.river_segments_under_minimum_fc], out_layer=hydro_polygons_lyr)
    arcpy.cartography.CollapseHydroPolygon(
        in_features=[hydro_polygons_lyr],
        out_line_feature_class=files[fc.river_centre_fc],
        merge_adjacent_input_polygons='NO_MERGE'
    )

def enlarge_rivers_below_min(files:dict)->None:

    centre_lines_lyr="centre_lines_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.river_centre_fc], out_layer=centre_lines_lyr)

    arcpy.analysis.Buffer(
        in_features=centre_lines_lyr,
        out_feature_class=files[fc.centre_buffed_fc],
        buffer_distance_or_field=f'{prog_config.min_width_rivers.value/2} Meters',
        line_side='FULL',
        line_end_type='FLAT',
        dissolve_option='ALL'
    )

    centre_buffed_lyr="centre_buffed_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.centre_buffed_fc], out_layer=centre_buffed_lyr)
    polyline_rivers_edge_lyr="polyline_rivers_edge_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.rivers_polygon_line_fc], out_layer=polyline_rivers_edge_lyr)

    arcpy.analysis.PairwiseClip(in_features=polyline_rivers_edge_lyr, clip_features=centre_buffed_lyr, out_feature_class=files[fc.river_below_min_edge_segments_fc])
    #arcpy.analysis.Clip(in_features=polyline_rivers_edge_lyr, clip_features=centre_buffed_lyr, out_feature_class=files[fc.river_below_min_edge_segments_fc])
    
    river_below_min_edge_segments_lyr="river_below_min_edge_segments_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.river_below_min_edge_segments_fc], out_layer=river_below_min_edge_segments_lyr)
    arcpy.management.MultipartToSinglepart(in_features=river_below_min_edge_segments_lyr, out_feature_class=files[fc.river_below_min_edge_segments_single_fc])
    
    river_below_min_edge_segments_single_lyr="river_below_min_edge_segments_single_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.river_below_min_edge_segments_single_fc], out_layer=river_below_min_edge_segments_single_lyr)

    centre_buffed_edge_intersections_lyr="centre_buffed_edge_intersections_lyr"
    arcpy.sfa.OverlayLayers(
        inputLayer=centre_buffed_lyr, 
        overlayLayer=river_below_min_edge_segments_single_lyr, 
        outputName=centre_buffed_edge_intersections_lyr,
        overlayType='INTERSECT'
        )
    arcpy.management.CopyFeatures(in_features=centre_buffed_edge_intersections_lyr, out_feature_class=files[fc.centre_buffed_edge_intersections_fc])

if __name__ == "__main__":
    main()
