import arcpy
from enum import Enum
from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from env_setup import environment_setup
from file_manager import WorkFileManager
from file_manager.n10.file_manager_facilities import Facility_N10
from input_data import input_innsjohoyde, input_n100

arcpy.env.overwriteOutput = True

# ========================
# Configurations
# ========================

class prog_config(Enum):
    #County ids
    area=[] 

    #Buffer for lakes below 5000 m^2. 'Number Unit'. 40 Meters is the minimum distance for label with 4 units to not intersect lake edge
    buffer_innsjo_below_5000_distance='40 Meters'

    #Buffer to mark invalid distance to edges of regulated lakes and lakes larger than 5000m^2
    innsjo_above_5000_line_buffer_distance='40 Meters'

    innsjo_above_5000_full_buffer=innsjo_above_5000_line_buffer_distance+1

    snapping_distance='40 Meters'


# ========================
# Program
# ========================

def main():

    environment_setup.main()

    # Sets up work file manager and creates temporarily files
    working_fc = Facility_N10.ledning__n10_facility.value
    config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=config)

    files = create_wfm_gdbs(wfm=wfm)
    fetch_data(files=files, area=prog_config.area)

# ========================
# Dictionary creation and
# Data fetching
# ========================

class fc(Enum):
    #Enum class for easier use of files dictionary. Prevents misspelling file variables

    #Fetch data
    innsjo_below_5000="innsjo_below_5000"
    innsjo_above_5000="innsjo_above_5000"
    annotations_pre_buffed="annotations_pre_buffed"

    #Invalid areas
    innsjo_below_5000_buffed="innsjo_below_5000_buffed"

    #Valid areas large
    areas_above_5000_line="areas_above_5000_line"
    areas_above_5000_line_buffer="areas_above_5000_line_buffer"
    areas_above_5000_full_buffer="areas_above_5000_full_buffer"
    areas_within_above_5000="areas_within_above_5000"
    just_areas_within_above_5000="just_areas_within_above_5000"
    valid_label_positions_large="valid_label_positions_large"
    
    #Valid areas small
    valid_label_positions_small="valid_label_positions_small"

    #Find points
    innsjo_above_5000_simplified="innsjo_above_5000_simplified"
    above_5000_simplified_inner="above_5000_simplified_inner"
    above_5000_simplified_centroid="above_5000_simplified_centroid"

    #Check if point inside lake and split points
    small_lakes="small_lakes"
    
    #Check if point inside lake
    above_5000_centroids="above_5000_centroids"
    
    #Split points
    large_lakes="large_lakes"

    #Snap points
    hoydeintervaller="hoydeintervaller"

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
    innsjo_below_5000=wfm.build_file_path(file_name="innsjo_below_5000", file_type="gdb")
    innsjo_above_5000=wfm.build_file_path(file_name="innsjo_above_5000", file_type="gdb")
    annotations_pre_buffed=wfm.build_file_path(file_name="annotations_pre_buffed", file_type="gdb")

    #Invalid areas
    innsjo_below_5000_buffed=annotations_pre_buffed=wfm.build_file_path(file_name="innsjo_below_5000_buffed", file_type="gdb")
    
    #Valid areas large
    areas_above_5000_line=wfm.build_file_path(file_name="areas_above_5000_line", file_type="gdb")
    areas_above_5000_line_buffer=wfm.build_file_path(file_name="areas_above_5000_line_buffer", file_type="gdb")
    areas_above_5000_full_buffer=wfm.build_file_path(file_name="areas_above_5000_full_buffer", file_type="gdb")
    areas_within_above_5000=wfm.build_file_path(file_name="areas_within_above_5000", file_type="gdb")
    just_areas_within_above_5000=wfm.build_file_path(file_name="just_areas_within_above_5000", file_type="gdb")
    valid_label_positions_large=wfm.build_file_path(file_name="valid_label_positions_large", file_type="gdb")
    
    #Valid areas small
    valid_label_positions_small=wfm.build_file_path(file_name="valid_label_positions_small", file_type="gdb")
    
    #Find points
    innsjo_above_5000_simplified=wfm.build_file_path(file_name="innsjo_above_5000_simplified", file_type="gdb")
    above_5000_simplified_inner=wfm.build_file_path(file_name="above_5000_simplified_inner", file_type="gdb")
    above_5000_simplified_centroid=wfm.build_file_path(file_name="innsjo_above_5000_simplified", file_type="gdb")

    #Check if point inside lake and split points
    small_lakes=wfm.build_file_path(file_name="small_lakes", file_type="gdb")

    #Check if point inside lake
    above_5000_centroids=wfm.build_file_path(file_name="above_5000_centroids", file_type="gdb")

    #Split points
    large_lakes=wfm.build_file_path(file_name="large_lakes", file_type="gdb")

    #Snap points
    hoydeintervaller=wfm.build_file_path(file_name="hoydeintervaller", file_type="gdb")

    return {
        #Fetch data
        fc.innsjo_below_5000: innsjo_below_5000,
        fc.innsjo_above_5000:innsjo_above_5000,
        fc.annotations_pre_buffed:annotations_pre_buffed,

        #Invalid areas
        fc.innsjo_below_5000_buffed:innsjo_below_5000_buffed,

        #Valid areas large
        fc.areas_above_5000_line:areas_above_5000_line,
        fc.areas_above_5000_line_buffer:areas_above_5000_line_buffer,
        fc.areas_above_5000_full_buffer:areas_above_5000_full_buffer,
        fc.areas_within_above_5000:areas_within_above_5000,
        fc.just_areas_within_above_5000:just_areas_within_above_5000,
        fc.valid_label_positions_large:valid_label_positions_large,

        #Valid areas small
        fc.valid_label_positions_small:valid_label_positions_small,

        #Find points
        fc.innsjo_above_5000_simplified:innsjo_above_5000_simplified,
        fc.above_5000_simplified_inner:above_5000_simplified_inner,
        fc.above_5000_simplified_centroid:above_5000_simplified_centroid,

        #Check if point inside lake and split points
        fc.small_lakes:small_lakes,

        #Check if point inside lake
        fc.above_5000_centroids:above_5000_centroids,

        #Split points
        fc.large_lakes:large_lakes,

        #Snap points
        fc.hoydeintervaller:hoydeintervaller

    }

