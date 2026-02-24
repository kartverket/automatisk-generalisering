# Importing config file from the root path
from config import n10_path
import arcpy

# Defining universal paths for n10 regardless of local path env_setup
Allmenning = rf"{n10_path}\Allmenning"
arealdekkeflate = rf"{n10_path}\arealdekkeflate"
bane = rf"{n10_path}\bane"
bygning_omrade = rf"{n10_path}\bygning_omrade"
campingplass = rf"{n10_path}\campingplass"
demning = rf"{n10_path}\demning"
grunnmur_linje = rf"{n10_path}\grunnmur_linje"
gruve = rf"{n10_path}\gruve"
hoppbakke = rf"{n10_path}\hoppbakke"
jernbanestasjon = rf"{n10_path}\jernbanestasjon"
kaibrygge = rf"{n10_path}\kaibrygge"
ledning = rf"{n10_path}\ledning"
mast = rf"{n10_path}\mast"
molo = rf"{n10_path}\molo"
mur = rf"{n10_path}\mur"
N10_Hoydekurver_5m = rf"{n10_path}\N10_Hoydekurver_5m"
N10_Stedsnavn_2026_Anno10000 = rf"{n10_path}\N10_Stedsnavn_2026_Anno10000"
N10_Stedsnavn_2026_V3_punkt = rf"{n10_path}\N10_Stedsnavn_2026_V3_punkt"
N10_Veglenke_2026Anno10000 = rf"{n10_path}\N10_Veglenke_2026Anno10000"
N20_Hoydetall_10000 = rf"{n10_path}\N20_Hoydetall_10000"
navigasjonsinstallasjon = rf"{n10_path}\navigasjonsinstallasjon"
parkeringsomrade_omrade = rf"{n10_path}\parkeringsomrade_omrade"
parkeringsområde = rf"{n10_path}\parkeringsområde"
pipe = rf"{n10_path}\pipe"
rorgate = rf"{n10_path}\rorgate"
ruin = rf"{n10_path}\ruin"
skjerm = rf"{n10_path}\skjerm"
skytebane = rf"{n10_path}\skytebane"
skytebaneinnretning = rf"{n10_path}\skytebaneinnretning"
slipp = rf"{n10_path}\slipp"
snøskuterløype = rf"{n10_path}\snøskuterløype"
Stedsnavn_linje_2026Anno10000 = rf"{n10_path}\Stedsnavn_linje_2026Anno10000"
svommebasseng = rf"{n10_path}\svommebasseng"
takoverbygg = rf"{n10_path}\takoverbygg"
tank = rf"{n10_path}\tank"
tank_omrade = rf"{n10_path}\tank_omrade"
tarn = rf"{n10_path}\tarn"
taubane = rf"{n10_path}\taubane"
transformatorstasjon = rf"{n10_path}\transformatorstasjon"
tribune = rf"{n10_path}\tribune"
veglenke = rf"{n10_path}\veglenke"
Veglenke_Overbygg_2026Anno10000 = rf"{n10_path}\Veglenke_Overbygg_2026Anno10000"
Veglenke_Tunnel_2026Anno10000 = rf"{n10_path}\Veglenke_Tunnel_2026Anno10000"
vegsperring = rf"{n10_path}\vegsperring"
vindturbin = rf"{n10_path}\vindturbiner"
voll = rf"{n10_path}\voll"

Railways = rf"{n10_path}\fkb_bane_senterlinje"
N50HoydePunkt = rf"{n10_path}\N50HoydePunkt"
FKBforsenkningspunkt = rf"{n10_path}\FKBforsenkningspunkt"
FKBterrengpunkt = rf"{n10_path}\FKBterrengpunkt"
ArealdekkeFlate_bebygd = rf"{n10_path}\ArealdekkeFlate_bebygd"
AdminFlate = rf"{n10_path}\AdminFlate"
Buildings = rf"{n10_path}\bygning_omrade"
Contours = rf"{n10_path}\n10_hoydekurver_5m"

# Annotations
Stedsnavn = rf"{n10_path}\N10_Stedsnavn_2026_Anno10000"
Stedsnavn_linje = rf"{n10_path}\Stedsnavn_linje_2026Anno10000"
Veglenke = rf"{n10_path}\N10_Veglenke_2026Anno10000"
Veglenke_overbygg = rf"{n10_path}\Veglenke_Overbygg_2026Anno10000"
Veglenke_tunnel = rf"{n10_path}\Veglenke_Tunnel_2026Anno10000"
Hoydetall = rf"{n10_path}\N20_Hoydetall_10000"


# Defining datasets to test paths are set up correctly later
n10_datasets = [
    Allmenning,
    arealdekkeflate,
    bane,
    bygning_omrade,
    campingplass,
    demning,
    grunnmur_linje,
    gruve,
    hoppbakke,
    jernbanestasjon,
    kaibrygge,
    ledning,
    mast,
    molo,
    mur,
    N10_Hoydekurver_5m,
    N10_Stedsnavn_2026_Anno10000,
    N10_Stedsnavn_2026_V3_punkt,
    N10_Veglenke_2026Anno10000,
    N20_Hoydetall_10000,
    navigasjonsinstallasjon,
    parkeringsomrade_omrade,
    parkeringsområde,
    pipe,
    rorgate,
    ruin,
    skjerm,
    skytebane,
    skytebaneinnretning,
    slipp,
    snøskuterløype,
    Stedsnavn_linje_2026Anno10000,
    svommebasseng,
    takoverbygg,
    tank,
    tank_omrade,
    tarn,
    taubane,
    transformatorstasjon,
    tribune,
    veglenke,
    Veglenke_Overbygg_2026Anno10000,
    Veglenke_Tunnel_2026Anno10000,
    vegsperring,
    vindturbin,
    voll,
    Railways,
    N50HoydePunkt,
    FKBforsenkningspunkt,
    FKBterrengpunkt,
    ArealdekkeFlate_bebygd,
    AdminFlate,
    Buildings,
    Contours,
    Stedsnavn,
    Stedsnavn_linje,
    Veglenke,
    Veglenke_overbygg,
    Veglenke_tunnel,
    Hoydetall,
]

# Annotations
annotations = [
    Stedsnavn,
    Stedsnavn_linje,
    Veglenke,
    Veglenke_overbygg,
    Veglenke_tunnel,
    Hoydetall,
]

# Annotations
annotations = [
    N10_Stedsnavn_2026_Anno10000,
    N10_Veglenke_2026Anno10000,
    N20_Hoydetall_10000,
    Stedsnavn_linje_2026Anno10000,
    Veglenke_Overbygg_2026Anno10000,
    Veglenke_Tunnel_2026Anno10000,
]


# Looping through all paths to check if they are formatted correctly
def check_paths():
    for dataset in n10_datasets:
        try:
            arcpy.management.MakeFeatureLayer(dataset, "temp_layer")
            arcpy.management.Delete("temp_layer")
        except Exception as e:
            print(f"Failed on {dataset}: {e}")
        else:
            print(f"Success on {dataset}")


if __name__ == "__main__":
    check_paths()
