# Importing packages
import arcpy

from collections import defaultdict

arcpy.env.overwriteOutput = True

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from file_manager import WorkFileManager
from file_manager.n100.file_manager_roads import Road_N100

from custom_tools.generalization_tools.road.remove_road_triangles import endpoints_of, sort_prioritized_hierarchy

# File overview
input_fc = Road_N100.data_preparation___resolve_road_conflicts___n100_road.value
working_fc = Road_N100.parallel_roads__n100_road.value

@timing_decorator
def generalize_parallel_roads() -> None:
    """
    Generalizes the road data by removing or adjusting parallel roads.
    """
    # Create WorkFileManager
    config = core_config.WorkFileConfig(
        root_file=working_fc
    )
    wfm = WorkFileManager(config=config)

    # Collect the original geometries for final match when storing the data
    original_geometries = fetch_original_data(input_fc=input_fc)

    # Dissolve the road instances
    dissolved_fc = wfm.build_file_path(
        file_name="dissolved_roads",
        file_type='gdb',
    )
    dissolve_road_features(input_fc=input_fc, dissolved_fc=dissolved_fc)
    clean_small_instances(dissolved_fc=dissolved_fc)

##################
# Help functions
##################



##################
# Main functions
##################

@timing_decorator
def fetch_original_data(input_fc: str) -> dict:
    """
    Creates a dictionary that contains the original geometries.

    Args:
        input_fc (str): Path to the featureclass containing the original data
    
    Returns:
        dict: Dictionary where key is oid and value original geometry
    """
    oid_to_geom = {}
    with arcpy.da.SearchCursor(input_fc, ["OID@", "SHAPE@", "vegkategori", "vegklasse", "Shape_Length"]) as search_cursor:
        for oid, geom, vegkategori, vegklasse, length in search_cursor:
            if geom is None:
                continue
            oid_to_geom[oid] = [vegkategori, vegklasse, length, geom]
    return oid_to_geom

@timing_decorator
def dissolve_road_features(input_fc: str, dissolved_fc: str):
    arcpy.management.Dissolve(
        in_features=input_fc,
        out_feature_class=dissolved_fc,
        dissolve_field=["medium"],
        multi_part="SINGLE_PART"
    )

if __name__ == "__main__":
    generalize_parallel_roads()

@timing_decorator
def clean_small_instances(dissolved_fc: str):
    """
    """
    # Create feature layer for selection
    short_roads = r"short_roads_lyr"
    arcpy.management.MakeFeatureLayer(dissolved_fc, short_roads, "Shape_Length < 100")
    relevant_roads = r"relevant_roads_lyr"
    arcpy.management.MakeFeatureLayer(dissolved_fc, relevant_roads)
    arcpy.management.SelectLayerByLocation(
        in_layer=relevant_roads,
        overlap_type="INTERSECT",
        select_features=short_roads,
        selection_type="NEW_SELECTION",
    )

    # Finds all short roads connected to junctions in every end
    endpoint_collection = {}
    with arcpy.da.SearchCursor(relevant_roads, ["OID@", "SHAPE@"]) as search_cursor:
        for oid, geom in search_cursor:
            s, e = endpoints_of(geom)
            for pnt in [s, e]:
                if pnt not in endpoint_collection:
                    endpoint_collection[pnt] = [oid]
                else:
                    endpoint_collection[pnt].append(oid)
    
    for key in endpoint_collection:
        endpoint_collection[key].append(len(endpoint_collection[key]))
    
    remove_pnts = set()
    with arcpy.da.UpdateCursor(short_roads, ["SHAPE@"]) as update_cursor:
        for row in update_cursor:
            s, e = endpoints_of(row[0], num=None)
            control = 0
            for pnt in [s, e]:
                if pnt in endpoint_collection:
                    if endpoint_collection[pnt][-1] > 2:
                        control += 1
            if control == 2:
                remove_pnts.add(s)
                remove_pnts.add(e)
                update_cursor.deleteRow()