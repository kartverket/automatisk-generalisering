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

def main():

    environment_setup.main()

    # Sets up work file manager and creates temporarily files
    working_fc = Road_N10.data_selection__roadblock__n10_road.value
    config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=config)

    files = create_wfm_gdbs(wfm=wfm)
    fetch_data(files=files)

    road_preprocessing(files=files)
    establish_target_area(files=files)
    calculate_road_bearing(files=files)

class fc(Enum):
    target_roads="target_roads"
    additional_roads="additional_roads"
    non_processed_roadblocks="non_processed_roadblocks"

    non_overlapping_roads="non_overlapping_roads"
    target_additional_combined="target_additional_combined"
    roadblocks_preprocessed="roadblocks_preprocessed"

    target_area="target_area"
    target_roads_adjusted="target_roads_adjusted"
    target_roads_adjusted_single="target_roads_adjusted_single"
    target_roads_fully_adjusted="target_roads_fully_adjusted"

    target_roads_w_bearing="target_roads_w_bearing"

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
    target_roads=wfm.build_file_path(file_name="target_roads", file_type="gdb")
    additional_roads=wfm.build_file_path(file_name="additional_roads", file_type="gdb")
    non_processed_roadblocks=wfm.build_file_path(file_name="non_processed_roadblocks", file_type="gdb")

    non_overlapping_roads=wfm.build_file_path(file_name="non_overlapping_roads", file_type="gdb")
    target_additional_combined=wfm.build_file_path(file_name="target_additional_combined", file_type="gdb")
    roadblocks_preprocessed=wfm.build_file_path(file_name="roadblocks_preprocessed", file_type="gdb")

    target_area=wfm.build_file_path(file_name="target_area", file_type="gdb")
    target_roads_adjusted=wfm.build_file_path(file_name="target_roads_adjusted", file_type="gdb")
    target_roads_adjusted_single=wfm.build_file_path(file_name="target_roads_adjusted_single", file_type="gdb")
    target_roads_fully_adjusted=wfm.build_file_path(file_name="target_roads_fully_adjusted", file_type="gdb")

    target_roads_w_bearing=wfm.build_file_path(file_name="target_roads_w_bearing", file_type="gdb")

    return {
        #Fetch data
        fc.target_roads:target_roads,
        fc.additional_roads:additional_roads,
        fc.non_processed_roadblocks:non_processed_roadblocks,

        #road preprocessing
        fc.non_overlapping_roads:non_overlapping_roads,
        fc.target_additional_combined:target_additional_combined,
        fc.roadblocks_preprocessed:roadblocks_preprocessed,

        #Establish target area
        fc.target_area:target_area,
        fc.target_roads_adjusted:target_roads_adjusted,
        fc.target_roads_adjusted_single:target_roads_adjusted_single,
        fc.target_roads_fully_adjusted:target_roads_fully_adjusted,

        #Calculate road bearing
        fc.target_roads_w_bearing:target_roads_w_bearing
    }

@timing_decorator
def fetch_data(files: dict)->None:
    pass

@timing_decorator
def road_preprocessing(files:dict)->None:

    #Remove original roads from the additional roads to avoid overlapping polygons
    additional_roads_lyr="additional_roads_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.additional_roads], out_layer=additional_roads_lyr)
    target_roads_lyr="target_roads_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.target_roads])

    arcpy.analysis.Erase(in_features=additional_roads_lyr, erase_features=target_roads_lyr, out_feature_class=files[fc.non_overlapping_roads])
    
    #Combine additional roads, pavements and paths with original roads.
    arcpy.management.Merge(inputs=[files[fc.non_overlapping_roads], files[fc.target_roads]], output=files[fc.target_additional_combined])

    #Delete all roadblocks that intersect with wrong "roads"
    target_additional_combined_lyr="target_additional_combined_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.target_additional_combined], out_layer=target_additional_combined_lyr)

    non_processed_roadblocks_lyr="non_processed_roadblocks_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.non_processed_roadblocks], out_layer=non_processed_roadblocks_lyr)

    arcpy.edit.Snap(in_features=non_processed_roadblocks_lyr, snap_environment=[target_additional_combined_lyr, 'EDGE', '0.05'])

    non_overlapping_roads_lyr="non_overlapping_roads_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.non_overlapping_roads], out_layer=non_overlapping_roads_lyr)

    arcpy.management.SelectLayerByLocation(
        in_layer=non_processed_roadblocks_lyr, 
        overlap_type='INTERSECT', 
        select_features=non_overlapping_roads_lyr,
        selection_type='NEW_SELECTION'
        )
    
    with arcpy.da.UpdateCursor(in_table=non_processed_roadblocks_lyr, field_names=["OBJECT_ID"]) as delete_cursor:
        for roadblock in delete_cursor:
            delete_cursor.deleteRow(roadblock)

    arcpy.management.SelectLayerByAttribute(in_layer_or_view=non_overlapping_roads_lyr, selection_type='CLEAR_SELECTION')
    arcpy.management.CopyFeatures(in_features=non_overlapping_roads_lyr, out_feature_class=files[fc.roadblocks_preprocessed])

@timing_decorator
def establish_target_area(files:dict)->None:
    
    #Create a buffer layer around each roadblock. Radius must be small due to intersecting roads.
    roadblocks_preprocessed_lyr="roadblocks_preprocessed_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.roadblocks_preprocessed], out_layer=roadblocks_preprocessed_lyr)

    arcpy.analysis.PairwiseBuffer(
        in_features=roadblocks_preprocessed_lyr,
        out_feature_class=files[fc.target_area],
        buffer_distance_or_field='1 Meters'
    )

    #Select the roads where the roadblocks intersect, since there can be multiple roads within the buffer that the roadblock is not on.
    target_roads_lyr="target_roads_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.target_roads], out_layer=target_roads_lyr)

    arcpy.management.SelectLayerByLocation(in_layer=target_roads_lyr, overlap_type='INTERSECT', select_features=roadblocks_preprocessed_lyr, selection_type='NEW_SELECTION')

    #Clip the selected roads to the target area
    target_area_lyr="target_area_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.target_area], out_layer=target_area_lyr)

    arcpy.analysis.Clip(in_features=target_roads_lyr, clip_features=target_area_lyr, out_feature_class=files[fc.target_roads_adjusted])

    #Make sure the clipped roads are treated seperately
    target_roads_adjusted_lyr="target_roads_adjusted_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.target_roads_adjusted], out_layer=target_roads_adjusted_lyr)

    arcpy.management.MultipartToSinglepart(in_features=target_roads_adjusted_lyr, out_feature_class=files[fc.target_roads_adjusted_single])

    #Save the original road id to the new road segments (this is located in the road blocks)
    target_roads_adjusted_single_lyr="target_roads_adjusted_single_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.target_roads_adjusted_single], out_layer=target_roads_adjusted_single_lyr)

    arcpy.analysis.SpatialJoin(
        target_features=target_roads_adjusted_single_lyr,
        join_features=roadblocks_preprocessed_lyr,
        out_feature_class=files[fc.target_roads_fully_adjusted],
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