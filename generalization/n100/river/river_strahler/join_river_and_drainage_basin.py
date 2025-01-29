"""
This script joins river and drainage basin data, selecting rivers within a specified basin and saving the results to a new shapefile.
"""
import arcpy
import geopandas as gpd
import config

gdb_path = config.n50_path
shp_path = config.drainage_basin_path

arcpy.env.workspace = gdb_path

rivers_fc = "ElvBekk"
basins_fc = shp_path

output_fc = config.output_folder + r"\river_basin_combined"

# Create a feature layer from rivers and drainage basins
arcpy.MakeFeatureLayer_management(rivers_fc, "rivers_layer")
arcpy.MakeFeatureLayer_management(basins_fc, "basins_layer")

# You can change this to any drainage basin
specified_basin_query = "nedborfelt = 'HOMLA'"
arcpy.SelectLayerByAttribute_management(
    "basins_layer", "NEW_SELECTION", specified_basin_query
)

arcpy.SelectLayerByLocation_management("rivers_layer", "INTERSECT", "basins_layer")
arcpy.CopyFeatures_management("rivers_layer", output_fc)
