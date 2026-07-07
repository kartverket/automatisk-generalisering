# Libraries

import os

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict

# Classes


@dataclass(frozen=True)
class FolderSpec:
    name: str = field(default_factory=str)
    files: frozenset[str] = field(default_factory=set)
    folders: Dict[str, "FolderSpec"] = field(default_factory=dict)

    def all_files(self, prefix: str = "") -> set[str]:
        """
        Returns a set of all the possible paths that this FolderSpec contains.

        Args:
            prefix (str): The prefix to add to the paths
        """
        current_path = os.path.join(prefix, self.name)

        result = {os.path.join(current_path, f) for f in self.files}

        for subfolder in self.folders.values():
            result.update(subfolder.all_files(prefix=current_path))

        return result


# Functionality


def create_folder_spec(
    path: Path, map_scale: str, structure: dict, gdb: bool = True
) -> FolderSpec:
    """
    Creates a new FolderSpec based on the input structure.

    Args:
        path (Path): The path to the folder structure
        map_scale (str): Current map scale to check files and folders for
        structure (dict): The complete structure that is required
        gdb (bool): Whether to include the .gdb folder in the structure

    Returns:
        FolderSpec: A new FolderSpec object containing the required
                    structure for this pipeline
    """
    postfix = ".gdb" if gdb else ""
    folders = {
        f"{key.lower()}{postfix}": folder(f"{key.lower()}{postfix}", files=values)
        for key, values in structure.items()
    }
    return folder(str(path), folders={map_scale: folder(map_scale, folders=folders)})


# Helpers


def folder(name: str, *, files=None, folders=None) -> FolderSpec:
    """
    Creates a specific FolderSpec for a folder.

    Args:
        name
    """
    return FolderSpec(name=name, files=set(files or []), folders=folders or {})
