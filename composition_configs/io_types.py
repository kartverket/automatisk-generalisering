from __future__ import annotations

from typing import TypeAlias

from . import type_defs
from .core_config import InjectIO

GdbPath = type_defs.GdbFilePath
GenPath = type_defs.GeneralFilePath
LyrxPath = type_defs.LyrxFilePath

FeatureIOArg: TypeAlias = GdbPath | GenPath | InjectIO
GdbIOArg: TypeAlias = GdbPath | InjectIO
LyrxIOArg: TypeAlias = LyrxPath | InjectIO

__all__ = ["GdbPath", "GenPath", "LyrxPath", "FeatureIOArg", "GdbIOArg", "LyrxIOArg"]
