# Libraries

from pathlib import Path

from data_orchestrator_2.fields import Fields as F


######################
# Classes
######################


class DataSet:
    def __init__(self, object: str, scale: str, path: str):
        self.object: str = object
        self.path: Path = Path(path)
        self.scale: str = scale.lower()

        columns: list[str] = [] # TODO: Add setter immediately after initialization
