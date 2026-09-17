"""Unit tests for `dissolve_parents`. No ArcPy; runs anywhere.

pytest collects it. Without pytest installed, `python3 test_dissolve_parents.py` runs
every `test_*` function and reports.
"""

from __future__ import annotations

import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dissolve_parents import (  # noqa: E402
    DissolveKey,
    KeyMismatchError,
    LocateRequest,
    LocatorContractError,
    ParentPair,
    ParentsResolution,
    UnmatchedInputError,
    dissolve_parents,
    require_matched,
)


class RecordingLocator:
    """Answers from a fixed table of hits and records what it was asked."""

    def __init__(self, hits: Iterable[ParentPair] = ()) -> None:
        self.hits = list(hits)
        self.calls: list[Sequence[LocateRequest]] = []

    def locate(self, *, requests: Sequence[LocateRequest]) -> Iterable[ParentPair]:
        self.calls.append(requests)
        return list(self.hits)


class FailingLocator:
    """Fails the test if consulted: single-part keys must never reach the locator."""

    def locate(self, *, requests: Sequence[LocateRequest]) -> Iterable[ParentPair]:
        raise AssertionError(f"locator consulted with {requests}")


def key(*values: object) -> DissolveKey:
    return tuple(values)


def pair(output_index: int, input_index: int) -> ParentPair:
    return ParentPair(output_index=output_index, input_index=input_index)


def test_single_part_key_is_an_attribute_join() -> None:
    result = dissolve_parents(
        input_keys=[(1, key("a")), (2, key("a")), (3, key("b"))],
        output_keys=[(10, key("a")), (11, key("b"))],
        locator=FailingLocator(),
    )
    assert result.pairs == (pair(10, 1), pair(10, 2), pair(11, 3))
    assert result.unmatched_input_indices == ()


def test_multi_part_key_goes_to_the_locator_as_one_request() -> None:
    locator = RecordingLocator(hits=[pair(20, 1), pair(21, 2), pair(21, 3)])
    result = dissolve_parents(
        input_keys=[(1, key("a")), (2, key("a")), (3, key("a")), (4, key("b"))],
        output_keys=[(20, key("a")), (21, key("a")), (30, key("b"))],
        locator=locator,
    )
    assert locator.calls == [
        [LocateRequest(input_indices=(1, 2, 3), output_indices=(20, 21))]
    ]
    assert result.pairs == (pair(20, 1), pair(21, 2), pair(21, 3), pair(30, 4))


def test_every_multi_part_key_is_in_the_same_locator_call() -> None:
    locator = RecordingLocator(
        hits=[pair(20, 1), pair(21, 2), pair(30, 3), pair(31, 4)]
    )
    dissolve_parents(
        input_keys=[(1, key("a")), (2, key("a")), (3, key("b")), (4, key("b"))],
        output_keys=[(20, key("a")), (21, key("a")), (30, key("b")), (31, key("b"))],
        locator=locator,
    )
    assert len(locator.calls) == 1
    assert len(locator.calls[0]) == 2


def test_multipart_input_may_pair_with_several_parts() -> None:
    locator = RecordingLocator(hits=[pair(20, 1), pair(21, 1), pair(21, 2)])
    result = dissolve_parents(
        input_keys=[(1, key("a")), (2, key("a"))],
        output_keys=[(20, key("a")), (21, key("a"))],
        locator=locator,
    )
    assert result.pairs == (pair(20, 1), pair(21, 1), pair(21, 2))


def test_no_hit_means_no_pair_and_is_reported() -> None:
    locator = RecordingLocator(hits=[pair(20, 1)])
    result = dissolve_parents(
        input_keys=[(1, key("a")), (2, key("a")), (3, key("a"))],
        output_keys=[(20, key("a")), (21, key("a"))],
        locator=locator,
    )
    assert result.pairs == (pair(20, 1),)
    assert result.unmatched_input_indices == (2, 3)


def test_key_with_no_output_is_unmatched_not_an_error() -> None:
    result = dissolve_parents(
        input_keys=[(1, key("a")), (2, key("gone"))],
        output_keys=[(10, key("a"))],
        locator=FailingLocator(),
    )
    assert result.pairs == (pair(10, 1),)
    assert result.unmatched_input_indices == (2,)


def test_cross_key_pair_from_the_locator_is_rejected() -> None:
    """The test that fails if a locator does not filter by key.

    Input 3 has key b; the locator claims it lies in output 21, a part of key a. That is
    the overlapping-inputs case: a point lookup without a key filter finds it.
    """
    locator = RecordingLocator(hits=[pair(20, 1), pair(21, 2), pair(21, 3)])
    try:
        dissolve_parents(
            input_keys=[(1, key("a")), (2, key("a")), (3, key("b")), (4, key("b"))],
            output_keys=[
                (20, key("a")),
                (21, key("a")),
                (30, key("b")),
                (31, key("b")),
            ],
            locator=locator,
        )
    except LocatorContractError as exc:
        assert "input 3" in str(exc) and "output 21" in str(exc)
    else:
        raise AssertionError("a cross-key pair was accepted")


