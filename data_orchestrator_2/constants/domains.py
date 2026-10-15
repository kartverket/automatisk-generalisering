# Libraries

from enum import StrEnum

######################
# Classes
######################

""" Which values are allowed for field [...] """


class Konnekteringslenke(StrEnum):
    IKKEKONNEKTERINGSLENKE = "NEI"
    KONNEKTERINGSLENKE = "JA"


class Medium(StrEnum):
    """https://register.geonorge.no/sosi-kodelister/kartdata/mediumsamferdsel"""

    BYGNING = "B"
    LUFT = "L"
    TERRENG = "T"
    UNDER = "U"


class Motorvegtype(StrEnum):
    """https://register.geonorge.no/sosi-kodelister/kartdata/motorvegtype"""

    IKKEMOTORVEG = "IkkeMotorveg"
    MOTORTRAFIKKVEG = "motortrafikkveg"
    MOTORVEG = "motorveg"
    UDEFINERT = "Udefinert"


class Objtype(StrEnum):
    BARMARKSLØYPE = "Barmarksløype"
    GANGSYKKELVEG = "GangSykkelveg"
    STI = "Sti"
    TRAKTORVEG = "Traktorveg"
    VEGSENTERLINJE = "VegSenterlinje"


class Rutemerking(StrEnum):
    """https://register.geonorge.no/sosi-kodelister/kartdata/rutemerking"""

    IKKEMERKET = "Nei"
    MERKETUSPESIFISERT = "Ja"
    UDEFINERT = "Udefinert"


class TypeVeg(StrEnum):
    """https://register.geonorge.no/sosi-kodelister/kartdata/typeveg"""

    ANNET = "annet"
    BARMARKSLØYPE = "barmarksløype"
    BILFERJE = "bilferje"
    ENKELBILVEG = "enkelBilveg"
    GANGOGSYKKELVEG = "gangOgSykkelveg"
    GANGVEG = "gangveg"
    KANALISERTVEG = "kanalisertVeg"
    PASSASJERFERJE = "passasjerferje"
    RAMPE = "rampe"
    RUNDKJØRING = "rundkjøring"
    STI = "sti"
    TRAKTORVEG = "traktorveg"


class Vedlikeh(StrEnum):
    """https://register.geonorge.no/sosi-kodelister/kartdata/vedlikeholdsansvarlig"""

    ANDRE = "Andre"
    DNT = "DNT"
    UKJENT = "Ukjent"


class Vegkategori(StrEnum):
    """https://register.geonorge.no/sosi-kodelister/kartdata/vegkategori"""

    EUROPAVEG = "E"
    FYLKESVEG = "F"
    KOMMUNALVEG = "K"
    PRIVATVEG = "P"
    RIKSVEG = "R"
