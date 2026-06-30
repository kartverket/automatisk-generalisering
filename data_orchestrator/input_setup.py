# Libraries

from dataclasses import dataclass, field
from typing import Dict

from data_names import DataNames as dn

# Classes


@dataclass(frozen=True)
class FolderSpec:
    name: str = field(default_factory=str)
    files: frozenset[str] = field(default_factory=set)
    folders: Dict[str, "FolderSpec"] = field(default_factory=dict)


# Functionality


def create_folder_spec(map_scale: str, structure: dict) -> FolderSpec:
    """
    Creates a new FolderSpec based on the input structure.

    Args:
        map_scale (str): Current map scale to check files and folders for
        structure (dict): The complete structure that is required
    
    Returns:
        FolderSpec: A new FolderSpec object containing the required
                    structure for this pipeline
    """
    folders = {
        f"{key.lower()}.gdb": folder(
            f"{key.lower()}.gdb",
            files=values
        )
        for key, values in structure.items()
    }
    return folder(
        "root",
        folders={
            map_scale: folder(map_scale, folders=folders)
        }
    )


def get_folder_spec(map_scale: str) -> FolderSpec:
    """
    Returns the FolderSpec for a given scale.

    Args:
        map_scale (str): Current map scale
    """
    GDBS: list[str] = [dn.area, dn.building, dn.matrikkel, dn.railway, dn.road]

    scale_folder = FolderSpec(
        name=map_scale,
        files={f"{name.lower()}.gdb" for name in GDBS},
    )
    
    symbology_folder = FolderSpec(
        name="symbology",
        folders={
            "n100": FolderSpec(
                name="n100",
                files={
                    "AnleggsLinje_maske_sort.lyrx",
                    "begrensningskurve_buffer_water_features_n100.lyrx",
                    "building_points_symbology_n100.lyrx",
                    "building_polygons_drawn_from_points.lyrx",
                    "grunnriss_symbology_n100.lyrx",
                    "jernbanestasjon_square.lyrx",
                    "M616_Samferdsel.lyrx",
                    "N100_Arealdekke_grense_blå_maske.lyrx",
                    "railway_buffer.lyrx",
                }
            ),
            "n250": FolderSpec(
                name="n250",
                files={"N250_Begrensningskurve.lyrx", "N250_Samferdsel.lyrx"}
            ),
        }
    )

    return FolderSpec(
        name="root",
        folders={
            map_scale: scale_folder,
            "symbology": symbology_folder
        }
    )

# Helpers

def folder(name: str, *, files=None, folders=None) -> FolderSpec:
    """
    Creates a specific FolderSpec for a folder.

    Args:
        name
    """
    return FolderSpec(
        name=name,
        files=set(files or []),
        folders=folders or {}
    )
