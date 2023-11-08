# Importing custom files relative to the root path
import config
# Importing general packages
import arcpy


def general_setup():
    """Set up the ArcGIS Pro environment.

    Parameters:
    - workspace (str): The workspace path. Defaults to what's set in the config.
    - Spatial Reference EPSG 3045 = ETRS89 / UTM zone 33N
    """

    arcpy.env.overwriteOutput = True
    arcpy.env.workspace = config.default_project_workspace
    arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(3045)
    arcpy.env.parallelProcessingFactor = config.cpu_percentage

    print(f"Workspace environment set up with workspace: {config.default_project_workspace}")


def resolve_building_conflicts_setup():
    pass
