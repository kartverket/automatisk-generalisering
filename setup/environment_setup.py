# Makes sure the path is relative to the root path
from rootpath import detect
import sys

root_path = detect()
sys.path.append(root_path)

# Importing custom files relative to the root path
import config

# Importing general packages
import arcpy


def setup(workspace=config.n100_building_workspace):
    """Set up the ArcGIS Pro environment.

    Parameters:
    - workspace (str): The workspace path. Defaults to what's set in the config.
    """

    arcpy.env.overwriteOutput = True
    arcpy.env.workspace = workspace
    arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(3045)

    print(f"Workspace environment set up with workspace: {workspace}")
