from enum import Enum
import  config

relative_path = rf"{config.output_folder}\n100\building.gdb"
scale = "n100"


def generate_file_name(function_name, description, scale):
    return rf"{relative_path}\{function_name}__{description}__{scale}"

# Function name definition:
selecting_grunnriss_for_generalization = "selecting_grunnriss_for_generalization"


class Building_N100(Enum):
    selecting_grunnriss_for_generalization__grunnriss_selection_not_church__n100 = generate_file_name(
        function_name=selecting_grunnriss_for_generalization,
        description="grunnriss_selection_not_church",
        scale= scale
    )

    # Example how file name will look like in ArcGIS Pro:
    "selecting_grunnriss_for_generalization__grunnriss_selection_not_church__n100"

    # Example of absolute path for the file name:
    r"C:\path\path\n100\building.gdb\selecting_grunnriss_for_generalization__grunnriss_selection_not_church__n100"


    r"C:\path\path\automatic_generalization_outputs\n100\building.gdb\selecting_grunnriss_for_generalization__grunnriss_selection_not_church__n100"