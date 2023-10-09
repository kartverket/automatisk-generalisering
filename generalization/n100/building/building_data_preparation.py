# Importing custom files relative to the root path
from custom_tools import custom_arcpy
import config
from setup import environment_setup
from input_data import input_n50
from input_data import input_n100

# Importing general packages
import arcpy

# Importing environment
environment_setup.setup(workspace=config.n100_building_workspace)


# Defining the SQL selection expression for water features for begrensningskurve, then using that selection to create a temporary feature layer
sql_expr_begrensningskurve_waterfeatures = "OBJTYPE = 'ElvBekkKant' Or OBJTYPE = 'Innsjøkant' Or OBJTYPE = 'InnsjøkantRegulert' Or OBJTYPE = 'Kystkontur'"
custom_arcpy.attribute_select_and_make_feature_layer(
    input_n100.BegrensningsKurve,
    sql_expr_begrensningskurve_waterfeatures,
    "begrensningskurve_waterfeatures",
)
begrensningskurve_waterfeatures = "begrensningskurve_waterfeatures"

# Creating a buffer of the water features begrensningskurve to take into account symbology of the water features
buffer_distance_begrensningskurve_waterfeatures = "20 Meters"
output_buffer_begrensningskurve_waterfeatures = f"begrensningskurve_waterfeatures_{buffer_distance_begrensningskurve_waterfeatures.replace(' ', '')}_buffer"
arcpy.analysis.PairwiseBuffer(
    begrensningskurve_waterfeatures,
    output_buffer_begrensningskurve_waterfeatures,
    buffer_distance_begrensningskurve_waterfeatures,
    "NONE",
    "",
    "PLANAR",
)

# Adding hierarchy and invisibility fields to the begrensningskurve_waterfeatures_buffer and setting them to 0
arcpy.management.AddFields(
    output_buffer_begrensningskurve_waterfeatures,
    [["hierarchy", "LONG"], ["invisibility", "LONG"]],
)
arcpy.management.CalculateFields(
    output_buffer_begrensningskurve_waterfeatures,
    "PYTHON3",
    [["hierarchy", "0"], ["invisibility", "0"]],
)
