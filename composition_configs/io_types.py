from __future__ import annotations

from typing import TypeAlias

from . import type_defs
from .core_config import InjectIO

FeatureIOArg: TypeAlias = type_defs.GdbFilePath | type_defs.GeneralFilePath | InjectIO
GdbIOArg: TypeAlias = type_defs.GdbFilePath | InjectIO
LyrxIOArg: TypeAlias = type_defs.LyrxFilePath | InjectIO


PathArg: TypeAlias = FeatureIOArg | GdbIOArg | LyrxIOArg

__all__ = ["FeatureIOArg", "GdbIOArg", "LyrxIOArg", "PathArg"]
