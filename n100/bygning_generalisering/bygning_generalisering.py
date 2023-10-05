import sys
import arcpy
sys.path.append("..")
import config
import custom_arcpy


# Setting up workspace environment
arcpy.env.overwriteOutput = True
arcpy.env.workspace = config.bygning_workspace
arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(3045)
print("Workspace environment set up.")

# Importing the input features
input_n50_grunriss = config.input_n50_grunriss
input_n50_bygningspunkt = config.input_n50_bygningspunkt
input_n50_arealdekke_flate = config.input_n50_arealdekke_flate
input_matrikkel_punkt = config.input_matrikkel_punkt
input_n100_arealdekke_flate = config.input_n100_arealdekke_flate
input_n100_veg_sti = config.input_n100_veg_sti
input_n100_begrensingskurve = config.input_n100_begrensingskurve
print("Input features imported.")

# Selecting water features to use as barriers and creating a temporary layer feature
water_expr = "OBJTYPE = 'ElvBekkKant' Or OBJTYPE = 'Innsjøkant' Or OBJTYPE = 'InnsjøkantRegulert' Or OBJTYPE = 'Kystkontur'"
custom_arcpy.attribute_select_and_make_feature_layer(
    input_n100_begrensingskurve, water_expr, "n100_begrensingskurve_waterfeatures"
)

custom_arcpy.attribute_select_and_make_permanent_feature(
    input_n100_begrensingskurve,
    water_expr,
    "n100_begrensingskurve_waterfeatures_copy2",
)
n100_begrensingskurve_waterfeatures = "n100_begrensingskurve_waterfeatures_copy2"


