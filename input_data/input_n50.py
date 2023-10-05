# Makes sure the path is relative to the root path
from rootpath import detect
import sys
root_path = detect()
sys.path.append(root_path)

# Importing config file from the root path
from config import n50_path

# Defining universal paths for n50 regardless of local path setup
AdminFlate = fr"{n50_path}\AdminFlate"
AdminGrense = fr"{n50_path}\AdminGrense"
AdminGrensePunkt = fr"{n50_path}\AdminGrensePunkt"
AnleggsLinje = fr"{n50_path}\AnleggsLinje"
AnleggsPunkt = fr"{n50_path}\AnleggsPunkt"
ArealdekkeFlate = fr"{n50_path}\ArealdekkeFlate"
Bane = fr"{n50_path}\Bane"
Begrensingskurve = fr"{n50_path}\Begrensingskurve"
BygningsPunkt = fr"{n50_path}\BygningsPunkt"
ElvBekk = fr"{n50_path}\ElvBekk"
Ferge = fr"{n50_path}\Ferge"
FlomLop = fr"{n50_path}\FlomLop"
Foss = fr"{n50_path}\Foss"
Grunnlinje = fr"{n50_path}\Grunnlinje"
Grunnriss = fr"{n50_path}\Grunnriss"
HoydeKontur = fr"{n50_path}\HoydeKontur"
HoydePunkt = fr"{n50_path}\HoydePunkt"
HoydeTall = fr"{n50_path}\HoydeTall"
JernbaneStasjon = fr"{n50_path}\JernbaneStasjon"
LufthavnPunkt = fr"{n50_path}\LufthavnPunkt"
Navn = fr"{n50_path}\Navn"
OmrissLinje = fr"{n50_path}\OmrissLinje"
Skjaer = fr"{n50_path}\Skjaer"
SkyteFelt = fr"{n50_path}\SkyteFelt"
StatsAllmenning = fr"{n50_path}\StatsAllmenning"
Tile = fr"{n50_path}\Tile"
TileKant = fr"{n50_path}\TileKant"
TreGruppe = fr"{n50_path}\TreGruppe"
TuristHytte = fr"{n50_path}\TuristHytte"
VegBom = fr"{n50_path}\VegBom"
VegSti = fr"{n50_path}\VegSti"
VerneOmrade = fr"{n50_path}\VerneOmrade"