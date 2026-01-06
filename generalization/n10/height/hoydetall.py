# Libraries

import arcpy

arcpy.env.overwriteOutput = True

import numpy as np
import os

from tqdm import tqdm

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from file_manager import WorkFileManager
from file_manager.n10 import *
from input_data import input_fkb, input_n50

# ========================
# Program
# ========================


@timing_decorator
def main():
    """
    The main program that is generalizing runways from FKB and N50 to N100.
    """

# ========================
# Main functions
# ========================

# ...

arcpy.cartography.ContourAnnotation(
    in_features="",
    out_geodatabase="",
    contour_label_field="",
    reference_scale_value="",
    out_layer="",
    contour_color="BROWN",
    contour_type_field="",
    contour_alignment="",
    enable_laddering="ENABLE_LADDERING",
)

# ========================
# Helper functions
# ========================

# ...

# ========================

if __name__ == "__main__":
    main()