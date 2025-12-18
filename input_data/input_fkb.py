# Importing config file from the root path
from config import fkb_path
import arcpy

# Defining universal paths for fkb regardless of local path env_setup
fkb_lufthavn_grense = rf"{fkb_path}\fkb_lufthavn_grense"
fkb_lufthavn_omrade = rf"{fkb_path}\fkb_lufthavn_omrade"
fkb_byggoganlegg_senterlinje = rf"{fkb_path}\byggoganlegg_senterlinje"


# Defining datasets to test paths are set up correctly later
fkb_datasets = [
    fkb_lufthavn_grense,
    fkb_lufthavn_omrade,
    fkb_byggoganlegg_senterlinje,
]


# Looping through all paths to check if they are formatted correctly
def check_paths():
    for dataset in fkb_datasets:
        try:
            arcpy.management.MakeFeatureLayer(dataset, "temp_layer")
            arcpy.management.Delete("temp_layer")
        except Exception as e:
            print(f"Failed on {dataset}: {e}")
        else:
            print(f"Success on {dataset}")


if __name__ == "__main__":
    check_paths()