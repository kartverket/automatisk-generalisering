# Importing config file from the root path
from config import n10_innsjoer_path
import arcpy

# Defining universal paths for n10 regardless of local path env_setup
hoyde_bearbeidet = r"{n10_path}\fkb_bane_senterlinje"



# Defining datasets to test paths are set up correctly later
n10_datasets = [
    hoyde_bearbeidet
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
