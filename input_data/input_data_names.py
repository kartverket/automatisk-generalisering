"This file contains all the standard names of feature types and classes that we use."

from enum import StrEnum


class DataNames(StrEnum):
    #########################
    # Main names
    #########################
    area = "AREA"
    building = "BUILDING"
    matrikkel = "MATRIKKEL"
    railway = "RAILWAY"
    road = "ROAD"
    symbology = "SYMBOLOGY"

    #########################
    # Sub names
    #########################

    # Area
    AdminFlate_N50 = "AdminFlate_N50"
    AdminGrense_N50 = "AdminGrense_N50"
    Arealdekke_Test = "Arealdekke_Test"
    ArealdekkeFlate = "ArealdekkeFlate"
    ArealdekkeFlate_N10 = "ArealdekkeFlate_N10"
    ArealdekkeFlate_N50 = "ArealdekkeFlate_N50"
    Begrensningskurve_N50 = "Begrensningskurve_N50"
    Fishnet_500m = "Fishnet_500m"

    # Building
    AnleggsLinje_N50 = "AnleggsLinje_N50"
    BygningsPunkt_N10 = "BygningsPunkt_N10"
    Grunnriss_N10 = "Grunnriss_N10"
    TuristHytte_N10 = "TuristHytte_N10"

    # Matrikkel
    bygning = "bygning"

    # Railway
    Bane_N50 = "Bane_N50"
    JernbaneStasjon_N50 = "JernbaneStasjon_N50"

    # Road
    elveg_and_sti = "elveg_and_sti"
    vegsperring = "vegsperring"
    VegSti_N50 = "VegSti_N50"
