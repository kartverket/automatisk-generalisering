"""

This file is used as a lookup table for the different generalization pipelines.
Which datasets are needed to run a specific generalization pipeline, and which
columns do these feature classes to contain to be valid and useful in the
pipeline.

"""

from data_orchestrator.data_names import DataNames as dn

PIPELINE_INPUT = {
    "N10": {"building": [], "land_use": [], "road": []},
    "N50": {"building": [], "land_use": [], "road": []},
    "N100": {
        "building": [],
        "land_use": [],
        "road": {
            dn.area: [
                dn.AdminFlate_N50,
                dn.AdminGrense_N50,
                dn.ArealdekkeFlate_N10,
                dn.ArealdekkeFlate_N50,
                dn.Begrensningskurve_N50,
            ],
            dn.building: [dn.AnleggsLinje_N50],
            dn.railway: [dn.Bane_N50],
            dn.road: [dn.elveg_and_sti, dn.vegsperring],
        },
    },
    "N250": {"building": [], "land_use": [], "road": []},
    "N500": {"building": [], "land_use": [], "road": []},
}
