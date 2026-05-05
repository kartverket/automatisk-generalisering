from dataclasses import dataclass
from pathlib import Path

from env_setup import global_config


@dataclass(frozen=True)
class ProjectLayout:
    """Single source of truth for the project's output directory layout."""

    output_root: Path
    main_directory_name: str = global_config.main_directory_name
    lyrx_directory_name: str = global_config.lyrx_directory_name
    general_files_name: str = global_config.general_files_name
    final_outputs_name: str = global_config.final_outputs

    @property
    def main_dir(self) -> Path:
        return self.output_root / self.main_directory_name

    def scale_dir(self, scale: str) -> Path:
        return self.main_dir / scale

    def gdb(self, scale: str, name: str) -> Path:
        return self.scale_dir(scale) / f"{name}.gdb"

    def lyrx_dir(self, scale: str) -> Path:
        return self.scale_dir(scale) / self.lyrx_directory_name

    def general_files_dir(self, scale: str) -> Path:
        return self.scale_dir(scale) / self.general_files_name
