"""The warning categories the layers above `core` emit.

What: `AgWarning` and its three categories, used with `warnings.warn(..., category)`.

Why: a warning is for a result that is correct but degraded or suspicious: degenerate
inputs dropped, orphans claimed by the nearest feature, a detector firing. Anything that
makes an output or the log wrong raises instead. One base lets a run collect every warning
this system emits without naming layers.
"""

from __future__ import annotations


class AgWarning(UserWarning):
    """Base of every warning this package emits on purpose."""


class LineageWarning(AgWarning):
    """Identity was kept correct by a fallback worth a second look."""


class DataQualityWarning(AgWarning):
    """Input or output data is degraded in a way the result tolerates."""


class PartitionWarning(AgWarning):
    """A partition ran to a correct result on a suspicious shape or size."""
