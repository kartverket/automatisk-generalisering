# Importing config file from the root path
from config import n10_arealdekke_path
import arcpy

# Defining universal paths for n10 regardless of local path env_setup
arealdekke = rf"{n10_arealdekke_path}\Arealdekke_Buskerud"
fishnet_500m=rf"{n10_arealdekke_path}\Fishnet_500m"

# Defining datasets to test paths are set up correctly later
n10_datasets = [
    arealdekke,
    fishnet_500m
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
