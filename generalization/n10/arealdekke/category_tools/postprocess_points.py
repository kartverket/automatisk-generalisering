# Libraries

import arcpy

arcpy.env.overwriteOutput = True

from enum import StrEnum

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10
from generalization.n100.land_use.rullebane import cluster_points

# ========================
# Class
# ========================


class Names(StrEnum):
    buffer = "buffer"


# ========================
# Main function
# ========================


@timing_decorator
def postprocess_points(land_use_fc: str) -> None:
    """
    Postprocessing of points:
        - Remove points by clustering
        - Remove points not located in areas of interest

    Args:
        land_use_fc (str): Land use feature class to use for filtering points
    """
    point_fc = Arealdekke_N10.poly_to_point_points__n10_land_use.value

    working_fc = Arealdekke_N10.poly_to_point__n10_land_use.value
    config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=config)

    files = {
        name: wfm.build_file_path(file_name=name, file_type="gdb") for name in Names
    }

    remove_points_not_in_areas_of_interest(
        point_fc=point_fc, land_use_fc=land_use_fc, files=files
    )
    remove_clustered_points(point_fc=point_fc)

    wfm.delete_created_files()


# ========================
# Helper functions
# ========================


def remove_points_not_in_areas_of_interest(
    point_fc: str, land_use_fc: str, files: dict
) -> None:
    """
    Remove points not located in areas of interest.

    Args:
        point_fc (str): Feature class containing points to be filtered
        land_use_fc (str): Feature class containing land use areas
        files (dict): Dictionary containing temporary files
    """
    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(in_features=land_use_fc, out_layer=land_use_lyr)
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr,
        selection_type="NEW_SELECTION",
        where_clause="arealdekke = 'Jordbruk'",
    )

    arcpy.analysis.Buffer(
        in_features=land_use_lyr,
        out_feature_class=files[Names.buffer],
        buffer_distance_or_field="-8 Meters",
    )

    point_lyr = "point_lyr"
    arcpy.management.MakeFeatureLayer(in_features=point_fc, out_layer=point_lyr)
    arcpy.management.SelectLayerByLocation(
        in_layer=point_lyr,
        overlap_type="INTERSECT",
        select_features=files[Names.buffer],
        selection_type="NEW_SELECTION",
        invert_spatial_relationship="INVERT",
    )

    arcpy.management.DeleteFeatures(in_features=point_lyr)

    for lyr in [point_lyr, land_use_lyr]:
        arcpy.management.Delete(lyr)


def remove_clustered_points(point_fc: str) -> None:
    """
    Removes too dense clusters of points by grouping points together with DBSCAN
    calculate the centroid of each cluster and keep only the centroid point.

    Args:
        point_fc (str): Feature class containing points to be filtered
        files (dict): Dictionary containing temporary files
    """
    points = {
        oid: (geom.centroid.X, geom.centroid.Y)
        for oid, geom in arcpy.da.SearchCursor(point_fc, ["OID@", "SHAPE@"])
    }

    clusters = cluster_points(points=points, eps=10, min_pts=2)

    if len(clusters) == 0:
        print("No clusters found. No points will be removed.")
        return

    new_points = {}
    all_clustered_oids = {oid for cluster in clusters for oid in cluster}

    for cluster in clusters:
        clustered_points = [points[oid] for oid in cluster]
        avg_x = sum(x for x, _ in clustered_points) / len(clustered_points)
        avg_y = sum(y for _, y in clustered_points) / len(clustered_points)

        new_points[cluster[0]] = arcpy.Point(X=avg_x, Y=avg_y)

    point_lyr = "point_lyr"
    arcpy.management.MakeFeatureLayer(in_features=point_fc, out_layer=point_lyr)
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=point_lyr,
        selection_type="NEW_SELECTION",
        where_clause=f"OBJECTID IN ({','.join(map(str, all_clustered_oids))})",
    )

    with arcpy.da.UpdateCursor(point_lyr, ["OID@", "SHAPE@"]) as cursor:
        for oid, _ in cursor:
            if oid in new_points:
                cursor.updateRow([oid, new_points[oid]])
            else:
                cursor.deleteRow()
