import re
from pathlib import Path

import config

from composition_configs import type_defs
from env_setup.project_layout import ProjectLayout


class BaseFileManager:
    """
    The core file manager class handles the creation of absolute paths across our project,
    imported in different file managers.

    Functions:
        generate_file_name_gdb (str, str) -> str:
            Generates the absolute path for files that can be stored in geodatabases (gdb).
        generate_file_name_general_files (str, str, str) -> str:
            Generates the absolute path for files that cannot be stored in geodatabases,
            specifying its file type.
        generate_file_name_lyrx (str, str) -> str:
            Generates the absolute path for ArcGIS layer files (.lyrx) that cannot be stored
            in geodatabases.

    Args:
        scale (str): The scale of the geospatial data, used to differentiate directories and
                     file names. Needs to be defined when imported.
        object_name (str): The name of the geospatial object, used to differentiate directories
                           and file names. Needs to be defined when imported.

    This class provides methods to generate standardized absolute paths for geodatabase files,
    general files, and layer files, using the project's naming conventions and directory structure.
    """

    def __init__(
        self,
        scale: str,
        object_name: str,
        script_source_name: str = "",
        description: str = "",
    ):
        """Initializes the BaseFileManager with specific scale and object name."""
        self.scale = scale
        self.object = object_name
        self._script_source_name = ""
        self._description = ""
        self.script_source_name = script_source_name
        self.description = description

        layout = ProjectLayout(output_root=Path(config.output_folder))
        self._gdb_dir = layout.gdb(self.scale, self.object)
        self._general_dir = layout.general_files_dir(self.scale)
        self._lyrx_dir = layout.lyrx_dir(self.scale)
        self._final_outputs_dir = layout.gdb(self.scale, layout.final_outputs_name)

    @property
    def script_source_name(self):
        return self._script_source_name

    @script_source_name.setter
    def script_source_name(self, value):
        if not self._validate_input(value):
            raise ValueError("script_source_name must not contain spaces or dots.")
        self._script_source_name = value

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, value):
        if not self._validate_input(value):
            raise ValueError("description must not contain spaces or dots.")
        self._description = value

    @staticmethod
    def _validate_input(value):
        """Validate the input to ensure it does not contain illegal characters for filenames or whitespace."""
        illegal_characters = r'[<>:"/\|?*\s]'
        if re.search(illegal_characters, value):
            return False
        return True

    def validate_inputs(self, *args):
        """Uses the validate_input method to validate the input."""
        for arg in args:
            if arg is not None and not self._validate_input(arg):
                raise ValueError(f"{arg} must not contain spaces or dots.")

    def generate_file_name_gdb(
        self,
        script_source_name: str,
        description: str,
    ) -> type_defs.GdbFilePath:
        """
        Generates a file path for geodatabase (.gdb) files. After validating the input.

        Args:
            script_source_name (str): The name of the script or source generating the file.
            description (str): A brief description of the file's purpose or contents.

        Returns:
            str: The absolute path for the .gdb file.
        """
        self.validate_inputs(script_source_name, description)
        stem = f"{script_source_name}___{description}___{self.scale}_{self.object}"
        return type_defs.GdbFilePath(str(self._gdb_dir / stem))

    def generate_file_name_general_files(
        self,
        script_source_name: str,
        description: str,
        file_type: str,
    ) -> type_defs.GeneralFilePath:
        """
        Generates a file path for general files (e.g., CSV, TXT). After validating the input.

        Args:
            script_source_name (str): The name of the script or source generating the file.
            description (str): A brief description of the file's purpose or contents.
            file_type (str): The filetype extension (without dot).

        Returns:
            str: The absolute path for the general file, including the file extension.
        """
        self.validate_inputs(script_source_name, description, file_type)
        stem = f"{script_source_name}___{description}___{self.scale}_{self.object}.{file_type}"
        return type_defs.GeneralFilePath(str(self._general_dir / stem))

    def generate_file_name_lyrx(
        self,
        script_source_name: str,
        description: str,
    ) -> type_defs.LyrxFilePath:
        """
        Generates a file path for ArcGIS layer files (.lyrx). After validating the input.

        Args:
            script_source_name (str): The name of the script or source generating the file.
            description (str): A brief description of the layer file's purpose or contents.

        Returns:
            str: The absolute path for the .lyrx file.
        """
        self.validate_inputs(script_source_name, description)
        stem = f"{script_source_name}___{description}___{self.scale}_{self.object}.lyrx"
        return type_defs.LyrxFilePath(str(self._lyrx_dir / stem))

    def generate_file_lyrx_directory_deprecated(
        self,
        script_source_name: str,
        description: str,
    ):
        """
        Generates a file path for ArcGIS layer files (.lyrx). After validating the input.

        Args:
            script_source_name (str): The name of the script or source generating the file.
            description (str): A brief description of the layer file's purpose or contents.

        Returns:
            str: The absolute path for the .lyrx file.
        """
        self.validate_inputs(script_source_name, description)
        return str(
            self._lyrx_dir
            / f"{script_source_name}___{description}___{self.scale}_{self.object}"
        )

    def generate_final_outputs(
        self,
        file_name: str,
    ) -> type_defs.GdbFilePath:
        """
        Generates a file path for geodatabase (.gdb) files for the final output files. After validating the input.

        Args:
            file_name (str): The name of the file name for the final output file.

        Returns:
            str: The absolute path for the .gdb file.
        """
        self.validate_inputs(file_name)
        return type_defs.GdbFilePath(str(self._final_outputs_dir / file_name))

    def generate_general_subdirectory(
        self, description: str
    ) -> type_defs.SubdirectoryPath:
        """
        Generates a subdirectory path under the general files directory.

        Args:
            description (str): A short descriptor for the subdirectory purpose.

        Returns:
            str: Absolute path of the subdirectory.
        """
        self.validate_inputs(description)

        dir_name = f"{description}___{self.scale}_{self.object}"
        full_path = self._general_dir / dir_name
        full_path.mkdir(parents=True, exist_ok=True)
        return type_defs.SubdirectoryPath(str(full_path))
