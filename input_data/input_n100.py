# Importing config file from the root path
from config import n100_path
import arcpy

# Defining universal paths for n100 regardless of local path env_setup
AdminFlate = rf"{n100_path}\AdminFlate"
AdminGrense = rf"{n100_path}\AdminGrense"
AdminGrensePunkt = rf"{n100_path}\AdminGrensePunkt"
Alpinbakke = rf"{n100_path}\Alpinbakke"
AnleggsLinje = rf"{n100_path}\AnleggsLinje"
AnleggsPunkt = rf"{n100_path}\AnleggsPunkt"
ArealdekkeFlate = rf"{n100_path}\ArealdekkeFlate"
Bane = rf"{n100_path}\Bane"
BegrensningsKurve = rf"{n100_path}\BegrensningsKurve"
BygningsPunkt = rf"{n100_path}\BygningsPunkt"
ElvBekk = rf"{n100_path}\ElvBekk"
Ferge = rf"{n100_path}\Ferge"
Foss = rf"{n100_path}\Foss"
Golfbane = rf"{n100_path}\Golfbane"
Grunnlinje = rf"{n100_path}\Grunnlinje"
Grunnriss = rf"{n100_path}\Grunnriss"
HoydeKontur = rf"{n100_path}\HoydeKontur"
HoydePunkt = rf"{n100_path}\HoydePunkt"
HoydeTall = rf"{n100_path}\HoydeTall"
JernbaneStasjon = rf"{n100_path}\JernbaneStasjon"
LufthavnPunkt = rf"{n100_path}\LufthavnPunkt"
Navn = rf"{n100_path}\Navn"
OmrissLinje = rf"{n100_path}\OmrissLinje"
Piktogram = rf"{n100_path}\Piktogram"
Rullebane = rf"{n100_path}\Rullebane"
Rutenett = rf"{n100_path}\Rutenett"
Skjaer = rf"{n100_path}\Skjaer"
SkyteFelt = rf"{n100_path}\SkyteFelt"
StatsAllmenning = rf"{n100_path}\StatsAllmenning"
Tile = rf"{n100_path}\Tile"
Tile_Kant = rf"{n100_path}\Tile_Kant"
TuristHytte = rf"{n100_path}\TuristHytte"
VegSti = rf"{n100_path}\VegSti"
VerneOmrade = rf"{n100_path}\VerneOmrade"

# Defining datasets to test paths are set up correctly later
n100_datasets = [
    AdminFlate,
    AdminGrense,
    AdminGrensePunkt,
    Alpinbakke,
    AnleggsLinje,
    AnleggsPunkt,
    ArealdekkeFlate,
    Bane,
    BegrensningsKurve,
    BygningsPunkt,
    ElvBekk,
    Ferge,
    Foss,
    Golfbane,
    Grunnlinje,
    Grunnriss,
    HoydeKontur,
    HoydePunkt,
    HoydeTall,
    JernbaneStasjon,
    LufthavnPunkt,
    Navn,
    OmrissLinje,
    Piktogram,
    Rullebane,
    Rutenett,
    Skjaer,
    SkyteFelt,
    StatsAllmenning,
    Tile,
    Tile_Kant,
    TuristHytte,
    VegSti,
    VerneOmrade,
]


# Looping through all paths to check if they are formatted correctly
def check_paths():
    for dataset in n100_datasets:
        try:
            arcpy.management.MakeFeatureLayer(dataset, "temp_layer")
            arcpy.management.Delete("temp_layer")
        except Exception as e:
            print(f"Failed on {dataset}: {e}")
        else:
            print(f"Success on {dataset}")
