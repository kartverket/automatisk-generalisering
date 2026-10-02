"""Replay the recorded goldens through `dissolve_parents` without ArcPy.

Each file under `goldens/` was written by `n1_parents_gate.py --write-goldens` on a
Windows Pro run: both key lists, the native lineage table's pairs, and for every locator
the raw hits it returned and the pairs the resolver produced from them. Replaying the
hits must reproduce the recorded resolver pairs exactly, and where the recorded run
agreed with the native table, the replay must too.

pytest collects it; `python3 test_goldens.py` runs it without pytest. With no goldens
recorded yet it reports that and passes, which is not a green result.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dissolve_parents import (  # noqa: E402
    DissolveKey,
    LocateRequest,
    ParentPair,
    dissolve_parents,
)

GOLDENS = Path(__file__).parent / "goldens"


class ReplayLocator:
    def __init__(self, hits: Iterable[ParentPair]) -> None:
        self.hits = list(hits)

    def locate(self, *, requests: Sequence[LocateRequest]) -> Iterable[ParentPair]:
        return list(self.hits)


def _pairs(rows: Iterable[Sequence[int]]) -> set[ParentPair]:
    return {ParentPair(output_index=o, input_index=i) for o, i in rows}


def _keys(rows: Iterable[Sequence[object]]) -> list[tuple[int, DissolveKey]]:
    return [(int(index), tuple(key)) for index, key in rows]  # type: ignore[misc]


def golden_files() -> list[Path]:
    return sorted(GOLDENS.glob("*.json"))


def replay(path: Path) -> list[str]:
    """Returns the failures for one golden, empty when it replays exactly."""
    with open(path, encoding="utf-8") as handle:
        golden = json.load(handle)
    failures: list[str] = []
    native = _pairs(golden["native_pairs"])
    for locator_name, recorded in golden["locators"].items():
        resolution = dissolve_parents(
            input_keys=_keys(golden["input_keys"]),
            output_keys=_keys(golden["output_keys"]),
            locator=ReplayLocator(_pairs(recorded["hits"])),
        )
        replayed = set(resolution.pairs)
        expected = _pairs(recorded["resolved"])
        if replayed != expected:
            failures.append(
                f"{path.name} / {locator_name}: replay differs from the recorded "
                f"resolver pairs ({len(replayed)} vs {len(expected)})"
            )
        if expected == native and replayed != native:
            failures.append(
                f"{path.name} / {locator_name}: recorded run agreed with the native "
                "table and the replay does not"
            )
    return failures


def test_every_golden_replays_exactly() -> None:
    files = golden_files()
    if not files:
        print("no goldens recorded under", GOLDENS)
        return
    failures = [failure for path in files for failure in replay(path)]
    assert not failures, "\n".join(failures)


if __name__ == "__main__":
    files = golden_files()
    if not files:
        print(f"no goldens recorded under {GOLDENS}; nothing was verified")
        sys.exit(0)
    all_failures: list[str] = []
    for path in files:
        failures = replay(path)
        all_failures.extend(failures)
        print(f"{'FAIL' if failures else 'ok  '}  {path.name}")
        for failure in failures:
            print(f"        {failure}")
    print(
        f"{len(files) - len({f.split(' /')[0] for f in all_failures})} of {len(files)} replayed exactly"
    )
    sys.exit(1 if all_failures else 0)
