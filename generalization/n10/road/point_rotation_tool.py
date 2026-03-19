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
Expect that the points have been snapped to the correct lines beforehand.
'''

def main(in_features_point, in_features_line, out_feature_class):

    environment_setup.main()

    # Sets up work file manager and creates temporarily files
    working_fc = Road_N10.data_selection__roadblock__n10_road.value
    config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=config)

    files = create_wfm_gdbs(wfm=wfm)
    insert_into_dict(files=files, in_features=in_features)

    establish_target_area(files=files)
    calculate_road_bearing(files=files)

class fc(Enum):
    input_point="input_point"

    target_area="target_area"
    target_lines_adjusted="target_lines_adjusted"
    target_lines_adjusted_single="target_lines_adjusted_single"
    target_lines_fully_adjusted="target_lines_fully_adjusted"

    target_roads_w_bearing="target_roads_w_bearing"

@timing_decorator
def create_wfm_gdbs(wfm: WorkFileManager) -> dict:
    #Creates dictionary for easier file handling

    input_point=wfm.build_file_path(file_name="input_point", file_type="gdb")
    input_line=wfm.build_file_path(file_name="input_line", file_type="gdb")

    target_area=wfm.build_file_path(file_name="target_area", file_type="gdb")
    target_lines_adjusted=wfm.build_file_path(file_name="target_lines_adjusted", file_type="gdb")
    target_lines_adjusted_single=wfm.build_file_path(file_name="target_lines_adjusted_single", file_type="gdb")
    target_lines_fully_adjusted=wfm.build_file_path(file_name="target_lines_fully_adjusted", file_type="gdb")

    target_roads_w_bearing=wfm.build_file_path(file_name="target_roads_w_bearing", file_type="gdb")

    return {
        #insert into dict
        fc.input_point:input_point,

        #Establish target area
        fc.target_area:target_area,
        fc.target_lines_adjusted:target_lines_adjusted,
        fc.target_lines_adjusted_single:target_lines_adjusted_single,
        fc.target_lines_fully_adjusted:target_lines_fully_adjusted,

        #Calculate road bearing
        fc.target_roads_w_bearing:target_roads_w_bearing
    }

@timing_decorator
def insert_into_dict(files: dict, in_features_point, in_features_line)->None:
    arcpy.management.Copy(in_data=in_feature_point, out_data=files[fc.input_point])
    arcpy.management.Copy(in_data=input_lines_line, out_data=files[fc.input_line])

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
    target_roads_fully_adjusted_lyr="target_roads_fully_adjusted_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.target_roads_fully_adjusted], out_layer=target_roads_fully_adjusted_lyr)

    arcpy.management.CalculateGeometryAttributes(in_features=target_roads_fully_adjusted_lyr, geometry_property=[["LINE_BEARING", "LINE_BEARING"]])

    arcpy.management.CopyFeatures(in_features=target_roads_fully_adjusted_lyr, out_feature_class=files[fc.target_roads_w_bearing])

@timing_decorator
def rotate_roadblocks(files:dict)->None:

    #Add a field to the fc for the road segment id and the roadblock rotation
    roadblocks_preprocessed_lyr="roadblocks_preprocessed_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.roadblocks_preprocessed], out_layer=roadblocks_preprocessed_lyr)

    arcpy.management.AddField(roadblocks_preprocessed_lyr, "vei_objekt_id", "DOUBLE")
    arcpy.management.AddField(roadblocks_preprocessed_lyr, "rotasjon", "DOUBLE")

    #Iterate through the roadblocks to add the road segment id
    with arcpy.da.UpdateCursor(roadblocks_preprocessed_lyr, ["OBJECTID", "veiobjektid"]) as cursor_original_roadblock:
        for roadblock in cursor_original_roadblock:

            with arcpy.da.SearchCursor(intersections_road_n_roadblock, ["TARGET_FID", "JOIN_FID"]) as cursor_intersections_road_n_roadblock:
                for intersection_road_n_roadblock in cursor_intersections_road_n_roadblock:
                    if roadblock[0]==intersection_road_n_roadblock[0]:
                        roadblock[1]=intersection_road_n_roadblock[1]
                        cursor_original_roadblock.updateRow(roadblock)
                        break

if __name__=="__main__":
    main()