import arcpy
from enum import Enum
from custom_tools.decorators.timing_decorator import timing_decorator

from composition_configs import core_config
from env_setup import environment_setup
from file_manager import WorkFileManager
from file_manager.n10.file_manager_landuse import Landuse_N10
from input_data import input_arealdekke

arcpy.env.overwriteOutput = True

'''
Function that buff small polygon segments.
Args: target arealdekk (string), locked arealdekks (list: arealdekks), output feature class (string), min width of polygon segments (int, meters)
'''
@timing_decorator
def buff_small_polygon_segments(
    target_fc,
    locked_fc:list,
    out_fc,
    min_width:int
    ):

    # Sets up work file manager and creates temporarily files
    working_fc = Landuse_N10.buffed_polygon_segments__n10_landuse.value
    config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=config)

    files=files_setup(wfm=wfm)

    extract_data(files=files, target_fc=target_fc, locked_fc=locked_fc)
    find_segments_under_min(files=files, min_width=min_width)
    choose_target_areas(files=files)
    #buff_small_segments(files=files, min_width=min_width, out_fc=out_feature_class)

class fc (Enum):
    target_fc="target_fc"
    locked_fc="locked_fc"

    target_out_buffer="target_out_buffer"
    locked_fc_conflicts="locked_fc_conflicts"

    input_polygon_edge="input_polygon_edge"
    input_polygon_minus_buffer="input_polygon_minus_buffer"
    core_of_segments_wide_enough="core_of_segments_wide_enough"
    segments_wide_enough="segments_wide_enough"
    core_wide_enough_segments_singlepart="core_wide_enough_segments_singlepart"
    segments_too_small="segments_too_small"
    segments_too_small_single="segments_too_small_single"

    overkill_buffer="overkill_buffer"
    areas_chosen="areas_chosen"

    centre_line="centre_line"
    small_segments_centre="small_segments_centre"
    small_segments_enlarged="small_segments_enlarged"
    small_segments_enlarged_single="small_segments_enlarged_single"


def files_setup(wfm: WorkFileManager) -> dict:

    #Extract data
    target_fc=wfm.build_file_path(file_name="target_fc", file_type="gdb")
    locked_fc=wfm.build_file_path(file_name="locked_fc", file_type="gdb")

    #Get shared boundary
    target_out_buffer=wfm.build_file_path(file_name="target_out_buffer", file_type="gdb")
    locked_fc_conflicts=wfm.build_file_path(file_name="locked_fc_conflicts", file_type="gdb")

    #Find segments under min
    input_polygon_edge=wfm.build_file_path(file_name="input_polygon_edge", file_type="gdb")
    input_polygon_minus_buffer=wfm.build_file_path(file_name="input_polygon_minus_buffer", file_type="gdb")
    core_of_segments_wide_enough=wfm.build_file_path(file_name="core_of_segments_wide_enough", file_type="gdb")
    segments_wide_enough=wfm.build_file_path(file_name="segments_wide_enough", file_type="gdb")
    core_wide_enough_segments_singlepart=wfm.build_file_path(file_name="core_wide_enough_segments_singlepart", file_type="gdb")
    segments_too_small=wfm.build_file_path(file_name="segments_too_small", file_type="gdb")
    segments_too_small_single=wfm.build_file_path(file_name="segments_too_small_single", file_type="gdb")

    #Choose target areas
    overkill_buffer=wfm.build_file_path(file_name="overkill_buffer", file_type="gdb")
    areas_chosen=wfm.build_file_path(file_name="areas_chosen", file_type="gdb")

    #Buff small segments
    centre_line=wfm.build_file_path(file_name="centre_line", file_type="gdb")
    small_segments_centre=wfm.build_file_path(file_name="small_segments_centre", file_type="gdb")
    small_segments_enlarged=wfm.build_file_path(file_name="small_segments_enlarged", file_type="gdb")
    small_segments_enlarged_single=wfm.build_file_path(file_name="small_segments_enlarged_single", file_type="gdb")

    return {
        fc.target_fc:target_fc,
        fc.locked_fc:locked_fc,

        fc.target_out_buffer:target_out_buffer,
        fc.locked_fc_conflicts:locked_fc_conflicts,

        fc.input_polygon_edge:input_polygon_edge,
        fc.input_polygon_minus_buffer:input_polygon_minus_buffer,
        fc.core_of_segments_wide_enough:core_of_segments_wide_enough,
        fc.segments_wide_enough:segments_wide_enough,
        fc.core_wide_enough_segments_singlepart:core_wide_enough_segments_singlepart,
        fc.segments_too_small:segments_too_small,
        fc.segments_too_small_single:segments_too_small_single,

        fc.overkill_buffer:overkill_buffer,
        fc.areas_chosen:areas_chosen,

        fc.centre_line:centre_line,
        fc.small_segments_centre:small_segments_centre,
        fc.small_segments_enlarged:small_segments_enlarged,
        fc.small_segments_enlarged_single:small_segments_enlarged_single
    }


