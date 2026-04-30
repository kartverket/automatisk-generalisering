# Libraries

from config import input_data_folder

from pathlib import Path

# Setup main N100 path

n100_path = Path.joinpath(Path(input_data_folder), "raw_data", "N100_FGDB.gdb")

# Setup feature class paths

AdminFlate = Path.joinpath(n100_path, "AdminFlate")
AdminGrense = Path.joinpath(n100_path, "AdminGrense")
AdminGrensePunkt = Path.joinpath(n100_path, "AdminGrensePunkt")
Alpinbakke = Path.joinpath(n100_path, "Alpinbakke")
AnleggsLinje = Path.joinpath(n100_path, "AnleggsLinje")
AnleggsPunkt = Path.joinpath(n100_path, "AnleggsPunkt")
ArealdekkeFlate = Path.joinpath(n100_path, "ArealdekkeFlate")
Bane = Path.joinpath(n100_path, "Bane")
BegrensningsKurve = Path.joinpath(n100_path, "BegrensningsKurve")
BygningsPunkt = Path.joinpath(n100_path, "BygningsPunkt")
ElvBekk = Path.joinpath(n100_path, "ElvBekk")
Ferge = Path.joinpath(n100_path, "Ferge")
Foss = Path.joinpath(n100_path, "Foss")
Golfbane = Path.joinpath(n100_path, "Golfbane")
Grunnlinje = Path.joinpath(n100_path, "Grunnlinje")
Grunnriss = Path.joinpath(n100_path, "Grunnriss")
HoydeKontur = Path.joinpath(n100_path, "HoydeKontur")
HoydePunkt = Path.joinpath(n100_path, "HoydePunkt")
HoydeTall = Path.joinpath(n100_path, "HoydeTall")
JernbaneStasjon = Path.joinpath(n100_path, "JernbaneStasjon")
LufthavnPunkt = Path.joinpath(n100_path, "LufthavnPunkt")
Navn = Path.joinpath(n100_path, "Navn")
OmrissLinje = Path.joinpath(n100_path, "OmrissLinje")
Piktogram = Path.joinpath(n100_path, "Piktogram")
Rullebane = Path.joinpath(n100_path, "Rullebane")
Rutenett = Path.joinpath(n100_path, "Rutenett")
Skjaer = Path.joinpath(n100_path, "Skjaer")
SkyteFelt = Path.joinpath(n100_path, "SkyteFelt")
StatsAllmenning = Path.joinpath(n100_path, "StatsAllmenning")
Tile = Path.joinpath(n100_path, "Tile")
Tile_Kant = Path.joinpath(n100_path, "Tile_Kant")
TuristHytte = Path.joinpath(n100_path, "TuristHytte")
VegSti = Path.joinpath(n100_path, "VegSti")
VerneOmrade = Path.joinpath(n100_path, "VerneOmrade")

# Create dataset for imports

DATA = [
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