@timing_decorator
def fetch_data(files: dict, area: list=None) -> None:
    """
    Fetches relevant data.

    Args:
        files (dict): Dictionary with all the working files
    """
    clip_lyr=None
    
    if area:
        clip_lyr="area_lyr"
        arcpy.management.MakeFeatureLayer(in_features=input_n100.AdminFlate, out_layer=clip_lyr)
        vals=",".join(f"{v}" for v in area)
        arcpy.management.SelectLayerByAttribute(clip_lyr, "NEW_SELECTION", f"KOMMUNENUMMER IN ({vals})")

    #Lakes
    innsjo_bearbeidet_lyr="innsjo_bearbeidet_lyr"
    arcpy.management.MakeFeatureLayer(in_features=input_innsjohoyde.hoyde_bearbeidet, out_layer=innsjo_bearbeidet_lyr)
    if area:arcpy.management.SelectLayerByLocation(in_layer=innsjo_bearbeidet_lyr, overlap_type='HAVE_THEIR_CENTER_IN', select_features=clip_lyr, search_distance=None, selection_type='NEW_SELECTION')
    
    selection='ADD_TO_SELECTION' if area else 'NEW_SELECTION'
    above_5000_sql="SHAPE_AREA>=5000 OR arealdekke='Ferskvann_innsjo_tjern_regulert'"

    #Lakes above 5000m^2 (needs labels)
    arcpy.management.SelectLayerByAttribute(in_layer_or_view=innsjo_bearbeidet_lyr, selection_type=selection, where_clause=above_5000_sql, invert_where_clause='NOT_INVERT')
    arcpy.management.CopyFeatures(in_features=innsjo_bearbeidet_lyr, out_feature_class=files[fc.innsjo_above_5000])
    arcpy.management.SelectLayerByAttribute(in_layer_or_view=innsjo_bearbeidet_lyr, selection_type='CLEAR_SELECTION')
    arcpy.management.RepairGeometry(in_features=files[fc.innsjo_above_5000], delete_null='DELETE_NULL')

    #Lakes below 5000m^2 (no labels)
    arcpy.management.SelectLayerByAttribute(in_layer_or_view=innsjo_bearbeidet_lyr, selection_type=selection, where_clause=above_5000_sql, invert_where_clause='INVERT')
    arcpy.management.CopyFeatures(in_features=innsjo_bearbeidet_lyr, out_feature_class=files[fc.innsjo_below_5000])

    #Annotations
    annotasjoner_bearbeidet_lyr="annotasjoner_bearbeidet_lyr"
    arcpy.management.MakeFeatureLayer(in_features=input_innsjohoyde.annotasjoner_bearbeidet, out_layer=annotasjoner_bearbeidet_lyr)
    if area: arcpy.management.SelectLayerByLocation(in_layer=annotasjoner_bearbeidet_lyr, overlap_type='HAVE_THEIR_CENTER_IN', select_features=clip_lyr, search_distance=None, selection_type='NEW_SELECTION')
    arcpy.management.CopyFeatures(in_features=annotasjoner_bearbeidet_lyr, out_feature_class=files[fc.annotations_pre_buffed])