@timing_decorator
def extract_data(files:dict, target_fc, locked_fc:list)->None:#TODO: Done?
    
    #Extract the target fc from the data layer.
    target_fc_lyr="target_fc_lyr"
    arcpy.management.MakeFeatureLayer(in_features=input_arealdekke.arealdekke, out_layer=target_fc_lyr, where_clause=f"arealdekke='{target_fc}'")
    arcpy.management.CopyFeatures(in_features=target_fc_lyr, out_feature_class=files[fc.target_fc])

    #Extract the locked areas from the data layer that share a line with the target fc.
    locked_fc_lyr="locked_fc_lyr"
    arcpy.management.MakeFeatureLayer(in_features=input_arealdekke.arealdekke, out_layer=locked_fc_lyr, where_clause=f"arealdekke IN {tuple(list)}")
    arcpy.management.SelectLayerByLocation(in_layer=locked_fc_lyr, overlap_type='SHARE_A_LINE_SEGMENT_WITH', select_features=target_fc_lyr, selection_type='NEW_SELECTION')
    arcpy.management.CopyFeatures(in_features=locked_fc_lyr, out_feature_class=files[fc.locked_fc])
  
@timing_decorator
def find_segments_under_min(files:dict, min_width:int)->None:

    #Create a lyr with the outline of the input polygon
    input_polygon_lyr="input_polygon_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.target_fc], out_layer=input_polygon_lyr)
    arcpy.management.PolygonToLine(in_features=input_polygon_lyr, out_feature_class=files[fc.input_polygon_edge])

    #Use polygon outline to create a negative buffer
    input_polygon_edge_lyr="input_polygon_edge_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.input_polygon_edge], out_layer=input_polygon_edge_lyr)

    arcpy.analysis.Buffer(
        in_features=input_polygon_edge_lyr,
        out_feature_class=files[fc.input_polygon_minus_buffer],
        buffer_distance_or_field=f"{min_width} Meters",
        line_side="FULL"
    )

    #Areas not intersecting the minus buffer are large enough. Extract them into its own layer.
    input_polygon_minus_buffer_lyr="input_polygon_minus_buffer_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.input_polygon_minus_buffer], out_layer=input_polygon_minus_buffer_lyr)

    arcpy.analysis.Erase(in_features=input_polygon_lyr, erase_features=input_polygon_minus_buffer_lyr, out_feature_class=files[fc.core_of_segments_wide_enough])

    #Create a full buffer for the core of the wide enough segments to get them back to their original size
    core_of_segments_wide_enough_lyr="core_of_segments_wide_enough_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.core_of_segments_wide_enough], out_layer=core_of_segments_wide_enough_lyr)

    arcpy.management.RepairGeometry(in_features=core_of_segments_wide_enough_lyr, delete_null='DELETE_NULL')
    arcpy.management.MultipartToSinglepart(in_features=core_of_segments_wide_enough_lyr, out_feature_class=files[fc.core_wide_enough_segments_singlepart])

    core_wide_enough_segments_singlepart_lyr="core_wide_enough_segments_singlepart_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.core_wide_enough_segments_singlepart], out_layer=core_wide_enough_segments_singlepart_lyr)

    arcpy.analysis.PairwiseBuffer(
        in_features=core_wide_enough_segments_singlepart_lyr,
        out_feature_class=files[fc.segments_wide_enough],
        buffer_distance_or_field=f"{min_width} Meters"
    )

    #Remove the large enough segments from the original polyon
    segments_wide_enough_lyr="segments_wide_enough_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.segments_wide_enough], out_layer=segments_wide_enough_lyr)

    arcpy.analysis.Erase(in_features=input_polygon_lyr, erase_features=segments_wide_enough_lyr, out_feature_class=files[fc.segments_too_small])

