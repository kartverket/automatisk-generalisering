# Importing config file from the root path
from config import n50_path
import arcpy

# Defining universal paths for n50 regardless of local path env_setup
AdminFlate = rf"{n50_path}\AdminFlate"
AdminGrense = rf"{n50_path}\AdminGrense"
AdminGrensePunkt = rf"{n50_path}\AdminGrensePunkt"
AnleggsLinje = rf"{n50_path}\AnleggsLinje"
AnleggsPunkt = rf"{n50_path}\AnleggsPunkt"
ArealdekkeFlate = rf"{n50_path}\ArealdekkeFlate"
Bane = rf"{n50_path}\Bane"
BegrensningsKurve = rf"{n50_path}\BegrensningsKurve"
BygningsPunkt = rf"{n50_path}\BygningsPunkt"
ElvBekk = rf"{n50_path}\ElvBekk"
Ferge = rf"{n50_path}\Ferge"
FlomLop = rf"{n50_path}\FlomLop"
Foss = rf"{n50_path}\Foss"
Grunnlinje = rf"{n50_path}\Grunnlinje"
Grunnriss = rf"{n50_path}\Grunnriss"
HoydeKontur = rf"{n50_path}\HoydeKontur"
HoydePunkt = rf"{n50_path}\HoydePunkt"
HoydeTall = rf"{n50_path}\HoydeTall"
JernbaneStasjon = rf"{n50_path}\JernbaneStasjon"
LufthavnPunkt = rf"{n50_path}\LufthavnPunkt"
Navn = rf"{n50_path}\Navn"
OmrissLinje = rf"{n50_path}\OmrissLinje"
Skjaer = rf"{n50_path}\Skjaer"
SkyteFelt = rf"{n50_path}\SkyteFelt"
StatsAllmenning = rf"{n50_path}\StatsAllmenning"
Tile = rf"{n50_path}\Tile"
TileKant = rf"{n50_path}\TileKant"
TreGruppe = rf"{n50_path}\TreGruppe"
TuristHytte = rf"{n50_path}\TuristHytte"
VegBom = rf"{n50_path}\VegBom"
VegSti = rf"{n50_path}\VegSti"
VerneOmrade = rf"{n50_path}\VerneOmrade"

# Defining datasets to test paths are set up correctly later
n50_datasets = [
    AdminFlate,
    AdminGrense,
    AdminGrensePunkt,
    AnleggsLinje,
    AnleggsPunkt,
    ArealdekkeFlate,
    Bane,
    BegrensningsKurve,
    BygningsPunkt,
    ElvBekk,
    Ferge,
    FlomLop,
    Foss,
    Grunnlinje,
    Grunnriss,
    HoydeKontur,
    HoydePunkt,
    HoydeTall,
    JernbaneStasjon,
    LufthavnPunkt,
    Navn,
    OmrissLinje,
    Skjaer,
    SkyteFelt,
    StatsAllmenning,
    Tile,
    TileKant,
    TreGruppe,
    TuristHytte,
    VegBom,
    VegSti,
    VerneOmrade,
]


# Looping through all paths to check if they are formatted correctly
def check_paths():
    for dataset in n50_datasets:
        try:
            arcpy.management.MakeFeatureLayer(dataset, "temp_layer")
            arcpy.management.Delete("temp_layer")
        except Exception as e:
            print(f"Failed on {dataset}: {e}")
        else:
            print(f"Success on {dataset}")
