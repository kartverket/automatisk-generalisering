"""The timing run's pure parts: the pass loop and the WKB walk.

What: `run_pass` on generators that record whether their `finally` ran, with an
injected clock; `shape_stats` on values the test-side encoder writes. No engine: the
stages that reach one are read in the evidence.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterator

import pytest

from ag.ports.errors import PortContractError
from ag.ports.geometry import Geometry, GeometryKind
from tests.support import wkb
from tools.engine import time_read_rows as timing

CRS = "EPSG:25833"
SQUARE_CCW = ((0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0), (0.0, 0.0))
HOLE_CW = ((1.0, 1.0), (1.0, 2.0), (2.0, 2.0), (2.0, 1.0), (1.0, 1.0))


class Clock:
    """A clock that advances by a fixed step on every read."""

    def __init__(self, step: float) -> None:
        self.now = 0.0
        self.step = step

    def __call__(self) -> float:
        self.now += self.step
        return self.now


class Rows:
    """A generator over `count` rows that records whether it was closed."""

    def __init__(self, count: int, *, interrupt_at: int | None = None) -> None:
        self.count = count
        self.interrupt_at = interrupt_at
        self.closed = False

    def __iter__(self) -> Iterator[object]:
        try:
            for index in range(self.count):
                if index == self.interrupt_at:
                    raise KeyboardInterrupt
                yield index
        finally:
            self.closed = True


def test_a_pass_that_ends_counts_its_rows_and_reports_each_batch() -> None:
    rows = Rows(7)
    batches: list[tuple[int, float]] = []
    result = timing.run_pass(
        iter(rows),
        cap_seconds=1_000.0,
        batch_rows=3,
        clock=Clock(1.0),
        on_batch=lambda count, elapsed: batches.append((count, elapsed)),
    )
    assert result.status == "complete"
    assert result.rows == 7
    assert [count for count, _ in batches] == [3, 6]
    assert rows.closed


def test_the_cap_ends_the_pass_at_a_batch_boundary_and_closes_the_iterator() -> None:
    rows = Rows(1_000)
    result = timing.run_pass(
        iter(rows), cap_seconds=5.0, batch_rows=4, clock=Clock(1.0)
    )
    assert result.status == "capped"
    assert result.rows == 20
    assert rows.closed
    assert result.rows_per_s is not None


def test_an_interrupt_is_a_result_and_the_iterator_is_closed() -> None:
    rows = Rows(100, interrupt_at=5)
    result = timing.run_pass(
        iter(rows), cap_seconds=1_000.0, batch_rows=50, clock=Clock(1.0)
    )
    assert result.status == "interrupted"
    assert result.rows == 5
    assert rows.closed


class Raising:
    """A generator that raises `error` after `before` rows and records its close."""

    def __init__(self, error: Exception, *, before: int) -> None:
        self.error = error
        self.before = before
        self.closed = False

    def __iter__(self) -> Iterator[object]:
        try:
            yield from range(self.before)
            raise self.error
        finally:
            self.closed = True


@pytest.mark.parametrize(
    ("error", "status"),
    [
        pytest.param(ValueError("cell value 42 at (1.0, 2.0)"), "failed", id="defect"),
        pytest.param(
            PortContractError("row 3 holds 'a value'"), "refused", id="refusal"
        ),
    ],
)
def test_an_exception_mid_pass_is_a_result_that_names_its_class_only(
    error: Exception, status: str
) -> None:
    rows = Raising(error, before=3)
    result = timing.run_pass(
        iter(rows), cap_seconds=1_000.0, batch_rows=50, clock=Clock(1.0)
    )
    assert (result.status, result.rows, result.error) == (
        status,
        3,
        type(error).__name__,
    )
    assert "42" not in json.dumps(result.__dict__)
    assert "a value" not in json.dumps(result.__dict__)
    assert rows.closed


def test_a_failure_line_carries_the_class_and_never_the_message() -> None:
    assert timing.failure(ValueError("cell value 42")) == {
        "status": "failed",
        "error": "ValueError",
    }
    assert timing.failure(PortContractError("row 3"))["status"] == "refused"


@pytest.mark.parametrize(
    ("value", "kind", "rings", "vertices", "holed"),
    [
        pytest.param(None, "null", 0, 0, 0, id="null"),
        pytest.param(wkb.empty(wkb.POLYGON), "empty", 0, 0, 0, id="empty-polygon"),
        pytest.param(wkb.empty(wkb.POINT), "empty", 0, 0, 0, id="empty-point"),
        pytest.param(
            wkb.to_wkb(Geometry.point(1.0, 2.0, crs=CRS)), "planar", 1, 1, 0, id="point"
        ),
        pytest.param(
            wkb.to_wkb(
                Geometry(
                    kind=GeometryKind.POLYGON, parts=(SQUARE_CCW, HOLE_CW), crs=CRS
                ),
                order=">",
            ),
            "planar",
            2,
            10,
            0,
            id="polygon-with-hole-big-endian",
        ),
        pytest.param(
            wkb.multipolygon_with_hole(), "planar", 3, 15, 1, id="holed-member"
        ),
        pytest.param(wkb.typed(10), "curve", 0, 0, 0, id="curve-polygon"),
        pytest.param(wkb.typed(1003), "z", 0, 0, 0, id="iso-z-polygon"),
        pytest.param(wkb.typed(2002), "m", 0, 0, 0, id="iso-m-line"),
        pytest.param(wkb.typed(3001), "zm", 0, 0, 0, id="iso-zm-point"),
        pytest.param(wkb.typed(0x40000001), "z", 0, 0, 0, id="ewkb-z-point"),
        pytest.param(wkb.typed(99), "other", 0, 0, 0, id="unknown-code"),
        pytest.param("text", "other", 0, 0, 0, id="not-bytes"),
    ],
)
def test_the_walk_classifies_a_shape_and_counts_a_planar_one(
    value: object, kind: str, rings: int, vertices: int, holed: int
) -> None:
    stats = timing.shape_stats(value)
    assert (stats.kind, stats.rings, stats.vertices, stats.holed_members) == (
        kind,
        rings,
        vertices,
        holed,
    )


def test_the_histogram_summary_reads_percentiles_from_counts() -> None:
    histogram: Counter[int] = Counter({2: 90, 10: 9, 100: 1})
    assert timing.summary(histogram) == {
        "n": 100,
        "mean": 3.7,
        "p50": 2,
        "p95": 10,
        "max": 100,
    }
    assert timing.summary(Counter[int]())["n"] == 0