# ========================
# Data manipulation?
# ======================== 

def label_text_creation(files:dict)->None:
    """
    Creates an additional field with the height and lrv combined for all lakes that are regulated and has an area equal to or larger than 5000.

    Args:
        files (dict): Dictionary with all the working files
    """

    field_name="hoyde_og_LRV"
    field_type='TEXT'

    arcpy.management.AddField(in_table=files[fc.innsjo_above_5000], field_name=field_name, field_type=field_type)
    with arcpy.da.UpdateCursor(in_table=files[fc.innsjo_above_5000], field_names=["hoyde", "LRV", field_type]) as update_cursor:
        for hoyde, lrv, label in update_cursor:
            if hoyde is not None and float(hoyde) > 0:
                if float(lrv)!=None and float(lrv)>0:
                    label=f"{hoyde}-{lrv}"
                else:
                    label=f"{hoyde}"    
                update_cursor.updateRow([hoyde, lrv, label])

def invalid_areas(files:dict)->None:
    """
    Creates a buffer for all non regulated lakes with area smaller than 5000m^2. 

    Args:
        files (dict): Dictionary with all the working files
    """

    innsjo_below_5000_layer="innsjo_below_5000_layer"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.innsjo_below_5000], out_layer=innsjo_below_5000_layer)

    arcpy.analysis.Buffer(
        in_features=innsjo_below_5000_layer, 
        out_feature_class=files[fc.innsjo_below_5000_buffed], 
        buffer_distance_or_field=prog_config.buffer_innsjo_below_5000_distance,
        line_side='FULL'
        )

def valid_areas_large_lakes(files:dict)->None:
    """
    Area with valid positions for all large lakes regulated or larger than 5000m^2.

    Args:
        files (dict): Dictionary with all the working files
    """

    arcpy.management.PolygonToLine(in_features=files[fc.innsjo_above_5000], out_feature_class=files[fc.areas_above_5000_line])
    
    areas_above_5000_line_lyr="areas_above_5000_line_lyr"    
    arcpy.management.MakeFeatureLayer(in_features=files[fc.areas_above_5000_line], out_layer=areas_above_5000_line_lyr)

    arcpy.analysis.Buffer(
        in_features=areas_above_5000_line_lyr, 
        out_feature_class=files[fc.areas_above_5000_line_buffer],
        buffer_distance_or_field=prog_config.innsjo_above_5000_line_buffer_distance,
        line_side='FULL'
        )
    
    innsjo_above_5000="innsjo_above_5000"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.innsjo_above_5000], out_layer=innsjo_above_5000)

    arcpy.analysis.Buffer(
        in_features=innsjo_above_5000,
        out_feature_class=files[fc.areas_above_5000_full_buffer],
        buffer_distance_or_field=prog_config.innsjo_above_5000_line_buffer_distance,
        line_side='FULL'
        )

    arcpy.analysis.Erase(
        in_features=files[fc.areas_above_5000_full_buffer],
        erase_features=files[fc.areas_above_5000_line_buffer],
        out_feature_class=files[fc.areas_within_above_5000]
        )
    
    arcpy.analysis.Erase(
        in_features=files[fc.areas_within_above_5000],
        erase_features=files[fc.innsjo_below_5000_buffed],
        out_feature_class=files[fc.just_areas_within_above_5000]
    )

    arcpy.analysis.Erase(
        in_features=files[fc.just_areas_within_below_5000],
        erase_features=files[fc.annotations_pre_buffed],
        out_feature_class=files[fc.valid_label_positions_large]
    )

