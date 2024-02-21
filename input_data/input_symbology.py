from enum import Enum

import config


# Defining universal paths for other files regardless of local path env_setup
class SymbologyN100(Enum):
    veg_sti = config.symbology_n100_veg_sti
    begrensnings_kurve_buffer = config.symbology_n100_begrensningskurve_buffer
    begrensnings_kurve_line = config.symbology_n100_begrensningskurve_line
    bygningspunkt = config.symbology_n100_bygningspunkt
    grunnriss = config.symbology_n100_grunnriss
    drawn_plygon = config.symbology_n100_drawn_plygon
