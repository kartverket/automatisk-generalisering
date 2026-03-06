import arcpy
from enum import Enum
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools import custom_arcpy

from composition_configs import core_config
from env_setup import environment_setup
from file_manager import WorkFileManager
from file_manager.n10.file_manager_river import Elv_Bekk_N10
from input_data import input_arealdekke

arcpy.env.overwriteOutput = True

class prog_config(Enum):
    #Minimum width (metres) for river polygon to show up on map
    min_width_rivers=6 #Opprinnelig 6

# ========================
# Program
# ========================

'''
    Choose areas that needs to be generalised:
    - Find areas that are wide enough (create buffer with negative minimum width radius)
    - Buff the areas that are wide enough and buff them with a full buffer to get them back to their original size.
    - Remove the wide enough areas buffer from the original rivers layer with erase.
    - Buff the new river segments that are not wide enough with a full buffer with a 10 metre radius.

    Center line:
    - Create a centre line inside the small river segments. Buff the centre line afterwards with a buffer with a large enough radius.

    Merge:
    - Merge the rivers with the buffer and dissolve them.
    '''

def main():

    environment_setup.main()

    # Sets up work file manager and creates temporarily files
    working_fc = Elv_Bekk_N10.arealdekke_elv__n10_elv_bekk.value
    config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=config)

    files = create_wfm_gdbs(wfm=wfm)
    fetch_data(files=files)

    cookie_cutting(files=files)
    enlarge_small_rivers(files=files)

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
    
    rivers_fixed="rivers_fixed"
    overkill_buffer="overkill_buffer"
    rivers_merged="rivers_merged"
    river_segments_under_minimum_buffed_fc="river_segments_under_minimum_buffed_fc"
    river_segments_under_minimum_single_fc="river_segments_under_minimum_single_fc"

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

    overkill_buffer=wfm.build_file_path(file_name="overkill_buffer", file_type="gdb")
    rivers_merged=wfm.build_file_path(file_name="rivers_merged", file_type="gdb")
    rivers_fixed=wfm.build_file_path(file_name="rivers_fixed", file_type="gdb")
    river_segments_under_minimum_buffed_fc=wfm.build_file_path(file_name="river_segments_under_minimum_buffed_fc", file_type="gdb")
    river_segments_under_minimum_single_fc=wfm.build_file_path(file_name="river_segments_under_minimum_single_fc", file_type="gdb")

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
        fc.centre_buffed_edge_intersections_fc:centre_buffed_edge_intersections_fc,
        fc.overkill_buffer:overkill_buffer,
        fc.rivers_merged:rivers_merged,
        fc.rivers_fixed:rivers_fixed,
        fc.river_segments_under_minimum_buffed_fc:river_segments_under_minimum_buffed_fc,
        fc.river_segments_under_minimum_single_fc:river_segments_under_minimum_single_fc

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
def cookie_cutting(files:dict)->None:

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
        line_end_type='FLAT'
        )
    
    rivers_polygon_line_buffed_lyr="rivers_polygon_line_buffed_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.rivers_polygon_line_buffed], out_layer=rivers_polygon_line_buffed_lyr)
    arcpy.analysis.Erase(in_features=rivers_lyr, erase_features=rivers_polygon_line_buffed_lyr, out_feature_class=files[fc.river_segments_above_minimum_fc])
    
    river_segments_above_minimum_lyr="river_segments_above_minimum_fc"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.river_segments_above_minimum_fc], out_layer=river_segments_above_minimum_lyr)

    arcpy.analysis.Buffer(
        in_features=river_segments_above_minimum_lyr,
        out_feature_class=files[fc.river_above_minimum_buffed_fc],
        buffer_distance_or_field=f'{prog_config.min_width_rivers.value/2} Meters',
        line_side='FULL',
        line_end_type='FLAT',
        dissolve_option='NONE'
    )

    river_above_minimum_buffed_lyr="river_above_minimum_buffed_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.river_above_minimum_buffed_fc], out_layer=river_above_minimum_buffed_lyr)
    arcpy.analysis.Erase(in_features=rivers_lyr, erase_features=river_above_minimum_buffed_lyr, out_feature_class=files[fc.river_segments_under_minimum_fc])

    river_segments_under_minimum_lyr="river_segments_under_minimum_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.river_segments_under_minimum_fc], out_layer=river_segments_under_minimum_lyr)

    arcpy.management.RepairGeometry(in_features=river_segments_under_minimum_lyr, delete_null='DELETE_NULL')

    arcpy.management.MultipartToSinglepart(in_features=river_segments_under_minimum_lyr, out_feature_class=files[fc.river_segments_under_minimum_single_fc])
    river_segments_under_minimum_single_lyr="river_segments_under_minimum_single_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.river_segments_under_minimum_single_fc], out_layer=river_segments_under_minimum_single_lyr)

    arcpy.management.SelectLayerByAttribute(in_layer_or_view=river_segments_under_minimum_single_lyr, selection_type='NEW_SELECTION', where_clause='SHAPE_AREA>1000')

    arcpy.analysis.Buffer(
        in_features=river_segments_under_minimum_single_lyr,
        out_feature_class=files[fc.overkill_buffer],
        buffer_distance_or_field='10 Meters',
        line_side='FULL',
        dissolve_option='NONE'
    )

    overkill_buffer_lyr="overkill_buffer_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.overkill_buffer], out_layer=overkill_buffer_lyr)
    arcpy.analysis.PairwiseClip(in_features=rivers_lyr, clip_features=overkill_buffer_lyr, out_feature_class=files[fc.river_segments_under_minimum_buffed_fc])
 
@timing_decorator
def enlarge_small_rivers(files:dict)->None:
    """
    Finds the centre of the rivers.

    Args:
        files (dict): Dictionary with all the working files
    """

    hydro_polygons_lyr="hydro_polygons_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.river_segments_under_minimum_buffed_fc], out_layer=hydro_polygons_lyr)
    arcpy.cartography.CollapseHydroPolygon(
        in_features=[hydro_polygons_lyr],
        out_line_feature_class=files[fc.river_centre_fc],
        merge_adjacent_input_polygons='NO_MERGE'
    )

    centre_lines_lyr="centre_lines_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.river_centre_fc], out_layer=centre_lines_lyr)

    arcpy.analysis.PairwiseBuffer(
        in_features=centre_lines_lyr,
        out_feature_class=files[fc.centre_buffed_fc],
        buffer_distance_or_field='2 Meters',
        dissolve_option='NONE'
    )

    centre_buffed_lyr="centre_buffed_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.centre_buffed_fc], out_layer=centre_buffed_lyr)

    original_rivers_lyr="original_rivers_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.rivers_fc], out_layer=original_rivers_lyr)

    arcpy.management.Merge(inputs=[original_rivers_lyr, centre_buffed_lyr], output=files[fc.rivers_merged])

    rivers_merged_lyr="rivers_merged_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.rivers_merged], out_layer=rivers_merged_lyr)
    arcpy.management.Dissolve(in_features=rivers_merged_lyr, out_feature_class=files[fc.rivers_fixed])

if __name__ == "__main__":
    main()