@timing_decorator
def choose_target_areas(files:dict)->None:
    
    #Create an overkill buffer that includes the small segments and some of the area around.
    segments_too_small_single_lyr="segments_too_small_single_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.segments_too_small], out_layer=segments_too_small_single_lyr)
    
    arcpy.analysis.Buffer(
        in_features=segments_too_small_single_lyr,
        out_feature_class=files[fc.overkill_buffer],
        buffer_distance_or_field="15 Meters",
        line_side="FULL"
    )

    #Clip original polygon to get area with the too small segments
    overkill_buffer_lyr="overkill_buffer_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.overkill_buffer], out_layer=overkill_buffer_lyr)

    original_polygon_lyr="original_polygon_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.input_data], out_layer=original_polygon_lyr)

    try:
        arcpy.analysis.PairwiseClip(in_features=original_polygon_lyr, clip_features=overkill_buffer_lyr, out_feature_class=files[fc.areas_chosen])
    except:
        arcpy.analysis.Clip(in_features=original_polygon_lyr, clip_features=overkill_buffer_lyr, out_feature_class=files[fc.areas_chosen])

@timing_decorator
def get_shared_locked_boundary(files:dict)->None: #TODO: Done?
    
    #Clip the locked fcs to the chosen target area buffer

    #Create a buffer around the clipped locked area

    #Clip the buffed area to the 
    
    #select the line that share a boundary with 

    target_polygon_lyr="target_polygon_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.target_fc], out_layer=target_polygon_lyr)

    arcpy.analysis.Buffer(
        in_features=target_polygon_lyr,
        out_feature_class=files[fc.target_out_buffer],
        buffer_distance_or_field='1 Meters',
        line_side='OUTSIDE_ONLY'
    )

    target_out_buffer_lyr="target_out_buffer_lyr"
    locked_fc_lyr="locked_fc_lyr"

    arcpy.management.MakeFeatureLayer(in_features=files[fc.target_out_buffer], out_layer=target_out_buffer_lyr)
    arcpy.management.MakeFeatureLayer(in_features=files[fc.locked_fc], out_layer=locked_fc_lyr)

    arcpy.analysis.Clip(
        in_features=locked_fc_lyr,
        clip_features=target_out_buffer_lyr,
        out_feature_class=files[fc.locked_fc_conflicts]
    )
 

@timing_decorator
def buff_locked_fc(files:dict, min_width:int)->None:
    #Buff the locked fs if they area within the chosen target area

@timing_decorator
def buff_small_segments(files:dict, min_width:int, out_fc)->None:

    #Use collapse hydro polygon to find the centre line of the segments
    chosen_areas_lyr="chosen_areas_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.areas_chosen], out_layer=chosen_areas_lyr)

    arcpy.cartography.CollapseHydroPolygon(
        in_features=chosen_areas_lyr,
        out_line_feature_class=files[fc.centre_line],
        merge_adjacent_input_polygons="NO_MERGE"
    )

    #Erase large enough areas from the centre line and the areas too close to the locked areas

    centre_line_lyr="centre_line_lyr"
    large_segments_lyr="large_segments_lyr"



    arcpy.management.MakeFeatureLayer(in_features=files[fc.centre_line], out_layer=centre_line_lyr)
    arcpy.management.MakeFeatureLayer(in_features=files[fc.segments_wide_enough], out_layer=large_segments_lyr)

    arcpy.analysis.Erase(in_features=centre_line_lyr, erase_features=large_segments_lyr, out_feature_class=files[fc.small_segments_centre])

    #Buff the centre line to min width
    small_segments_centre_lyr="small_segments_centre_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.small_segments_centre], out_layer=small_segments_centre_lyr)

    try:
        arcpy.analysis.PairwiseBuffer(
            in_features=small_segments_centre_lyr,
            out_feature_class=files[fc.small_segments_enlarged],
            buffer_distance_or_field=f"{min_width} Meters"
        )

    except:
        arcpy.analysis.PairBuffer(
            in_features=small_segments_centre_lyr,
            out_feature_class=files[fc.small_segments_enlarged],
            buffer_distance_or_field=f"{min_width} Meters"
        )
    
    #Make the segments singlepart
    small_segments_enlarged_lyr="small_segments_enlarged_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.small_segments_enlarged], out_layer=small_segments_enlarged_lyr)

    arcpy.management.MultipartToSinglepart(in_features=small_segments_enlarged_lyr, out_feature_class=files[fc.small_segments_enlarged_single])

    #Do a spatial join to get the arealdekke value.
    small_segments_enlarged_single_lyr="small_segments_enlarged_single_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.small_segments_enlarged_single], out_layer=small_segments_enlarged_single_lyr)

    arcpy.analysis.SpatialJoin(
        target_features=small_segments_enlarged_single_lyr,
        join_features=chosen_areas_lyr,
        out_feature_class=out_fc,
        join_operation='JOIN_ONE_TO_ONE',
        match_option='INTERSECT'
    )

if __name__ == "__main__":
    buff_small_polygon_segments()
