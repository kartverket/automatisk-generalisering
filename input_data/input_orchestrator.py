# Imports

from pathlib import Path

from config import input_data_folder
from input_data.input_setup import EXPECTED, FolderSpec


# ========================
# InputDataOrchestrator
# ========================


class InputDataOrchestrator:
    """
    Orchestrator handling all input data by validating and fetching relevant data only.
    """

    def __init__(self):
        self.path = Path(input_data_folder)

        self.assert_valid_structure(self.path)


    # ========================
    # Helper functions
    # ========================


    def assert_valid_structure(self, path: Path):
        """
        Checks that the folder structure is valid.
        """
        # Check validation
        m, e = self.scan_folder_structure(path, EXPECTED)

        # If unvalid match, throw error:
        if m or e:
            raise RuntimeError(
                f"Folder structure validation failed.\n"
                f"Missing: {m}\n"
                f"Extra: {e}"
            )


    def scan_folder_structure(self, path: Path, spec: FolderSpec) -> tuple:
        """
        Checks that the folder structure in the given path matches the expected structure.

        Args:
            path (Path): The path to the folder to validate
            spec (FolderSpec): The expected folder structure

        Returns:
            missing (list): A list of missing files and folders
            extra (list): A list of extra files and folders
        """
        missing, extra = [], []

        # Fetch actual content
        actual_files, actual_folders = set(), set()
        for p in path.iterdir():
            (actual_files if p.suffix.lower() == ".gdb" or p.is_file() else actual_folders).add(
                p.name
            )

        # Check for missing or extra data
        exp_files = spec.files
        exp_folders = spec.folders.keys()

        missing += [f for f in exp_files - actual_files]
        missing += [f"{d}/" for d in exp_folders - actual_folders]

        extra += [f for f in actual_files - exp_files]
        extra += [f"{d}/" for d in actual_folders - exp_folders]

        # Recursion for subfolders
        for dirname, sub_spec in spec.folders.items():
            if (path / dirname).exists():
                sub_missing, sub_extra = self.scan_folder_structure(Path.joinpath(path, dirname), sub_spec)
                missing.extend(sub_missing)
                extra.extend(sub_extra)

        return missing, extra


# ========================

if __name__ == "__main__":
    test = InputDataOrchestrator()
