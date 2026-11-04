# Libraries

from enum import StrEnum

######################
# Classes
######################


class GDBName(StrEnum):
    AREA = "area"
    BUILDING = "building"
    RAILWAY = "railway"
    ROAD = "road"


class FeatureClassName(StrEnum):
    ADMINFLATE = "AdminFlate"
    ADMINGRENSE = "AdminGrense"
    ANLEGGSLINJE = "AnleggsLinje"
    AREALDEKKE = "ArealdekkeFlate"
    BANE = "Bane"
    BEGRENSNINGSKURVE = "Begrensningskurve"
    BYGNINGSPUNKT = "BygningsPunkt"
    ELVEG_AND_STI = "elveg_and_sti"
    GRUNNRISS = "Grunnriss"
    JERNBANESTASJON = "JernbaneStasjon"
    TURISTHYTTE = "TuristHytte"
    VEGSPERRING = "vegsperring"
