import arcpy
import os
import config

raster_folder = config.raster_path_folder
combined_raster_output = config.output_folder + r"\combined_raster.tif"

arcpy.env.overwriteOutput = True

tif_files = [os.path.join(raster_folder, f) for f in os.listdir(raster_folder) if f.endswith('.tif')]

if not tif_files:
    raise FileNotFoundError(f"No .tif files found in the folder {raster_folder}")

# Combine all .tif files into a single raster
try:
    arcpy.management.MosaicToNewRaster(tif_files, os.path.dirname(combined_raster_output), os.path.basename(combined_raster_output),
                                      number_of_bands=1, pixel_type="32_BIT_FLOAT", cellsize="", mosaic_method="FIRST")
    print(f"Combined raster created: {combined_raster_output}")
except arcpy.ExecuteError as e:
    print(f"Failed to execute MosaicToNewRaster: {e}")
    raise