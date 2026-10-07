"""The warning categories: one base, three kinds, all catchable as `AgWarning`."""

from __future__ import annotations

import warnings

from ag.core.warnings import (
    AgWarning,
    DataQualityWarning,
    LineageWarning,
    PartitionWarning,
)


def test_every_category_is_an_ag_warning_and_a_user_warning() -> None:
    for category in (LineageWarning, DataQualityWarning, PartitionWarning):
        assert issubclass(category, AgWarning)
        assert issubclass(category, UserWarning)


def test_a_run_can_collect_every_warning_this_system_emits() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        warnings.warn("two orphans claimed by nearest", LineageWarning, stacklevel=1)
        warnings.warn("unrelated", RuntimeWarning, stacklevel=1)
    ours = [w for w in caught if issubclass(w.category, AgWarning)]
    assert len(ours) == 1 and ours[0].category is LineageWarning
