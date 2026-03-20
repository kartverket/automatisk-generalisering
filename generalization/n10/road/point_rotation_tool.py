#Imports
import arcpy
from math import degrees, atan2
from enum import Enum
from custom_tools.decorators.timing_decorator import timing_decorator

from composition_configs import core_config
from env_setup import environment_setup
from file_manager import WorkFileManager
from file_manager.n10.file_manager_roads import Road_N10
from input_data import input_roads

arcpy.env.overwriteOutput = True

'''
This function finds the rotation of a collection of points based on the angle of nearby lines.
It is expected that the points have been snapped to the correct lines on beforehand.

in_features_point -> feature class of points to be rotated
in_features_line -> feature class of lines the rotation will be based on
out_feature_class -> feature class the processed points will be saved to
'''

def tool(in_features_point, in_features_line, out_feature_class, rotation_difference:int):

    environment_setup.main()

    # Sets up work file manager and creates temporarily files
    working_fc = Road_N10.data_selection__roadblock__n10_road.value
    config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=config)

    files = create_wfm_gdbs(wfm=wfm)
    
    insert_into_dict(
        files=files, 
        in_features_point=in_features_point,
        in_features_line=in_features_line
        )

    establish_target_area(files=files)
    calculate_road_bearing(files=files)
    rotate_roadblocks(files=files, out_feature_class=out_feature_class, rotation_difference=rotation_difference)

class fc(Enum):
    input_point="input_point"
    input_line="input_line"

    target_area="target_area"
    target_lines_adjusted="target_lines_adjusted"
    target_lines_adjusted_single="target_lines_adjusted_single"
    target_lines_fully_adjusted="target_lines_fully_adjusted"

    target_lines_w_bearing="target_lines_w_bearing"

@timing_decorator
def create_wfm_gdbs(wfm: WorkFileManager) -> dict:
    
    #Creates dictionary for easier file handling
    input_point=wfm.build_file_path(file_name="input_point", file_type="gdb")
    input_line=wfm.build_file_path(file_name="input_line", file_type="gdb")

    target_area=wfm.build_file_path(file_name="target_area", file_type="gdb")
    target_lines_adjusted=wfm.build_file_path(file_name="target_lines_adjusted", file_type="gdb")
    target_lines_adjusted_single=wfm.build_file_path(file_name="target_lines_adjusted_single", file_type="gdb")
    target_lines_fully_adjusted=wfm.build_file_path(file_name="target_lines_fully_adjusted", file_type="gdb")

    target_lines_w_bearing=wfm.build_file_path(file_name="target_lines_w_bearing", file_type="gdb")

    return {
        #insert into dict
        fc.input_point:input_point,
        fc.input_line:input_line,

        #Establish target area
        fc.target_area:target_area,
        fc.target_lines_adjusted:target_lines_adjusted,
        fc.target_lines_adjusted_single:target_lines_adjusted_single,
        fc.target_lines_fully_adjusted:target_lines_fully_adjusted,

        #Calculate road bearing
        fc.target_lines_w_bearing:target_lines_w_bearing
    }

@timing_decorator
def insert_into_dict(files: dict, in_features_point, in_features_line)->None:

    #Insert the input variables into the file manager dictionary
    arcpy.management.Copy(in_data=in_features_point, out_data=files[fc.input_point])
    arcpy.management.Copy(in_data=in_features_line, out_data=files[fc.input_line])

@timing_decorator
def establish_target_area(files:dict)->None:

    #Create a buffer layer around each roadblock. Radius must be small due to intersecting roads.
    input_point_lyr="input_point_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.input_point], out_layer=input_point_lyr)

    input_line_lyr="input_lines_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.input_line], out_layer=input_line_lyr)

    arcpy.analysis.PairwiseBuffer(
        in_features=input_point_lyr,
        out_feature_class=files[fc.target_area],
        buffer_distance_or_field='1 Meters'
    )

    #Select the lines where the points intersect to avoid clipping unimportant lines to the target area.
    arcpy.management.SelectLayerByLocation(
        in_layer=input_line_lyr, 
        overlap_type='INTERSECT',
        select_features=input_point_lyr,
        selection_type='NEW_SELECTION'
        )

    #Clip the selected lines to the target area
    target_area_lyr="target_area_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.target_area], out_layer=target_area_lyr)

    arcpy.analysis.Clip(in_features=input_line_lyr, clip_features=target_area_lyr, out_feature_class=files[fc.target_lines_adjusted])

    #Make sure the clipped roads are treated seperately
    target_lines_adjusted_lyr="target_lines_adjusted_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.target_lines_adjusted], out_layer=target_lines_adjusted_lyr)

    arcpy.management.MultipartToSinglepart(in_features=target_lines_adjusted_lyr, out_feature_class=files[fc.target_lines_adjusted_single])

    #Save the original line id to the new line segments (this will be used to rotate the points later!)
    target_lines_adjusted_single_lyr="target_lines_adjusted_single_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.target_lines_adjusted_single], out_layer=target_lines_adjusted_single_lyr)

    arcpy.analysis.SpatialJoin(
        target_features=target_lines_adjusted_single_lyr,
        join_features=input_point_lyr,
        out_feature_class=files[fc.target_lines_fully_adjusted],
        join_operation='JOIN_ONE_TO_MANY',
        match_option='WITHIN_A_DISTANCE',
        search_radius='1 Meters'
    )

@timing_decorator
def calculate_road_bearing(files:dict)->None:
    
    #Find the bearing for each road segment
    target_lines_fully_adjusted_lyr="target_lines_fully_adjusted_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.target_lines_fully_adjusted], out_layer=target_lines_fully_adjusted_lyr)

    arcpy.management.AddField(target_lines_fully_adjusted_lyr, field_name="LINE_BEARING")
    arcpy.management.CalculateGeometryAttributes(in_features=target_lines_fully_adjusted_lyr, geometry_property=[["LINE_BEARING", "LINE_BEARING"]])

    arcpy.management.CopyFeatures(in_features=target_lines_fully_adjusted_lyr, out_feature_class=files[fc.target_lines_w_bearing])

@timing_decorator
def rotate_roadblocks(files:dict, out_feature_class, rotation_difference)->None:

    #Add a field to the fc for the road segment id and the roadblock rotation
    input_point_lyr="input_point_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.input_point], out_layer=input_point_lyr)

    arcpy.management.AddField(input_point_lyr, "rotasjon", "DOUBLE")

    target_lines_w_bearing_lyr="target_lines_w_bearing_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.target_lines_w_bearing], out_layer=target_lines_w_bearing_lyr)

    #Iterate through the roadblocks to add the road segment id
    with arcpy.da.UpdateCursor(input_point_lyr, ["OBJECTID", "rotasjon"]) as cursor_roadblock:
        for roadblock in cursor_roadblock:

            with arcpy.da.SearchCursor(target_lines_w_bearing_lyr, ["JOIN_FID", "LINE_BEARING"]) as cursor_intersections_road_n_roadblock:
                for intersection_road_n_roadblock in cursor_intersections_road_n_roadblock:
                    if roadblock[0]==intersection_road_n_roadblock[0]:
                        roadblock[1]=intersection_road_n_roadblock[1]+rotation_difference
                        cursor_roadblock.updateRow(roadblock)
                        break

    arcpy.management.CopyFeatures(in_features=input_point_lyr, out_feature_class=out_feature_class)

if __name__=="__main__":
    tool()