def test_pair_for_an_input_outside_every_request_is_rejected() -> None:
    locator = RecordingLocator(hits=[pair(20, 9)])
    try:
        dissolve_parents(
            input_keys=[(1, key("a")), (2, key("a"))],
            output_keys=[(20, key("a")), (21, key("a"))],
            locator=locator,
        )
    except LocatorContractError:
        pass
    else:
        raise AssertionError("a pair for an unrequested input was accepted")


def test_output_key_without_inputs_is_a_key_mismatch() -> None:
    try:
        dissolve_parents(
            input_keys=[(1, key("a"))],
            output_keys=[(10, key("a")), (11, key("b"))],
            locator=FailingLocator(),
        )
    except KeyMismatchError:
        pass
    else:
        raise AssertionError("an output key with no inputs was accepted")


def test_duplicate_index_is_a_key_mismatch() -> None:
    for input_keys, output_keys in (
        ([(1, key("a")), (1, key("a"))], [(10, key("a"))]),
        ([(1, key("a"))], [(10, key("a")), (10, key("a"))]),
    ):
        try:
            dissolve_parents(
                input_keys=input_keys, output_keys=output_keys, locator=FailingLocator()
            )
        except KeyMismatchError:
            continue
        raise AssertionError("a duplicated index was accepted")


def test_null_key_is_a_group() -> None:
    result = dissolve_parents(
        input_keys=[(1, key(None)), (2, key(None)), (3, key("a"))],
        output_keys=[(10, key(None)), (11, key("a"))],
        locator=FailingLocator(),
    )
    assert result.pairs == (pair(10, 1), pair(10, 2), pair(11, 3))


def test_int_and_float_keys_are_one_group_so_the_caller_must_normalise() -> None:
    """Pins the hazard rather than hiding it: 1 == 1.0, so a LONG read as int on one
    side and as float on the other is one key with two parts, not two keys."""
    locator = RecordingLocator()
    dissolve_parents(
        input_keys=[(1, key(1)), (2, key(1.0))],
        output_keys=[(11, key(1)), (12, key(1.0))],
        locator=locator,
    )
    assert locator.calls == [
        [LocateRequest(input_indices=(1, 2), output_indices=(11, 12))]
    ]


def test_pairs_are_sorted_and_deduplicated() -> None:
    locator = RecordingLocator(hits=[pair(21, 2), pair(20, 1), pair(21, 2)])
    result = dissolve_parents(
        input_keys=[(2, key("a")), (1, key("a"))],
        output_keys=[(21, key("a")), (20, key("a"))],
        locator=locator,
    )
    assert result.pairs == (pair(20, 1), pair(21, 2))


def test_one_large_multi_part_key_stays_linear_in_memory() -> None:
    """A key with n inputs and n parts must not cost n x n: the real STRESS key had
    112,331 inputs and 96,185 parts and the earlier per-input output sets ran out of
    memory. 40,000 x 40,000 would be 1.6e9 entries the old way; it must be instant."""
    n = 40_000
    locator = RecordingLocator(hits=[pair(100_000 + i, i) for i in range(1, 6)])
    result = dissolve_parents(
        input_keys=[(i, key("a")) for i in range(1, n + 1)],
        output_keys=[(100_000 + i, key("a")) for i in range(1, n + 1)],
        locator=locator,
    )
    assert len(result.pairs) == 5
    assert len(result.unmatched_input_indices) == n - 5


def test_unmatched_non_degenerate_input_raises() -> None:
    resolution = ParentsResolution(pairs=(pair(10, 1),), unmatched_input_indices=(2, 3))
    try:
        require_matched(resolution=resolution, degenerate_input_indices=[3])
    except UnmatchedInputError as exc:
        assert "[2]" in str(exc)
    else:
        raise AssertionError("a non-degenerate unmatched input was accepted")


def test_unmatched_degenerate_inputs_are_allowed() -> None:
    resolution = ParentsResolution(pairs=(pair(10, 1),), unmatched_input_indices=(2, 3))
    require_matched(resolution=resolution, degenerate_input_indices={2, 3})


if __name__ == "__main__":
    tests = [
        (name, fn) for name, fn in sorted(globals().items()) if name.startswith("test_")
    ]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"ok    {name}")
        except Exception as exc:  # report and continue, like pytest
            failed += 1
            print(f"FAIL  {name}: {type(exc).__name__}: {exc}")
    print(f"{len(tests) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
