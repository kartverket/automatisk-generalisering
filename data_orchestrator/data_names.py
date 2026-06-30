"This file contains all the standard names of feature types and classes that we use."

from enum import StrEnum


class DataNames(StrEnum):
    #########################
    # Main folder names
    #########################
    area = "AREA"
    building = "BUILDING"
    matrikkel = "MATRIKKEL"
    railway = "RAILWAY"
    road = "ROAD"
    symbology = "SYMBOLOGY"

    #########################
    # Scale names
    #########################
    scale_n10 = "n10"
    scale_n50 = "n50"
    scale_n100 = "n100"
    scale_n250 = "n250"
    scale_n500 = "n500"

    #########################
    # Main sub folder names
    #########################

    object_admin = "admin"
    object_arealdekke_flate = "land_use"
    object_bygning = "building"
    object_elv_bekk = "river"
    object_veg_sti = "road"
    object_bygg_og_anlegg = "facility"
    object_bane = "railway"
    object_hoyde = "landforms"
    lyrx_directory_name = "lyrx_outputs"

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
