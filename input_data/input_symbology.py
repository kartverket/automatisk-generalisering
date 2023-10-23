from enum import Enum

import config

# Defining universal paths for other files regardless of local path env_setup
class SymbologyN100 (Enum):
    veg_sti = config.symbology_n100_veg_sti
    begrensnings_kurve = config.symbology_n100_begrensningskurve
    bygningspunkt = config.symbology_n100_bygningspunkt
    grunnriss = config.symbology_n100_grunnriss