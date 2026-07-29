# Libraries

import arcpy

arcpy.env.overwriteOutput = True

from enum import StrEnum

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10

# ========================
# Class
# ========================

class names(StrEnum):
    test = "test"


# ========================
# Main function
# ========================


# ...


# ========================
# Helper functions
# ========================


# ...

# ========================
