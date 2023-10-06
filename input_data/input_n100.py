# Makes sure the path is relative to the root path
from rootpath import detect
import sys
root_path = detect()
sys.path.append(root_path)

# Importing config file from the root path
from config import n100_path
import arcpy

# Defining universal paths for n100 regardless of local path setup
AdminFlate = fr"{n100_path}\AdminFlate"
AdminGrense = fr"{n100_path}\AdminGrense"
AdminGrensePunkt = fr"{n100_path}\AdminGrensePunkt"
Alpinbakke = fr"{n100_path}\Alpinbakke"
AnleggsLinje = fr"{n100_path}\AnleggsLinje"
AnleggsPunkt = fr"{n100_path}\AnleggsPunkt"
ArealdekkeFlate = fr"{n100_path}\ArealdekkeFlate"
Bane = fr"{n100_path}\Bane"
BegrensningsKurve = fr"{n100_path}\BegrensningsKurve"
BygningsPunkt = fr"{n100_path}\BygningsPunkt"
ElvBekk = fr"{n100_path}\ElvBekk"
Ferge = fr"{n100_path}\Ferge"
Foss = fr"{n100_path}\Foss"
Golfbane = fr"{n100_path}\Golfbane"
Grunnlinje = fr"{n100_path}\Grunnlinje"
Grunnriss = fr"{n100_path}\Grunnriss"
HoydeKontur = fr"{n100_path}\HoydeKontur"
HoydePunkt = fr"{n100_path}\HoydePunkt"
HoydeTall = fr"{n100_path}\HoydeTall"
JernbaneStasjon = fr"{n100_path}\JernbaneStasjon"
LufthavnPunkt = fr"{n100_path}\LufthavnPunkt"
Navn = fr"{n100_path}\Navn"
OmrissLinje = fr"{n100_path}\OmrissLinje"
Piktogram = fr"{n100_path}\Piktogram"
Rullebane = fr"{n100_path}\Rullebane"
Rutenett = fr"{n100_path}\Rutenett"
Skjaer = fr"{n100_path}\Skjaer"
SkyteFelt = fr"{n100_path}\SkyteFelt"
StatsAllmenning = fr"{n100_path}\StatsAllmenning"
Tile = fr"{n100_path}\Tile"
Tile_Kant = fr"{n100_path}\Tile_Kant"
TuristHytte = fr"{n100_path}\TuristHytte"
VegSti = fr"{n100_path}\VegSti"
VerneOmrade = fr"{n100_path}\VerneOmrade"

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


