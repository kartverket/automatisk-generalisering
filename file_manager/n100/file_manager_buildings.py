from enum import Enum

class TemporaryFiles(Enum):
    begrensningskurve_buffer_waterfeatures = (
        "begrensningskurve_waterfeatures_20m_buffer"
    )
    unsplit_veg_sti_n100 = "unsplit_veg_sti_n100"
    matrikkel_bygningspunkt = "matrikkel_bygningspunkt"
    grunnriss_selection_n50 = "grunnriss_selection_n50"
    kirke_sykehus_points_n50 = "kirke_sykehus_points_n50"
    bygningspunkt_pre_symbology = "bygningspunkt_pre_symbology"

class PermanentFiles(Enum):
    n100_building_points_undefined_nbr_values = "n100_building_points_undefined_nbr_values"