def valid_areas_small_lakes(files:dict)->None:
    """
    Area with valid positions for all small lakes regulated or larger than 5000m^2.

    Args:
        files (dict): Dictionary with all the working files
    """

    arcpy.analysis.Erase(
        in_features=files[fc.just_areas_within_above_5000],
        erase_features=files[fc.innsjo_above_5000],
        out_feature_class=files[fc.valid_label_positions_small]
    )

def find_points(files:dict)->None:
    """
    Finding centroids and inner points for all lakes above 5000m^2 or regulated.

    Args:
        files (dict): Dictionary with all the working files
    """

    arcpy.cartography.SimplifyPolygon(
        in_features=files[fc.innsjo_above_5000],
        out_feature_class=files[fc.innsjo_above_5000_simplified],
        algorithm='EFFECTIVE_AREA',
        tolerance='20 Meters',
        error_option='RESOLVE_ERRORS'
    )

    try:
        arcpy.management.FeatureToPoint(in_features=files[fc.innsjo_above_5000_simplified], out_feature_class=files[fc.above_5000_simplified_inner], point_location='INSIDE')
        arcpy.management.FeatureToPoint(in_features=files[fc.innsjo_above_5000_simplified], out_feature_class=files[fc.above_5000_simplified_centroid], point_location='CENTROID')
    except Exception as e:
        raise
    
def check_if_point_inside_lake(files:dict)->None:
    """
    Checks if lake centroids found are inside their lake polygon. If not, it fixes it.

    Args:
        files (dict): Dictionary with all the working files
    """
    
    above_5000_lyr="simplified_above_5000_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.innsjo_above_5000], out_layer=above_5000_lyr)

    centroids="centroids"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.above_5000_simplified_centroid], out_layer=centroids)

    inside="innside"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.above_5000_simplified_inner], out_layer=inside)
    arcpy.management.AddField(in_table=inside, field_name="outside", field_type='SHORT')
    arcpy.management.SelectLayerByLocation(in_layer=inside, overlap_type='INTERSECT', select_features=above_5000_lyr, search_distance=None, selection_type='NEW_SELECTION', invert_spatial_relationship='INVERT')
    
    with arcpy.da.UpdateCursor(in_table=inside, field_names=["outside"]) as update_inside_cursor:
        for inner_point in update_inside_cursor:
            inner_point=1
            update_inside_cursor.updateRow(inner_point)

    arcpy.management.SelectLayerByLocation(in_layer=centroids, overlap_type='WITHIN', select_features=above_5000_lyr, search_distance=None, selection_type='NEW_SELECTION', invert_spatial_relationship='INVERT')

    innerpoints_outside_lakes=[]

    with arcpy.da.UpdateCursor(in_table=centroids, field_names=["OBJECTID","SHAPE@X", "SHAPE@Y"]) as update_cursor:
        for centroid_id, centroid_x, centroid_y in update_cursor:
            
            with arcpy.da.SearchCursor(in_table=inside, field_names=["OBJECTID", "outside","SHAPE@X", "SHAPE@Y"]) as search_cursor:
                for inner_id, outside, inner_x, inner_y in search_cursor:

                    if centroid_id==inner_id:
                        if outside==1:
                            innerpoints_outside_lakes.append(inner_id)

                        else:
                            centroid_x=inner_x
                            centroid_y=inner_y

                            update_cursor.updateRow([centroid_id, centroid_x, centroid_y])
    
    if innerpoints_outside_lakes:
        arcpy.management.SelectLayerByAttribute(in_layer_or_view=centroids, selection_type='NEW_SELECTION', where_clause=f"OBJECTID IN {tuple(innerpoints_outside_lakes)}")
        arcpy.management.Append(inputs=centroids, target=files[fc.small_lakes], schema_type='NO_TEST')
        arcpy.management.DeleteRows(in_rows=centroids)
        arcpy.management.SelectLayerByAttribute(in_layer_or_view=centroids,selection_type="CLEAR_SELECTION")

    arcpy.management.CopyFeatures(in_features=centroids, out_feature_class=files[fc.above_5000_centroids])

