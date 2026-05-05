# Libraries

from dataclasses import dataclass, field
from typing import Set, Dict

# Classes


@dataclass(frozen=True)
class FolderSpec:
    files: Set[str] = field(default_factory=set)
    folders: Dict[str, "FolderSpec"] = field(default_factory=dict)


EXPECTED = FolderSpec(
    folders={
        "raw_data": FolderSpec(
            files={
                "area.gdb",
                "building.gdb",
                "matrikkel.gdb",
                "railway.gdb",
                "road.gdb",
            },
        ),
        "symbology": FolderSpec(
            folders={
                "n100": FolderSpec(
                    files={
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
                    files={"N250_Begrensningskurve.lyrx", "N250_Samferdsel.lyrx"}
                ),
            }
        ),
    }
)
