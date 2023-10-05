# Makes sure the path is relative to the root path
from rootpath import detect
import sys
root_path = detect()
sys.path.append(root_path)

# Importing config file from the root path
from config import n100_path

# Defining universal paths for n100 regardless of local path setup
AdminFlate = fr"{n100_path}\n100.gdb\AdminFlate"
AdminGrense = fr"{n100_path}\n100.gdb\AdminGrense"
AdminGrensePunkt = fr"{n100_path}\n100.gdb\AdminGrensePunkt"
Alpinbakke = fr"{n100_path}\n100.gdb\Alpinbakke"
AnleggsLinje = fr"{n100_path}\n100.gdb\AnleggsLinje"
AnleggsPunkt = fr"{n100_path}\n100.gdb\AnleggsPunkt"
ArealdekkeFlate = fr"{n100_path}\n100.gdb\ArealdekkeFlate"
Bane = fr"{n100_path}\n100.gdb\Bane"
BegrensingsKurve = fr"{n100_path}\n100.gdb\BegrensingsKurve"
BygningsPunkt = fr"{n100_path}\n100.gdb\BygningsPunkt"
ElvBekk = fr"{n100_path}\n100.gdb\ElvBekk"
Ferge = fr"{n100_path}\n100.gdb\Ferge"
Foss = fr"{n100_path}\n100.gdb\Foss"
Golfbane = fr"{n100_path}\n100.gdb\Golfbane"
Grunnlinje = fr"{n100_path}\n100.gdb\Grunnlinje"
Grunnriss = fr"{n100_path}\n100.gdb\Grunnriss"
HoydeKontur = fr"{n100_path}\n100.gdb\HoydeKontur"
HoydePunkt = fr"{n100_path}\n100.gdb\HoydePunkt"
HoydeTall = fr"{n100_path}\n100.gdb\HoydeTall"
JernbaneStasjon = fr"{n100_path}\n100.gdb\JernbaneStasjon"
LufthavnPunkt = fr"{n100_path}\n100.gdb\LufthavnPunkt"
Navn = fr"{n100_path}\n100.gdb\Navn"
OmrissLinje = fr"{n100_path}\n100.gdb\OmrissLinje"
Piktogram = fr"{n100_path}\n100.gdb\Piktogram"
Rullebane = fr"{n100_path}\n100.gdb\Rullebane"
Rutenett = fr"{n100_path}\n100.gdb\Rutenett"
Skjaer = fr"{n100_path}\n100.gdb\Skjaer"
SkyteFelt = fr"{n100_path}\n100.gdb\SkyteFelt"
StatsAllmenning = fr"{n100_path}\n100.gdb\StatsAllmenning"
Tile = fr"{n100_path}\n100.gdb\Tile"
TileKant = fr"{n100_path}\n100.gdb\TileKant"
TuristHytte = fr"{n100_path}\n100.gdb\TuristHytte"
VegSti = fr"{n100_path}\n100.gdb\VegSti"
VerneOmrade = fr"{n100_path}\n100.gdb\VerneOmrade"