def split_punkter(files:dict)->None:
    """
    Seperates lakes into those that have valid areas (large lakes) and those who do not (small lakes).

    Args:
        files (dict): Dictionary with all the working files
    """
    valid_areas_large_lakes_lyr="valid_areas_large_lakes_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.valid_label_positions_large], out_layer=valid_areas_large_lakes_lyr)

    centroids_lyr="centroids_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.above_5000_centroids], out_layer=centroids_lyr)

    innsjo_above_5000_lyr="innsjo_above_5000_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.innsjo_above_5000], out_layer=innsjo_above_5000_lyr)

    arcpy.management.SelectLayerByLocation(in_layer=innsjo_above_5000_lyr, overlap_type='INTERSECT', select_features=valid_areas_large_lakes_lyr, search_distance=None, selection_type='NEW_SELECTION', invert_spatial_relationship='INVERT')
    arcpy.management.SelectLayerByLocation(in_layer=centroids_lyr, overlap_type='INTERSECT', select_features=innsjo_above_5000_lyr, search_distance=None, selection_type='NEW_SELECTION')
    arcpy.management.Append(inputs=centroids_lyr, target=files[fc.small_lakes])
    arcpy.management.DeleteRows(in_rows=centroids_lyr)
    arcpy.management.SelectLayerByAttribute(in_layer_or_view=centroids_lyr,selection_type="CLEAR_SELECTION")
    arcpy.management.CopyFeatures(in_features=centroids_lyr, out_feature_class=files[fc.large_lakes])

def snap_points(files:dict)->None:

    large_lakes_lyr="large_lakes_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.large_lakes], out_layer=large_lakes_lyr)

    valid_area_large_lakes_lyr="valid_area_large_lakes_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.valid_label_positions_large], out_layer=valid_area_large_lakes_lyr)

    arcpy.management.SelectLayerByLocation(in_layer=large_lakes_lyr, overlap_type='INTERSECT', select_features=valid_area_large_lakes_lyr, search_distance=None, selection_type='NEW_SELECTION', invert_spatial_relationship='INVERT')
    arcpy.edit.Snap(
        in_features=large_lakes_lyr,
        snap_environment=[
            [valid_area_large_lakes_lyr, "EDGE", prog_config.snapping_distance]
        ]
    )
    arcpy.management.SelectLayerByAttribute(in_layer_or_view=large_lakes_lyr,selection_type="CLEAR_SELECTION")


    small_lakes_lyr="small_lakes_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.small_lakes], out_layer=small_lakes_lyr)

    valid_area_small_lakes_lyr="valid_area_small_lakes_lyr"
    arcpy.management.MakeFeatureLayer(in_features=files[fc.valid_label_positions_small], out_layer=valid_area_small_lakes_lyr)
    arcpy.edit.Snap(
        in_features=small_lakes_lyr,
        snap_environment=[
            [valid_area_small_lakes_lyr, "EDGE", prog_config.snapping_distance]
        ]
    )

    arcpy.management.Merge(inputs=[small_lakes_lyr, large_lakes_lyr], output=files[fc.hoydeintervaller])


if __name__ == "__main__":
    main()
