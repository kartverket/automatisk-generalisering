# Importing custom files relative to the root path
import config

# Importing general packages
import arcpy

project_spatial_reference = 25833


def general_setup():
    """Set up the ArcGIS Pro environment.

    Parameters:
    - workspace (str): The workspace path. Defaults to what's set in the config.
    - Spatial Reference EPSG 3045 = ETRS89 / UTM zone 33N
    """

    arcpy.env.overwriteOutput = True
    arcpy.env.workspace = config.default_project_workspace
    arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(project_spatial_reference)
    arcpy.env.parallelProcessingFactor = config.cpu_percentage

    print(
        f"Workspace environment set up with workspace: {config.default_project_workspace}"
    )


if __name__ == "__main__":
    general_setup()
