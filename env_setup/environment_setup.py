# Importing custom files relative to the root path
import config
# Importing general packages
import arcpy


def setup(workspace=config.n100_building_workspace):
    """Set up the ArcGIS Pro environment.

    Parameters:
    - workspace (str): The workspace path. Defaults to what's set in the config.
    - Spatial Reference EPSG 3045 = ETRS89 / UTM zone 33N
    """

    arcpy.env.overwriteOutput = True
    arcpy.env.workspace = workspace
    arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(3045)

    print(f"Workspace environment set up with workspace: {workspace}")
