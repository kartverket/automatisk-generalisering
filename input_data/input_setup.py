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
            files={"N10_input.gdb", "N100_FGDB.gdb", "Roads.gdb"},
        ),
        "symbology": FolderSpec(
            folders={
                "n100": FolderSpec(
                    files={
                        "M616_Samferdsel.lyrx",
                        "N100_Arealdekke_grense_blå_maske.lyrx",
                    }
                ),
                "n250": FolderSpec(
                    files={"N250_Begrensningskurve.lyrx", "N250_Samferdsel.lyrx"}
                ),
            }
        ),
    }
)
