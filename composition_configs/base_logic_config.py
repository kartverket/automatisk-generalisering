from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union


@dataclass
class WorkFileConfig:
    root_file: str
    write_to_memory: Optional[bool] = False
    keep_files: Optional[bool] = False
