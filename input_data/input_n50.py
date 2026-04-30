# Libraries

from config import input_data_folder

from pathlib import Path

# Setup main N50 path

n50_path = Path.joinpath(Path(input_data_folder), "raw_data", "n50_09_01_2025.gdb")

# Setup feature class paths

# AdminFlate = Path.joinpath(n50_path, "AdminFlate")
# AdminGrense = Path.joinpath(n50_path, "AdminGrense")
# AdminGrensePunkt = Path.joinpath(n50_path, "AdminGrensePunkt")
AnleggsLinje = Path.joinpath(n50_path, "AnleggsLinje")
AnleggsPunkt = Path.joinpath(n50_path, "AnleggsPunkt")
ArealdekkeFlate = Path.joinpath(n50_path, "ArealdekkeFlate")
Bane = Path.joinpath(n50_path, "Bane")
BegrensningsKurve = Path.joinpath(n50_path, "BegrensningsKurve")
BygningsPunkt = Path.joinpath(n50_path, "BygningsPunkt")
ElvBekk = Path.joinpath(n50_path, "ElvBekk")
Ferge = Path.joinpath(n50_path, "Ferge")
FlomLop = Path.joinpath(n50_path, "FlomLop")
Foss = Path.joinpath(n50_path, "Foss")
# Grunnlinje = Path.joinpath(n50_path, "Grunnlinje")
Grunnriss = Path.joinpath(n50_path, "Grunnriss")
HoydeKontur = Path.joinpath(n50_path, "HoydeKontur")
HoydePunkt = Path.joinpath(n50_path, "HoydePunkt")
# HoydeTall = Path.joinpath(n50_path, "HoydeTall")
JernbaneStasjon = Path.joinpath(n50_path, "JernbaneStasjon")
LufthavnPunkt = Path.joinpath(n50_path, "LufthavnPunkt")
# Navn = Path.joinpath(n50_path, "Navn")
OmrissLinje = Path.joinpath(n50_path, "OmrissLinje")
Skjaer = Path.joinpath(n50_path, "Skjaer")
# SkyteFelt = Path.joinpath(n50_path, "SkyteFelt")
# StatsAllmenning = Path.joinpath(n50_path, "StatsAllmenning")
# Tile = Path.joinpath(n50_path, "Tile")
# TileKant = Path.joinpath(n50_path, "TileKant")
TreGruppe = Path.joinpath(n50_path, "TreGruppe")
TuristHytte = Path.joinpath(n50_path, "TuristHytte")
VegBom = Path.joinpath(n50_path, "VegBom")
VegSti = Path.joinpath(n50_path, "VegSti")
# VerneOmrade = Path.joinpath(n50_path, "VerneOmrade")

# Create dataset for imports

DATA = [
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
    Grunnriss,
    HoydeKontur,
    HoydePunkt,
    JernbaneStasjon,
    LufthavnPunkt,
    OmrissLinje,
    Skjaer,
    TreGruppe,
    TuristHytte,
    VegBom,
    VegSti,
]
