# Importing config file from the root path
from config import n10_path
import arcpy

# Defining universal paths for n10 regardless of local path env_setup
Buildings = rf"{n10_path}\fkb_bygning_omrade"
Airport = rf"{n10_path}\n50k_lufthavn_punkt_p450"
Contours = rf"{n10_path}\n10_hoydekurver_5m"
Railways = rf"{n10_path}\fkb_bane_senterlinje"
N50HoydePunkt = rf"{n10_path}\N50HoydePunkt"
FKBforsenkningspunkt = rf"{n10_path}\FKBforsenkningspunkt"
FKBterrengpunkt = rf"{n10_path}\FKBterrengpunkt"
ArealdekkeFlate = rf"{n10_path}\ArealdekkeFlate"
ArealdekkeFlate_bebygd = rf"{n10_path}\ArealdekkeFlate_bebygd"
AdminFlate = rf"{n10_path}\AdminFlate"

# Defining datasets to test paths are set up correctly later
n10_datasets = [
    # Buildings,
    # Airport,
    # Contours,
    Railways,
    N50HoydePunkt,
    FKBforsenkningspunkt,
    FKBterrengpunkt,
    ArealdekkeFlate,
    ArealdekkeFlate_bebygd,
    AdminFlate,
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
