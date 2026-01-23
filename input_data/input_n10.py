# Importing config file from the root path
from config import n10_path
import arcpy

# Defining universal paths for n10 regardless of local path env_setup
Buildings = rf"{n10_path}\fkb_bygning_omrade"
Airport = rf"{n10_path}\n50k_lufthavn_punkt_p450"
Contours = rf"{n10_path}\n10_hoydekurver_5m"

# Annotations
Stedsnavn = rf"{n10_path}\N10_Stedsnavn_2026_Anno10000"
Stedsnavn_linje = rf"{n10_path}\Stedsnavn_linje_2026Anno10000"
Veglenke = rf"{n10_path}\N10_Veglenke_2026Anno10000"
Veglenke_overbygg = rf"{n10_path}\Veglenke_Overbygg_2026Anno10000"
Veglenke_tunnel = rf"{n10_path}\Veglenke_Tunnel_2026Anno10000"
Hoydetall = rf"{n10_path}\N20_Hoydetall_10000"
Visning = rf"{n10_path}\ssrkopi_visningstjenesteAnno10000"

# Defining datasets to test paths are set up correctly later
n10_datasets = [
    Buildings,
    Airport,
    Contours,
    Stedsnavn,
    Stedsnavn_linje,
    Veglenke,
    Veglenke_overbygg,
    Veglenke_tunnel,
    Hoydetall,
    Visning,
]

# Annotations
annotations = [
    Stedsnavn,
    Stedsnavn_linje,
    Veglenke,
    Veglenke_overbygg,
    Veglenke_tunnel,
    Hoydetall,
    Visning,
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
