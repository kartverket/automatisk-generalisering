# Importing config file from the root path
from config import n10_path
import arcpy

# Defining universal paths for n10 regardless of local path env_setup
Railways = rf"{n10_path}\fkb_bane_senterlinje"
N50HoydePunkt = rf"{n10_path}\N50HoydePunkt"
FKBforsenkningspunkt = rf"{n10_path}\FKBforsenkningspunkt"
FKBterrengpunkt = rf"{n10_path}\FKBterrengpunkt"
ArealdekkeFlate = rf"{n10_path}\ArealdekkeFlate"
ArealdekkeFlate_bebygd = rf"{n10_path}\ArealdekkeFlate_bebygd"
Arealdekke_Oslo = rf"{n10_path}\Arealdekke_Oslo"
Arealdekke_Norge = rf"{n10_path}\Arealdekke_Norge"
AdminFlate = rf"{n10_path}\AdminFlate"
Fishnet_500m = rf"{n10_path}\Fishnet_500m"

# Defining datasets to test paths are set up correctly later
n10_datasets = [
    Railways,
    N50HoydePunkt,
    FKBforsenkningspunkt,
    FKBterrengpunkt,
    ArealdekkeFlate,
    ArealdekkeFlate_bebygd,
    Arealdekke_Oslo,
    Arealdekke_Norge,
    AdminFlate,
    Fishnet_500m,
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
